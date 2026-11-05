# SmartPrep AI: Interview Practice & Career Guidance Platform

React + FastAPI + SQLAlchemy (SQLite or MySQL) + Claude API.

## Verification status (please read)

| Item | Status |
|---|---|
| Backend Python files | Syntax-compiled (`py_compile`) only |
| Backend runtime, endpoints, sandbox | **Not run.** The build sandbox blocked PyPI, so dependencies could not be installed |
| Frontend build | **Not run.** The build sandbox blocked the npm registry |
| AI features (interview, resume, coach, RAG, hints, code review) | **Not run.** They need your `ANTHROPIC_API_KEY` |
| Voice/video (browser APIs) | Needs manual testing in Chrome or Edge |

Run the smoke test first (step 3 below). It checks auth, admin, aptitude, the code sandbox, file-upload validation and
clean failure when no AI key is set. Fix anything it reports before demoing.

## Folder structure

```
smartprep/
  docker-compose.yml
  backend/
    requirements.txt  .env.example  Dockerfile
    app/
      main.py  config.py  database.py (all models)  security.py  ai.py  files.py  sandbox.py  seed.py
      routers/ auth interview resume coding aptitude analytics coach rag admin
    tests/smoke_test.py
  frontend/
    package.json  vite.config.js  index.html  Dockerfile
    src/ main.jsx App.jsx api.js auth.jsx styles.css
      pages/ Landing AuthPage Dashboard Interview Resume Coding Aptitude Coach Knowledge Profile Admin
```

## Setup

### 1. Backend (Python 3.11+)
```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then edit .env
```
In `.env` set:
- `ANTHROPIC_API_KEY`: create one at console.anthropic.com. **Every AI feature needs it.**
- `SECRET_KEY`: `python -c "import secrets; print(secrets.token_urlsafe(48))"`
- `DATABASE_URL`: SQLite is the default (no setup). For MySQL, create a database and use
  `mysql+pymysql://user:password@localhost:3306/smartprep`.

### 2. Run the API
```bash
uvicorn app.main:app --reload --port 8000
```
Tables and sample data are created automatically on first start. Interactive API docs: http://localhost:8000/docs

### 3. Smoke test (no API key needed)
```bash
python -m tests.smoke_test
```

### 4. Frontend (Node 18+)
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173 (the dev server proxies `/api` to port 8000).

### Docker alternative
```bash
cp backend/.env.example backend/.env   # set ANTHROPIC_API_KEY and SECRET_KEY
docker compose up --build
```
This runs MySQL, the API (with gcc, g++, JDK and Node installed for the code sandbox) and the frontend.

## Sample accounts
| Role | Email | Password |
|---|---|---|
| Admin | admin@example.com | Admin@123 |
| Student | student@example.com | Student@123 |

Change or delete these before any real deployment. Sample data: 15 interview categories, 16 aptitude questions, 6 coding problems.

## Feature map and API summary (all under `/api`)

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/register, /auth/login, /auth/forgot-password, /auth/reset-password`, `GET/PUT /auth/me` |
| Interview | `GET /interview/categories`, `POST /interview/start`, `POST /interview/{id}/answer`, `GET /interview`, `GET/DELETE /interview/{id}` |
| Resume | `POST /resume/upload`, `GET /resume`, `POST /resume/{id}/match`, `DELETE /resume/{id}` |
| Coding | `GET /coding/problems`, `GET /coding/problems/{id}`, `POST /coding/run, /submit, /hint`, `GET /coding/languages` |
| Aptitude | `GET /aptitude/sections, /questions, /history`, `POST /aptitude/submit` |
| Analytics | `GET /analytics/summary` |
| Coach | `POST /coach/plan`, `GET /coach/plans` |
| RAG | `POST /rag/upload, /ask, /questions`, `GET /rag/documents`, `DELETE /rag/documents/{id}` |
| Admin | `/admin/stats, /users, /questions, /categories, /activity` (admin role only) |

Authenticate with `Authorization: Bearer <token>`. Import `http://localhost:8000/openapi.json` into Postman for the full collection.

## Design notes and honest limitations

- **Database:** one relational database (SQLite or MySQL) via SQLAlchemy holds everything. The brief lists MongoDB as well;
  it is not used because a second database adds no value here. Documents and chunks are stored relationally.
- **AI:** Claude (model set by `ANTHROPIC_MODEL`) generates questions, scores answers, analyses resumes, reviews code
  and builds roadmaps. If no key is set the API returns `503` with a clear message; there are no canned AI answers.
  AI scores are estimates and can be wrong.
- **RAG:** passages are retrieved with TF-IDF similarity (scikit-learn), then Claude answers from them with citations. This is
  keyword-based, not embedding-based. For large corpora, swap `_retrieve()` in `routers/rag.py` for a vector store.
- **Voice:** uses the browser Web Speech API (best in Chrome/Edge; audio may be processed by the browser vendor).
  Language support depends on the browser.
- **Video:** the camera is a local practice mirror and is never uploaded. Feedback uses only speech pace and filler words.
  There is no facial analysis, and the app makes no claims about personality or competence.
- **Code sandbox:** subprocess with CPU/memory/file limits, a timeout, a temp directory and a clean environment. It is process-level
  isolation, not a full jail. For public deployment run the API in the provided Docker container (non-root) with no
  network access for the sandbox, or move execution to a dedicated runner.
- **Password reset:** without SMTP settings the reset link is printed in the server log (dev mode).
- **Not included:** rate limiting, email verification, automated frontend tests, database migrations (Alembic). Add these before production.
