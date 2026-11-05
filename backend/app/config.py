import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-key-change-me-please-0123456789")
    ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "720"))
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./smartprep.db")
    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "5"))
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM = os.getenv("SMTP_FROM", "no-reply@smartprep.local")
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
    CODE_TIMEOUT_SECONDS = int(os.getenv("CODE_TIMEOUT_SECONDS", "5"))


settings = Settings()
