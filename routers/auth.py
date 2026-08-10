from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

import models
from database import get_db
from limiter import limiter
from security import create_access_token, pwd_context

router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/register")
@limiter.limit("5/minute")
async def register(request: Request, credentials: LoginRequest, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == credentials.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    user = models.User(
        email=credentials.email,
        hashed_password=pwd_context.hash(credentials.password),
    )
    db.add(user)
    db.commit()
    return {"message": f"User {credentials.email} registered"}


@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == credentials.email).first()
    if not user or not pwd_context.verify(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(user.email)
    return {"access_token": token, "token_type": "bearer"}
