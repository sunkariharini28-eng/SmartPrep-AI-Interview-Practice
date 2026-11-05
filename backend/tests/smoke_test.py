"""Smoke test for everything that does not need an AI key.
Run from backend/:   python -m tests.smoke_test
Uses a throwaway SQLite file, so it never touches your real database."""
import os
import tempfile

tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/test.db"
os.environ["UPLOAD_DIR"] = f"{tmp}/uploads"
os.environ["ANTHROPIC_API_KEY"] = ""

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

failures = []


def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  {extra}" if not cond else ""))
    if not cond:
        failures.append(name)


with TestClient(app) as c:
    check("health", c.get("/api/health").json()["status"] == "ok")

    # auth
    r = c.post("/api/auth/register", json={"name": "Test User", "email": "t@example.com", "password": "Passw0rdX"})
    check("register", r.status_code == 201, r.text)
    check("duplicate email rejected", c.post("/api/auth/register", json={"name": "Test User", "email": "t@example.com", "password": "Passw0rdX"}).status_code == 409)
    check("weak password rejected", c.post("/api/auth/register", json={"name": "Weak", "email": "w@example.com", "password": "short"}).status_code == 422)
    check("bad login rejected", c.post("/api/auth/login", json={"email": "t@example.com", "password": "nope12345"}).status_code == 401)
    tok = c.post("/api/auth/login", json={"email": "t@example.com", "password": "Passw0rdX"}).json()["token"]
    H = {"Authorization": f"Bearer {tok}"}
    check("protected route needs token", c.get("/api/auth/me").status_code == 401)
    check("me", c.get("/api/auth/me", headers=H).json()["email"] == "t@example.com")
    check("profile update", c.put("/api/auth/me", headers=H, json={"target_role": "SDE", "skills": ["Python"]}).json()["target_role"] == "SDE")
    check("forgot password generic", c.post("/api/auth/forgot-password", json={"email": "nobody@example.com"}).status_code == 200)
    check("student blocked from admin", c.get("/api/admin/stats", headers=H).status_code == 403)

    # admin
    at = c.post("/api/auth/login", json={"email": "admin@example.com", "password": "Admin@123"}).json()["token"]
    AH = {"Authorization": f"Bearer {at}"}
    check("admin stats", c.get("/api/admin/stats", headers=AH).json()["users"] >= 3)
    check("admin users", len(c.get("/api/admin/users", headers=AH).json()) >= 3)
    check("admin add category", c.post("/api/admin/categories", headers=AH, json={"name": "Go", "kind": "interview"}).status_code == 201)
    check("admin activity", len(c.get("/api/admin/activity", headers=AH).json()) > 0)

    # categories / interview without AI key must fail cleanly, not crash
    check("interview categories", len(c.get("/api/interview/categories").json()) >= 15)
    r = c.post("/api/interview/start", headers=H, json={"category": "Python"})
    check("interview without key -> 503", r.status_code == 503, r.text)

    # aptitude
    qs = c.get("/api/aptitude/questions?section=Quantitative&n=5", headers=H).json()
    check("aptitude questions hide answers", len(qs) == 5 and "answer_index" not in qs[0])
    r = c.post("/api/aptitude/submit", headers=H, json={"section": "Quantitative", "answers": {str(qs[0]["id"]): 0}, "question_ids": [q["id"] for q in qs], "duration_seconds": 30})
    check("aptitude scoring", r.status_code == 200 and r.json()["total"] == 5, r.text)

    # coding sandbox
    probs = c.get("/api/coding/problems", headers=H).json()
    check("coding problems", len(probs) >= 5)
    langs = c.get("/api/coding/languages", headers=H).json()
    print("INFO runtimes available:", langs)
    pid = probs[0]["id"]
    if langs.get("python"):
        r = c.post("/api/coding/run", headers=H, json={"language": "python", "code": "print(sum(map(int, input().split())))", "stdin": "3 4"})
        check("python run", r.json()["stdout"].strip() == "7", r.text)
        r = c.post("/api/coding/run", headers=H, json={"language": "python", "code": "while True: pass"})
        check("infinite loop is stopped", r.json()["status"] in ("timeout", "runtime_error"), r.text)
        r = c.post("/api/coding/submit", headers=H, json={"problem_id": pid, "language": "python", "code": "print(sum(map(int, input().split())))"})
        check("submit passes all tests", r.status_code == 200 and r.json()["passed"] == r.json()["total"], r.text)
    # analytics
    s = c.get("/api/analytics/summary", headers=H).json()
    check("analytics reflects aptitude", s["aptitude_score_pct"] is not None)

    # uploads validation
    r = c.post("/api/resume/upload", headers=H, files={"file": ("evil.exe", b"MZ....", "application/octet-stream")})
    check("bad extension rejected", r.status_code == 415)
    r = c.post("/api/resume/upload", headers=H, files={"file": ("fake.pdf", b"not a pdf at all", "application/pdf")})
    check("fake pdf rejected", r.status_code == 415)
    r = c.post("/api/rag/upload", headers=H, files={"file": ("notes.txt", b"A stack is a LIFO data structure. A queue is FIFO. " * 5, "text/plain")})
    check("rag upload", r.status_code == 201, r.text)
    r = c.get("/api/rag/documents", headers=H)
    check("rag list", len(r.json()) == 1)
    r = c.post("/api/rag/ask", headers=H, json={"question": "What is a stack?"})
    check("rag ask without key -> 503", r.status_code == 503, r.text)

print("\nFAILED:" if failures else "\nAll checks passed.", failures or "")
raise SystemExit(1 if failures else 0)
