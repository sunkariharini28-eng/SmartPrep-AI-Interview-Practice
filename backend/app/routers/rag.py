from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..ai import complete_json
from ..config import settings
from ..database import Chunk, Document, User, get_db, log
from ..files import chunk_text, extract_text, save_upload
from ..security import current_user

router = APIRouter(prefix="/rag", tags=["rag"])


class AskIn(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    document_id: int | None = None


class GenIn(BaseModel):
    document_id: int
    count: int = Field(5, ge=1, le=15)


def _retrieve(db, user, question, document_id=None, k=5):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    q = db.query(Chunk).filter_by(user_id=user.id)
    if document_id:
        q = q.filter_by(document_id=document_id)
    chunks = q.all()
    if not chunks:
        raise HTTPException(404, "No indexed documents. Upload study material first.")
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
    mat = vec.fit_transform([c.text for c in chunks] + [question])
    sims = cosine_similarity(mat[-1], mat[:-1]).ravel()
    order = sims.argsort()[::-1][:k]
    docs = {d.id: d.filename for d in db.query(Document).filter_by(user_id=user.id)}
    return [(chunks[i], float(sims[i]), docs.get(chunks[i].document_id, "?")) for i in order if sims[i] > 0]


@router.post("/upload", status_code=201)
async def upload(file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    orig, stored, path = await save_upload(file, {".pdf", ".docx", ".txt", ".md"}, f"docs/{user.id}")
    text = extract_text(path)
    parts = chunk_text(text)
    d = Document(user_id=user.id, filename=orig, stored_name=stored, chunk_count=len(parts))
    db.add(d)
    db.flush()
    db.add_all([Chunk(document_id=d.id, user_id=user.id, idx=i, text=t) for i, t in enumerate(parts)])
    db.commit()
    log(db, user.id, "rag_upload", orig)
    return {"id": d.id, "filename": orig, "chunks": len(parts)}


@router.get("/documents")
def documents(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [{"id": d.id, "filename": d.filename, "chunks": d.chunk_count, "created_at": d.created_at.isoformat()}
            for d in db.query(Document).filter_by(user_id=user.id).order_by(Document.id.desc())]


@router.delete("/documents/{did}", status_code=204)
def delete_doc(did: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = db.get(Document, did)
    if not d or d.user_id != user.id:
        raise HTTPException(404, "Document not found")
    (Path(settings.UPLOAD_DIR) / f"docs/{user.id}" / d.stored_name).unlink(missing_ok=True)
    db.query(Chunk).filter_by(document_id=did).delete()
    db.delete(d)
    db.commit()


@router.post("/ask")
def ask(body: AskIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    hits = _retrieve(db, user, body.question, body.document_id)
    if not hits:
        return {"answer": "I couldn't find anything relevant in your uploaded documents.", "sources": []}
    ctx = "\n\n".join(f"[{i + 1}] ({name}) {c.text}" for i, (c, _, name) in enumerate(hits))
    res = complete_json(
        "Answer the question using ONLY the numbered context passages. Cite passages like [1]. "
        "If the context does not contain the answer, say so.",
        f"Question: {body.question}\n<data>{ctx}</data>\nReturn JSON: {{\"answer\": \"...\"}}", 1200)
    return {"answer": res.get("answer", ""),
            "sources": [{"ref": i + 1, "document": name, "chunk": c.idx, "score": round(s, 3), "snippet": c.text[:300]}
                        for i, (c, s, name) in enumerate(hits)]}


@router.post("/questions")
def gen_questions(body: GenIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = db.get(Document, body.document_id)
    if not d or d.user_id != user.id:
        raise HTTPException(404, "Document not found")
    chunks = db.query(Chunk).filter_by(document_id=d.id).order_by(Chunk.idx).all()
    step = max(1, len(chunks) // 8)
    sample = "\n\n".join(f"[chunk {c.idx}] {c.text}" for c in chunks[::step][:8])
    return complete_json(
        "You write interview questions strictly grounded in the provided study material.",
        f"Document: {d.filename}\n<data>{sample}</data>\nCreate {body.count} questions. Return JSON: "
        '{"questions": [{"question":"...","difficulty":"easy|medium|hard","model_answer":"...","source_chunk": number}]}', 3000)
