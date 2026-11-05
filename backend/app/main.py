from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .database import Base, engine
from .routers import admin, aptitude, analytics, auth, coach, coding, interview, rag, resume
from .seed import seed

app = FastAPI(title="SmartPrep AI API", version="1.0.0",
              description="AI interview practice & career guidance platform. Interactive docs at /docs.")
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

for r in (auth, interview, resume, coding, aptitude, analytics, coach, rag, admin):
    app.include_router(r.router, prefix="/api")


@app.on_event("startup")
def startup():
    Base.metadata.create_all(engine)
    seed()


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    msgs = [f"{'.'.join(str(p) for p in e['loc'][1:])}: {e['msg']}" for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": "; ".join(msgs)})


@app.get("/api/health")
def health():
    return {"status": "ok", "ai_configured": bool(settings.GROQ_API_KEY)}
