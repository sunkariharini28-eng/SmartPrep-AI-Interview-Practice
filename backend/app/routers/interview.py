
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..ai import clamp, complete_json, _client
from ..database import (
    Answer, Category, Evaluation, InterviewSession,
    Resume, User, get_db, log, record_progress
)
from ..security import current_user

router = APIRouter(prefix="/interview", tags=["interview"])

LEVELS = ["easy", "medium", "hard"]

PERSONAS = {
    "HR Interview": (
        "an HR interviewer: behavioural, situational, motivation "
        "and culture-fit questions (use STAR-style evaluation)."
    ),
    "Communication Skills": (
        "a communication coach: ask the candidate to explain, "
        "persuade, summarise or handle workplace conversations; "
        "judge clarity, structure and tone."
    ),
    "Resume-Based": (
        "a technical interviewer who asks about the candidate's "
        "own resume, projects and claimed skills."
    ),
}


class StartIn(BaseModel):
    category: str = Field(max_length=100)
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    num_questions: int = Field(5, ge=1, le=20)
    mode: Literal["text", "voice", "video"] = "text"
    language: str = Field("English", max_length=30)
    resume_id: int | None = None


class AnswerIn(BaseModel):
    answer: str = Field(min_length=1, max_length=6000)
    duration_seconds: float | None = Field(None, ge=0, le=3600)


def _owned(db, user, sid) -> InterviewSession:
    s = db.get(InterviewSession, sid)

    if not s or s.user_id != user.id:
        raise HTTPException(404, "Interview not found")

    return s



# VOICE TO TEXT - GROQ WHISPER
@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    user: User = Depends(current_user)
):
    audio = await file.read(25 * 1024 * 1024 + 1)

    if not audio:
        raise HTTPException(400, "Audio file is empty.")

    if len(audio) > 25 * 1024 * 1024:
        raise HTTPException(
            413,
            "Audio file is too large. Maximum 25 MB."
        )

    filename = file.filename or "answer.webm"

    print("----- AUDIO TRANSCRIPTION DEBUG -----")
    print("Filename:", filename)
    print("Content type:", file.content_type)
    print("Audio size:", len(audio), "bytes")

    try:
        client = _client()

        result = client.audio.transcriptions.create(
            file=(filename, audio),
            model="whisper-large-v3",
            response_format="verbose_json",
            temperature=0.0
        )

        transcript = (result.text or "").strip()

        print("Transcription completed.")
        print("Transcript characters:", len(transcript))
        print("-------------------------------------")

        if not transcript:
            raise HTTPException(
                422,
                "No speech detected. Please record again."
            )

        return {"text": transcript}

    except HTTPException:
        raise

    except Exception as e:
        print("Whisper error:", type(e).__name__, str(e)[:300])

        raise HTTPException(
            502,
            f"Voice transcription failed: {type(e).__name__}: {str(e)[:200]}"
        )



def _adapt(session: InterviewSession) -> str:
    """Raise/lower difficulty from the last two scores."""

    cur = LEVELS.index(
        session.difficulty
        if session.difficulty in LEVELS
        else "medium"
    )

    scored = [
        a.evaluation.score
        for a in session.answers if a.evaluation
    ]

    if len(scored) >= 2:
        avg = sum(scored[-2:]) / 2

        if avg >= 8:
            cur = min(2, cur + 1)
        elif avg <= 4:
            cur = max(0, cur - 1)

    elif scored:
        if scored[-1] >= 9:
            cur = min(2, cur + 1)
        elif scored[-1] <= 3:
            cur = max(0, cur - 1)

    return LEVELS[cur]


def _next_question(db: Session, s: InterviewSession) -> Answer:
    s.difficulty = _adapt(s)

    persona = PERSONAS.get(
        s.category,
        f"a senior technical interviewer for the topic '{s.category}'."
    )

    prev = [a.question for a in s.answers]
    resume_part = ""

    if s.resume_id:
        r = db.get(Resume, s.resume_id)

        if r:
            resume_part = (
                f"\nCandidate resume:\n<data>{r.text[:6000]}</data>"
            )

    system = (
        f"You are {persona} Ask exactly ONE interview question at a time, "
        f"at {s.difficulty} difficulty. "
        f"Write the question in {s.language}. "
        "Do not repeat earlier questions or give the answer."
    )

    user_msg = (
        f"Category: {s.category}. "
        f"Question number {len(prev) + 1} of {s.num_questions}.\n"
        f"Earlier questions: {prev if prev else 'none'}"
        f"{resume_part}\n"
        'Return JSON: {"question": "...", "topic": "short subtopic name"}'
    )

    data = complete_json(system, user_msg, 600)
    q = str(data.get("question", "")).strip()

    if not q:
        raise HTTPException(
            502,
            "AI did not return a question. Please retry."
        )

    a = Answer(
        session=s,
        idx=len(prev) + 1,
        question=q,
        topic=str(data.get("topic", s.category))[:150],
        difficulty=s.difficulty
    )

    db.add(a)
    db.flush()

    return a


def _qa_out(a: Answer) -> dict:
    ev = a.evaluation

    return {
        "id": a.id,
        "idx": a.idx,
        "question": a.question,
        "topic": a.topic,
        "difficulty": a.difficulty,
        "answer": a.answer,
        "evaluation": None if not ev else {
            "score": ev.score,
            "communication": ev.communication,
            "feedback": ev.feedback,
            "correct_answer": ev.correct_answer,
            "improvements": ev.improvements
        }
    }


