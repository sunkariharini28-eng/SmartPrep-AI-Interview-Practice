from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..ai import clamp, complete_json
from ..database import Resume, User, get_db, log
from ..files import extract_text, save_upload
from ..security import current_user

router = APIRouter(prefix="/resume", tags=["resume"])


class MatchIn(BaseModel):
    role: str = Field(min_length=2, max_length=120)
    job_description: str = Field("", max_length=6000)


def _owned(db, user, rid) -> Resume:
    r = db.get(Resume, rid)
    if not r or r.user_id != user.id:
        raise HTTPException(404, "Resume not found")
    return r


def _out(r: Resume, full=False) -> dict:
    d = {"id": r.id, "filename": r.filename, "analysis": r.analysis, "created_at": r.created_at.isoformat()}
    if full:
        d["text"] = r.text
    return d


@router.post("/upload", status_code=201)
async def upload(file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    orig, stored, path = await save_upload(file, {".pdf", ".docx"}, f"resumes/{user.id}")
    text = extract_text(path)
    analysis = complete_json(
        "You are an expert technical recruiter and resume coach.",
        f"Analyse this resume.\n<data>{text[:9000]}</data>\nReturn JSON: "
        '{"skills": ["..."], "education": [{"degree":"...","institution":"...","year":"..."}], '
        '"projects": [{"name":"...","summary":"...","tech":["..."]}], "strengths": ["..."], "weaknesses": ["..."], '
        '"improvements": ["specific, actionable suggestions"], "interview_questions": ["8 questions based on this resume"], '
        '"ats_score": number 0-100}', 2500)
    r = Resume(user_id=user.id, filename=orig, stored_name=stored, text=text, analysis=analysis)
    db.add(r)
    db.commit()
    log(db, user.id, "resume_upload", orig)
    return _out(r)


@router.get("")
def list_resumes(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [_out(r) for r in db.query(Resume).filter_by(user_id=user.id).order_by(Resume.id.desc())]


@router.post("/{rid}/match")
def match(rid: int, body: MatchIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = _owned(db, user, rid)
    jd = f"\nJob description:\n<data>{body.job_description}</data>" if body.job_description else ""
    res = complete_json(
        "You are an ATS and recruiter assessing resume-to-role fit. Be honest and calibrated.",
        f"Target role: {body.role}{jd}\nResume:\n<data>{r.text[:9000]}</data>\nReturn JSON: "
        '{"match_score": number 0-100, "matched_skills": ["..."], "missing_skills": ["..."], "summary": "...", '
        '"suggestions": ["..."]}', 1500)
    res["match_score"] = clamp(res.get("match_score"), 0, 100)
    r.analysis = {**(r.analysis or {}), "last_match": {"role": body.role, **res}}
    db.commit()
    return {"role": body.role, **res}


@router.delete("/{rid}", status_code=204)
def delete(rid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from pathlib import Path
    from ..config import settings
    r = _owned(db, user, rid)
    (Path(settings.UPLOAD_DIR) / f"resumes/{user.id}" / r.stored_name).unlink(missing_ok=True)
    db.delete(r)
    db.commit()
