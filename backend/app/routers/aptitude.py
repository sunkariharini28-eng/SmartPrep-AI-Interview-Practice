import random

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import AptitudeTest, Question, User, get_db, log, record_progress
from ..security import current_user

router = APIRouter(prefix="/aptitude", tags=["aptitude"])
SECTIONS = ["Quantitative", "Logical", "Verbal"]


class SubmitIn(BaseModel):
    section: str
    answers: dict[int, int]  # question id -> chosen option index
    question_ids: list[int] = Field(max_length=50)
    duration_seconds: int = Field(0, ge=0, le=7200)


@router.get("/sections")
def sections(db: Session = Depends(get_db)):
    out = []
    for s in SECTIONS:
        n = db.query(Question).filter_by(kind="aptitude", category=s).count()
        out.append({"name": s, "available": n})
    return out


@router.get("/questions")
def questions(section: str, n: int = 10, db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.query(Question).filter_by(kind="aptitude", category=section).all()
    if not rows:
        raise HTTPException(404, "No questions for this section")
    random.shuffle(rows)
    rows = rows[:max(1, min(n, 30))]
    return [{"id": q.id, "text": q.text, "options": q.options, "difficulty": q.difficulty} for q in rows]


@router.post("/submit")
def submit(body: SubmitIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    qs = {q.id: q for q in db.query(Question).filter(Question.id.in_(body.question_ids), Question.kind == "aptitude")}
    if not qs:
        raise HTTPException(422, "No valid questions submitted")
    details, correct = [], 0
    for qid in body.question_ids:
        q = qs.get(qid)
        if not q:
            continue
        chosen = body.answers.get(qid)
        ok = chosen == q.answer_index
        correct += ok
        details.append({"id": qid, "text": q.text, "options": q.options, "chosen": chosen,
                        "correct_index": q.answer_index, "is_correct": ok, "explanation": q.explanation})
    total = len(details)
    pct = round(correct / total * 100, 1)
    t = AptitudeTest(user_id=user.id, section=body.section, total=total, correct=correct, score_pct=pct,
                     duration_seconds=body.duration_seconds, details=details)
    db.add(t)
    record_progress(db, user.id, f"Aptitude: {body.section}", pct / 10)
    db.commit()
    log(db, user.id, "aptitude_submit", f"{body.section} {correct}/{total}")
    return {"id": t.id, "section": body.section, "total": total, "correct": correct, "score_pct": pct, "details": details}


@router.get("/history")
def history(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.query(AptitudeTest).filter_by(user_id=user.id).order_by(AptitudeTest.id.desc()).limit(30).all()
    return [{"id": t.id, "section": t.section, "total": t.total, "correct": t.correct, "score_pct": t.score_pct,
             "created_at": t.created_at.isoformat()} for t in rows]
