import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

import models
from database import get_db
from limiter import limiter
from security import create_access_token, create_refresh_token, get_valid_refresh_token, pwd_context

router = APIRouter()
logger = logging.getLogger(__name__)

PASSWORD_MIN_LENGTH = 8


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


@router.post("/register")
@limiter.limit("5/minute")
async def register(request: Request, credentials: RegisterRequest, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == credentials.email).first()
    if existing_user:
        logger.warning("Registration attempt for existing email: %s", credentials.email)
        raise HTTPException(status_code=400, detail="User already exists")

    user = models.User(
        email=credentials.email,
        hashed_password=pwd_context.hash(credentials.password),
    )
    db.add(user)
    db.commit()
    logger.info("User registered: %s", credentials.email)
    return {"message": f"User {credentials.email} registered"}


@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == credentials.email).first()
    if not user or not pwd_context.verify(credentials.password, user.hashed_password):
        logger.warning("Failed login attempt for email: %s", credentials.email)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(user.email)
    refresh_token = create_refresh_token(user, db)
    logger.info("User logged in: %s", credentials.email)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/refresh")
@limiter.limit("10/minute")
async def refresh(request: Request, body: RefreshRequest, db: Session = Depends(get_db)):
    stored_token = get_valid_refresh_token(body.refresh_token, db)
    user = db.query(models.User).filter(models.User.id == stored_token.user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    stored_token.revoked = True
    new_refresh_token = create_refresh_token(user, db)
    access_token = create_access_token(user.email)
    logger.info("Access token refreshed for user: %s", user.email)
    return {"access_token": access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(body: RefreshRequest, db: Session = Depends(get_db)):
    stored_token = get_valid_refresh_token(body.refresh_token, db)
    stored_token.revoked = True
    db.commit()
    logger.info("User logged out: user_id=%s", stored_token.user_id)
    return {"message": "Logged out"}
