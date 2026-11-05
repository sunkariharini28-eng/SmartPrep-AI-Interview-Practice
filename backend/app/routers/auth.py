import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from ..config import settings
from ..database import User, get_db, log
from ..security import (create_token, current_user, hash_password, hash_token, new_reset_token,
                        validate_password, verify_password)

router = APIRouter(prefix="/auth", tags=["auth"])


def user_out(u: User) -> dict:
    return {"id": u.id, "name": u.name, "email": u.email, "role": u.role, "target_role": u.target_role,
            "skills": u.skills or [], "bio": u.bio, "created_at": u.created_at.isoformat()}


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ProfileIn(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    target_role: str | None = Field(None, max_length=120)
    skills: list[str] | None = None
    bio: str | None = Field(None, max_length=1000)


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str
    password: str


@router.post("/register", status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    validate_password(body.password)
    email = body.email.lower()
    if db.query(User).filter_by(email=email).first():
        raise HTTPException(409, "Email already registered")
    u = User(name=body.name.strip(), email=email, password_hash=hash_password(body.password))
    db.add(u)
    db.commit()
    log(db, u.id, "register", email)
    return {"token": create_token(u), "user": user_out(u)}


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    u = db.query(User).filter_by(email=body.email.lower()).first()
    if not u or not verify_password(body.password, u.password_hash):
        raise HTTPException(401, "Invalid email or password")
    if not u.is_active:
        raise HTTPException(403, "Account disabled")
    log(db, u.id, "login", u.email)
    return {"token": create_token(u), "user": user_out(u)}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return user_out(user)


@router.put("/me")
def update_me(body: ProfileIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    data = body.model_dump(exclude_none=True)
    if "skills" in data:
        data["skills"] = [s.strip()[:40] for s in data["skills"] if s.strip()][:40]
    for k, v in data.items():
        setattr(user, k, v)
    db.commit()
    return user_out(user)


def _send_reset(email: str, link: str):
    if not settings.SMTP_HOST:
        print(f"\n[DEV] Password reset link for {email}: {link}\n", flush=True)
        return
    msg = EmailMessage()
    msg["Subject"] = "Reset your SmartPrep password"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = email
    msg.set_content(f"Use this link to reset your password (valid for 30 minutes):\n{link}")
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as s:
            s.starttls()
            if settings.SMTP_USER:
                s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            s.send_message(msg)
    except Exception as e:
        print(f"[WARN] SMTP send failed: {e}", flush=True)


@router.post("/forgot-password")
def forgot(body: ForgotIn, db: Session = Depends(get_db)):
    u = db.query(User).filter_by(email=body.email.lower()).first()
    if u and u.is_active:
        raw, hashed = new_reset_token()
        u.reset_token_hash, u.reset_expires = hashed, datetime.utcnow() + timedelta(minutes=30)
        db.commit()
        _send_reset(u.email, f"{settings.FRONTEND_URL}/reset?token={raw}")
    # Same response whether or not the account exists (prevents account enumeration).
    return {"message": "If that email is registered, a reset link has been sent."}


@router.post("/reset-password")
def reset(body: ResetIn, db: Session = Depends(get_db)):
    validate_password(body.password)
    u = db.query(User).filter_by(reset_token_hash=hash_token(body.token)).first()
    if not u or not u.reset_expires or u.reset_expires < datetime.utcnow():
        raise HTTPException(400, "Invalid or expired reset token")
    u.password_hash = hash_password(body.password)
    u.reset_token_hash, u.reset_expires = None, None
    db.commit()
    log(db, u.id, "password_reset", u.email)
    return {"message": "Password updated. You can now log in."}
