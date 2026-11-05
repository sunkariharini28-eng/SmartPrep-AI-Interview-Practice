from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..ai import complete_json
from ..database import Resume, Roadmap, User, UserProgress, get_db, log
from ..security import current_user

router = APIRouter(prefix="/coach", tags=["coach"])


class PlanIn(BaseModel):
    target_role: str = Field("", max_length=120)
    weeks: int = Field(8, ge=2, le=26)


@router.post("/plan", status_code=201)
def plan(body: PlanIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    prog = db.query(UserProgress).filter_by(user_id=user.id).all()
    perf = [f"{p.topic}: {p.avg_score:.1f}/10 over {p.attempts} attempts" for p in prog][:30]
    resume = db.query(Resume).filter_by(user_id=user.id).order_by(Resume.id.desc()).first()
    res_skills = (resume.analysis or {}).get("skills", []) if resume else []
    role = body.target_role or user.target_role or ""
    ctx = (f"Declared skills: {user.skills or []}\nResume skills: {res_skills}\nTarget role: {role or 'not specified'}\n"
           f"Practice performance: {perf or 'no practice data yet'}\nBio: {user.bio[:500]}")
    content = complete_json(
        "You are an experienced career coach for software students and job seekers. Be specific and realistic.",
        f"<data>{ctx}</data>\nCreate a {body.weeks}-week personalised plan. Return JSON: "
        '{"suggested_roles": [{"role":"...","reason":"..."}], "missing_skills": ["..."], '
        '"roadmap": [{"week": 1, "focus": "...", "tasks": ["..."]}], "daily_tasks": ["..."], '
        '"interview_prep_plan": ["..."], "project_ideas": [{"name":"...","description":"...","skills":["..."]}]}', 3500)
    r = Roadmap(user_id=user.id, target_role=role or "General", content=content)
    db.add(r)
    db.commit()
    log(db, user.id, "coach_plan", role)
    return {"id": r.id, "target_role": r.target_role, "content": content, "created_at": r.created_at.isoformat()}


@router.get("/plans")
def plans(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.query(Roadmap).filter_by(user_id=user.id).order_by(Roadmap.id.desc()).limit(10).all()
    return [{"id": r.id, "target_role": r.target_role, "content": r.content, "created_at": r.created_at.isoformat()}
            for r in rows]