def _session_out(s: InterviewSession) -> dict:
    return {
        "id": s.id,
        "category": s.category,
        "mode": s.mode,
        "difficulty": s.difficulty,
        "num_questions": s.num_questions,
        "language": s.language,
        "status": s.status,
        "avg_score": s.avg_score,
        "avg_communication": s.avg_communication,
        "summary": s.summary,
        "created_at": s.created_at.isoformat(),
        "answers": [_qa_out(a) for a in s.answers]
    }


@router.get("/categories")
def categories(db: Session = Depends(get_db)):
    return [
        c.name
        for c in db.query(Category)
        .filter_by(kind="interview")
        .order_by(Category.id)
    ]


@router.post("/start", status_code=201)
def start(
    body: StartIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db)
):
    cat = body.category

    if body.resume_id:
        r = db.get(Resume, body.resume_id)

        if not r or r.user_id != user.id:
            raise HTTPException(404, "Resume not found")

        cat = "Resume-Based"

    elif not db.query(Category).filter_by(
        name=cat, kind="interview"
    ).first():
        raise HTTPException(422, "Unknown category")

    s = InterviewSession(
        user_id=user.id,
        category=cat,
        mode=body.mode,
        difficulty=body.difficulty,
        num_questions=body.num_questions,
        language=body.language,
        resume_id=body.resume_id
    )

    db.add(s)
    db.flush()

    _next_question(db, s)

    db.commit()

    log(db, user.id, "interview_start", cat)

    return _session_out(s)


@router.post("/{sid}/answer")
def answer(
    sid: int,
    body: AnswerIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db)
):
    s = _owned(db, user, sid)

    if s.status != "active":
        raise HTTPException(400, "Interview already finished")

    cur = next(
        (a for a in s.answers if a.answer is None),
        None
    )

    if not cur:
        raise HTTPException(400, "No pending question")

    system = (
        "You are a fair, rigorous interview evaluator. "
        "Score the candidate's answer from 0 to 10 "
        "(0 = wrong/empty, 5 = partially correct, "
        "10 = excellent and complete). "
        "Also rate communication (clarity, structure, concision) 0-10. "
        "Be specific and constructive. "
        f"Write in {s.language}."
    )

    user_msg = (
        f"Category: {s.category} | Difficulty: {cur.difficulty}\n"
        f"Question: {cur.question}\n"
        f"Candidate answer:\n<data>{body.answer}</data>\n"
        'Return JSON: {"score": number, "communication": number, '
        '"feedback": "...", "correct_answer": "model answer", '
        '"improvements": ["...", "..."]}'
    )

    ev = complete_json(system, user_msg, 1200)

    cur.answer = body.answer
    cur.duration_seconds = body.duration_seconds

    imps = ev.get("improvements", [])

    imps = (
        [str(i) for i in imps][:6]
        if isinstance(imps, list)
        else [str(imps)]
    )

    e = Evaluation(
        answer_id=cur.id,
        score=clamp(ev.get("score")),
        communication=clamp(ev.get("communication")),
        feedback=str(ev.get("feedback", "")),
        correct_answer=str(ev.get("correct_answer", "")),
        improvements=imps
    )

    db.add(e)
    cur.evaluation = e

    record_progress(
        db, user.id, cur.topic or s.category, e.score
    )

    finished = (
        sum(1 for a in s.answers if a.answer is not None)
        >= s.num_questions
    )

    if finished:
        scores = [
            a.evaluation.score
            for a in s.answers if a.evaluation
        ]

        comms = [
            a.evaluation.communication
            for a in s.answers if a.evaluation
        ]

        s.avg_score = round(sum(scores) / len(scores), 2)
        s.avg_communication = round(sum(comms) / len(comms), 2)

        s.status = "finished"
        s.finished_at = datetime.utcnow()

        recap = "\n".join(
            f"Q{a.idx} ({a.topic}) score "
            f"{a.evaluation.score}: {a.question[:150]}"
            for a in s.answers if a.evaluation
        )

        try:
            s.summary = complete_json(
                "You are an interview coach summarising a mock interview.",
                f"Category: {s.category}\n{recap}\n"
                'Return JSON: {"overall": "2-3 sentence summary", '
                '"strengths": ["..."], "weaknesses": ["..."], '
                '"next_steps": ["..."]}',
                900
            )

        except Exception:
            s.summary = None

    else:
        _next_question(db, s)

    db.commit()

    return _session_out(s)


@router.get("/{sid}")
def get_one(
    sid: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db)
):
    return _session_out(_owned(db, user, sid))


@router.get("")
def history(
    user: User = Depends(current_user),
    db: Session = Depends(get_db)
):
    rows = (
        db.query(InterviewSession)
        .filter_by(user_id=user.id)
        .order_by(InterviewSession.id.desc())
        .limit(50)
        .all()
    )

    return [
        {
            "id": s.id,
            "category": s.category,
            "mode": s.mode,
            "status": s.status,
            "avg_score": s.avg_score,
            "avg_communication": s.avg_communication,
            "created_at": s.created_at.isoformat(),
            "questions": s.num_questions
        }
        for s in rows
    ]


@router.delete("/{sid}", status_code=204)
def delete(
    sid: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db)
):
    db.delete(_owned(db, user, sid))
    db.commit()
