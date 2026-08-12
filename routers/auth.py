import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, field_validator
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

import models
from database import get_db
from limiter import limiter
from mailer import send_password_reset_email
from security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    get_valid_password_reset_token,
    get_valid_refresh_token,
    pwd_context,
)

router = APIRouter()
logger = logging.getLogger(__name__)

PASSWORD_MIN_LENGTH = 8


def _validate_password_strength(password: str) -> str:
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters long")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")
    if not re.search(r"[^\w\s]", password):
        raise ValueError("Password must contain at least one special character")
    return password


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, password: str) -> str:
        return _validate_password_strength(password)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, password: str) -> str:
        return _validate_password_strength(password)


@router.post("/register")
@limiter.limit("5/minute")
async def register(request: Request, credentials: RegisterRequest, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == credentials.email).first()
    if existing_user:
        logger.warning(
            "Registration attempt for existing email: %s, ip=%s",
            credentials.email,
            get_remote_address(request),
        )
        raise HTTPException(status_code=400, detail="User already exists")

    user = models.User(
        email=credentials.email,
        hashed_password=pwd_context.hash(credentials.password),
    )
    db.add(user)
    db.commit()
    logger.info("User registered: %s, ip=%s", credentials.email, get_remote_address(request))
    return {"message": f"User {credentials.email} registered"}


@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == credentials.email).first()
    if not user or not pwd_context.verify(credentials.password, user.hashed_password):
        logger.warning(
            "Failed login attempt for email: %s, ip=%s", credentials.email, get_remote_address(request)
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(user.email)
    refresh_token = create_refresh_token(user, db)
    logger.info("User logged in: %s, ip=%s", credentials.email, get_remote_address(request))
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/refresh")
@limiter.limit("10/minute")
async def refresh(request: Request, body: RefreshRequest, db: Session = Depends(get_db)):
    stored_token = get_valid_refresh_token(body.refresh_token, db, request)
    user = db.query(models.User).filter(models.User.id == stored_token.user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    stored_token.revoked = True
    new_refresh_token = create_refresh_token(user, db)
    access_token = create_access_token(user.email)
    logger.info("Access token refreshed for user: %s, ip=%s", user.email, get_remote_address(request))
    return {"access_token": access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(request: Request, body: RefreshRequest, db: Session = Depends(get_db)):
    stored_token = get_valid_refresh_token(body.refresh_token, db, request)
    stored_token.revoked = True
    db.commit()
    logger.info("User logged out: user_id=%s, ip=%s", stored_token.user_id, get_remote_address(request))
    return {"message": "Logged out"}


@router.post("/password-reset/request")
@limiter.limit("5/minute")
async def request_password_reset(request: Request, body: PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == body.email).first()
    if user is not None:
        token = create_password_reset_token(user, db)

        try:
            send_password_reset_email(user.email, token)
        except Exception:
            logger.exception("Failed to send password reset email to user_id=%s", user.id)

        logger.info(
            "Password reset token generated for user_id=%s ip=%s", user.id, get_remote_address(request)
        )
    else:
        logger.info(
            "Password reset requested for unknown email: %s, ip=%s", body.email, get_remote_address(request)
        )

    return {"message": "If an account with that email exists, a password reset token has been generated"}


@router.post("/password-reset/confirm")
@limiter.limit("5/minute")
async def confirm_password_reset(
    request: Request, body: PasswordResetConfirmRequest, db: Session = Depends(get_db)
):
    stored_token = get_valid_password_reset_token(body.token, db)
    user = db.query(models.User).filter(models.User.id == stored_token.user_id).first()
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user.hashed_password = pwd_context.hash(body.new_password)
    stored_token.used = True
    db.query(models.RefreshToken).filter(
        models.RefreshToken.user_id == user.id,
        models.RefreshToken.revoked.is_(False),
    ).update({"revoked": True})
    db.commit()
    logger.info("Password reset completed for user_id=%s, ip=%s", user.id, get_remote_address(request))
    return {"message": "Password has been reset"}
