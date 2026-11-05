from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import (Answer, AptitudeTest, CodingSubmission, Evaluation, InterviewSession, User,
                        UserProgress, get_db)
from ..security import current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])
SOFT = {"HR Interview", "Communication Skills"}


def _r(v, n=1):
    return None if v is None else round(float(v), n)


@router.get("/summary")
def summary(user: User = Depends(current_user), db: Session = Depends(get_db)):
    sessions = db.query(InterviewSession).filter_by(user_id=user.id, status="finished").order_by(InterviewSession.id).all()
    tech = [s.avg_score for s in sessions if s.category not in SOFT and s.avg_score is not None]
    comm = db.query(func.avg(Evaluation.communication)).join(Answer, Answer.id == Evaluation.answer_id) \
        .join(InterviewSession, InterviewSession.id == Answer.session_id).filter(InterviewSession.user_id == user.id).scalar()
    subs = db.query(CodingSubmission).filter_by(user_id=user.id).all()
    coding = [s.passed / s.total * 100 for s in subs if s.total]
    apt = db.query(func.avg(AptitudeTest.score_pct)).filter_by(user_id=user.id).scalar()
    prog = db.query(UserProgress).filter_by(user_id=user.id).all()
    weak = sorted([p for p in prog if p.avg_score < 6], key=lambda p: p.avg_score)[:8]
    strong = sorted([p for p in prog if p.avg_score >= 7.5], key=lambda p: -p.avg_score)[:8]
    fmt = lambda p: {"topic": p.topic, "avg_score": round(p.avg_score, 1), "attempts": p.attempts}
    return {
        "total_interviews": len(sessions),
        "avg_interview_score": _r(sum(s.avg_score for s in sessions if s.avg_score is not None) / len(sessions)) if sessions else None,
        "technical_score": _r(sum(tech) / len(tech)) if tech else None,
        "communication_score": _r(comm),
        "coding_score_pct": _r(sum(coding) / len(coding)) if coding else None,
        "aptitude_score_pct": _r(apt),
        "problems_solved": len({s.problem_id for s in subs if s.total and s.passed == s.total}),
        "weak_topics": [fmt(p) for p in weak],
        "strong_topics": [fmt(p) for p in strong],
        "progress": [{"id": s.id, "date": s.created_at.strftime("%Y-%m-%d"), "category": s.category,
                      "score": s.avg_score, "communication": s.avg_communication} for s in sessions[-30:]],
        "skills": [{"name": "Technical", "value": _r(sum(tech) / len(tech) * 10) if tech else 0},
                   {"name": "Communication", "value": _r(comm * 10) if comm else 0},
                   {"name": "Coding", "value": _r(sum(coding) / len(coding)) if coding else 0},
                   {"name": "Aptitude", "value": _r(apt) or 0}],
    }
