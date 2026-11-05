from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..ai import complete_json
from ..database import CodingSubmission, Question, User, get_db, log, record_progress
from ..sandbox import available_languages, run_code
from ..security import current_user

router = APIRouter(prefix="/coding", tags=["coding"])
Lang = Literal["python", "javascript", "java", "c", "cpp"]


class RunIn(BaseModel):
    language: Lang
    code: str = Field(max_length=50000)
    stdin: str = Field("", max_length=5000)


class SubmitIn(BaseModel):
    problem_id: int
    language: Lang
    code: str = Field(max_length=50000)


class HintIn(BaseModel):
    problem_id: int
    language: Lang
    code: str = Field("", max_length=50000)


def _norm(s: str) -> str:
    return "\n".join(line.rstrip() for line in s.strip().splitlines())


@router.get("/languages")
def languages():
    return available_languages()


@router.get("/problems")
def problems(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.query(Question).filter_by(kind="coding").order_by(Question.id).all()
    solved = {s.problem_id for s in db.query(CodingSubmission).filter_by(user_id=user.id)
              if s.total and s.passed == s.total}
    return [{"id": p.id, "title": p.title, "difficulty": p.difficulty, "category": p.category,
             "solved": p.id in solved} for p in rows]


@router.get("/problems/{pid}")
def problem(pid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    p = db.get(Question, pid)
    if not p or p.kind != "coding":
        raise HTTPException(404, "Problem not found")
    samples = (p.test_cases or [])[:2]
    return {"id": p.id, "title": p.title, "difficulty": p.difficulty, "text": p.text, "samples": samples,
            "total_tests": len(p.test_cases or [])}


@router.post("/run")
def run(body: RunIn, user: User = Depends(current_user)):
    return run_code(body.language, body.code, body.stdin)


@router.post("/submit")
def submit(body: SubmitIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = db.get(Question, body.problem_id)
    if not p or p.kind != "coding":
        raise HTTPException(404, "Problem not found")
    results, passed = [], 0
    for i, tc in enumerate(p.test_cases or []):
        r = run_code(body.language, body.code, tc["input"])
        ok = r["status"] == "ok" and _norm(r["stdout"]) == _norm(tc["expected"])
        passed += ok
        hidden = i >= 2
        results.append({"test": i + 1, "passed": ok, "status": r["status"], "time_ms": r["time_ms"],
                        "input": None if hidden else tc["input"], "expected": None if hidden else tc["expected"],
                        "output": None if hidden else r["stdout"][:500], "error": r["stderr"][:500]})
    total = len(results)
    review = None
    try:
        review = complete_json(
            "You are a senior engineer reviewing a coding interview submission.",
            f"Problem: {p.text}\nLanguage: {body.language}\nTests passed: {passed}/{total}\n"
            f"Code:\n<data>{body.code[:6000]}</data>\nReturn JSON: "
            '{"time_complexity": "O(...)", "space_complexity": "O(...)", "correctness": "assessment", '
            '"explanation": "how the solution works / why it fails", "improvements": ["..."]}', 1000)
    except HTTPException:
        review = {"error": "AI review unavailable (check ANTHROPIC_API_KEY)."}
    sub = CodingSubmission(user_id=user.id, problem_id=p.id, language=body.language, code=body.code,
                           passed=passed, total=total, results=results, review=review)
    db.add(sub)
    record_progress(db, user.id, f"Coding: {p.title}", (passed / total * 10) if total else 0)
    db.commit()
    log(db, user.id, "coding_submit", f"{p.title} {passed}/{total}")
    return {"passed": passed, "total": total, "results": results, "review": review}


@router.post("/hint")
def hint(body: HintIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = db.get(Question, body.problem_id)
    if not p or p.kind != "coding":
        raise HTTPException(404, "Problem not found")
    return complete_json(
        "You are a coding mentor. Give a nudge, NOT the full solution.",
        f"Problem: {p.text}\nLanguage: {body.language}\nStudent code so far:\n<data>{body.code[:4000]}</data>\n"
        'Return JSON: {"hint": "...", "concept": "key concept or algorithm to consider"}', 600)
