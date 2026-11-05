import os
import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from .config import settings


def _magic_ok(ext: str, head: bytes) -> bool:
    if ext == ".pdf":
        return head.startswith(b"%PDF")
    if ext == ".docx":
        return head.startswith(b"PK")
    return True


async def save_upload(file: UploadFile, allowed: set[str], subdir: str) -> tuple[str, str, Path]:
    """Validate extension, size and magic bytes; store under a random name. Returns (orig_name, stored_name, path)."""
    orig = os.path.basename(file.filename or "file")
    ext = Path(orig).suffix.lower()
    if ext not in allowed:
        raise HTTPException(415, f"Unsupported file type. Allowed: {', '.join(sorted(allowed))}")
    data = await file.read(settings.MAX_UPLOAD_MB * 1024 * 1024 + 1)
    if len(data) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"File too large (max {settings.MAX_UPLOAD_MB} MB)")
    if not data:
        raise HTTPException(422, "Empty file")
    if not _magic_ok(ext, data[:8]):
        raise HTTPException(415, "File content does not match its extension")
    folder = Path(settings.UPLOAD_DIR) / subdir
    folder.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid.uuid4().hex}{ext}"
    path = folder / stored
    path.write_bytes(data)
    return orig, stored, path


def extract_text(path: Path) -> str:
    ext = path.suffix.lower()
    try:
        if ext == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            text = "\n".join((p.extract_text() or "") for p in reader.pages)
        elif ext == ".docx":
            import docx
            d = docx.Document(str(path))
            parts = [p.text for p in d.paragraphs]
            for t in d.tables:
                for row in t.rows:
                    parts.append(" | ".join(c.text for c in row.cells))
            text = "\n".join(parts)
        else:
            text = path.read_text(errors="ignore")
    except Exception:
        path.unlink(missing_ok=True)
        raise HTTPException(422, "Could not read this file. It may be corrupted or password-protected.")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) < 20:
        path.unlink(missing_ok=True)
        raise HTTPException(422, "No readable text found (scanned images are not supported).")
    return text


def chunk_text(text: str, size: int = 900, overlap: int = 150) -> list[str]:
    chunks, i = [], 0
    while i < len(text):
        chunks.append(text[i:i + size])
        i += size - overlap
    return chunks
