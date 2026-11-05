from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import (ActivityLog, AptitudeTest, Category, CodingSubmission, InterviewSession, Question, User,
                        get_db, log)
from ..security import admin_user

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(admin_user)])


class QuestionIn(BaseModel):
    kind: Literal["aptitude", "coding", "interview"]
    category: str = Field(max_length=100)
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    title: str = Field("", max_length=200)
    text: str = Field(min_length=5)
    options: list[str] | None = None
    answer_index: int | None = None
    explanation: str = ""
    test_cases: list[dict] | None = None


class CategoryIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    kind: Literal["interview", "aptitude", "coding"] = "interview"


class UserPatch(BaseModel):
    is_active: bool | None = None
    role: Literal["student", "admin"] | None = None


def _validate_q(q: QuestionIn):
    if q.kind == "aptitude":
        if not q.options or len(q.options) < 2 or q.answer_index is None or not (0 <= q.answer_index < len(q.options)):
            raise HTTPException(422, "Aptitude questions need >=2 options and a valid answer_index")
    if q.kind == "coding" and not q.test_cases:
        raise HTTPException(422, "Coding problems need test_cases: [{input, expected}]")


def _q_out(q: Question):
    return {"id": q.id, "kind": q.kind, "category": q.category, "difficulty": q.difficulty, "title": q.title,
            "text": q.text, "options": q.options, "answer_index": q.answer_index, "explanation": q.explanation,
            "test_cases": q.test_cases}


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    by_cat = db.query(InterviewSession.category, func.count(), func.avg(InterviewSession.avg_score)) \
        .group_by(InterviewSession.category).all()
    return {"users": db.query(User).count(), "active_users": db.query(User).filter_by(is_active=True).count(),
            "interviews": db.query(InterviewSession).count(),
            "finished_interviews": db.query(InterviewSession).filter_by(status="finished").count(),
            "coding_submissions": db.query(CodingSubmission).count(),
            "aptitude_tests": db.query(AptitudeTest).count(), "questions": db.query(Question).count(),
            "by_category": [{"category": c, "count": n, "avg_score": round(a, 2) if a else None} for c, n, a in by_cat]}


@router.get("/users")
def users(db: Session = Depends(get_db)):
    return [{"id": u.id, "name": u.name, "email": u.email, "role": u.role, "is_active": u.is_active,
             "created_at": u.created_at.isoformat()} for u in db.query(User).order_by(User.id)]


@router.patch("/users/{uid}")
def patch_user(uid: int, body: UserPatch, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404, "User not found")
    if u.id == admin.id:
        raise HTTPException(400, "You cannot change your own role or status")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(u, k, v)
    db.commit()
    log(db, admin.id, "admin_user_update", f"user {uid}")
    return {"id": u.id, "role": u.role, "is_active": u.is_active}


@router.delete("/users/{uid}", status_code=204)
def delete_user(uid: int, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    u = db.get(User, uid)
    if not u or u.id == admin.id:
        raise HTTPException(400, "Cannot delete this user")
    db.delete(u)
    db.commit()
    log(db, admin.id, "admin_user_delete", f"user {uid}")


@router.get("/questions")
def list_questions(kind: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Question)
    if kind:
        q = q.filter_by(kind=kind)
    return [_q_out(x) for x in q.order_by(Question.id.desc()).limit(300)]


@router.post("/questions", status_code=201)
def add_question(body: QuestionIn, db: Session = Depends(get_db)):
    _validate_q(body)
    q = Question(**body.model_dump())
    db.add(q)
    db.commit()
    return _q_out(q)


@router.put("/questions/{qid}")
def edit_question(qid: int, body: QuestionIn, db: Session = Depends(get_db)):
    _validate_q(body)
    q = db.get(Question, qid)
    if not q:
        raise HTTPException(404, "Question not found")
    for k, v in body.model_dump().items():
        setattr(q, k, v)
    db.commit()
    return _q_out(q)


@router.delete("/questions/{qid}", status_code=204)
def del_question(qid: int, db: Session = Depends(get_db)):
    q = db.get(Question, qid)
    if not q:
        raise HTTPException(404, "Question not found")
    db.delete(q)
    db.commit()


@router.get("/categories")
def cats(db: Session = Depends(get_db)):
    return [{"id": c.id, "name": c.name, "kind": c.kind} for c in db.query(Category).order_by(Category.id)]


@router.post("/categories", status_code=201)
def add_cat(body: CategoryIn, db: Session = Depends(get_db)):
    if db.query(Category).filter_by(name=body.name).first():
        raise HTTPException(409, "Category exists")
    c = Category(**body.model_dump())
    db.add(c)
    db.commit()
    return {"id": c.id, "name": c.name, "kind": c.kind}


@router.delete("/categories/{cid}", status_code=204)
def del_cat(cid: int, db: Session = Depends(get_db)):
    c = db.get(Category, cid)
    if not c:
        raise HTTPException(404, "Category not found")
    db.delete(c)
    db.commit()


@router.get("/activity")
def activity(limit: int = 100, db: Session = Depends(get_db)):
    rows = db.query(ActivityLog).order_by(ActivityLog.id.desc()).limit(min(limit, 500)).all()
    names = {u.id: u.email for u in db.query(User)}
    return [{"id": a.id, "user": names.get(a.user_id, "-"), "action": a.action, "detail": a.detail,
             "created_at": a.created_at.isoformat()} for a in rows]
