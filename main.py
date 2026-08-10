import os
from datetime import datetime, timedelta, timezone

from deep_translator import GoogleTranslator
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

import models
from database import Base, engine, get_db
from models import User

Base.metadata.create_all(bind=engine)

APP_VERSION = "1.0.0"

app = FastAPI()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

JWT_SECRET_KEY = os.environ["JWT_SECRET_KEY"]
JWT_ALGORITHM = "HS256"
JWT_EXPIRES_MINUTES = 60


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TranslateRequest(BaseModel):
    text: str
    source_lang: str
    target_langs: list[str]


def create_access_token(email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRES_MINUTES)
    payload = {"sub": email, "exp": expire}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> type[User]:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@app.post("/register")
async def register(credentials: LoginRequest, db: Session = Depends(get_db)):
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


@app.post("/login")
async def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == credentials.email).first()
    if not user or not pwd_context.verify(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(user.email)
    return {"access_token": token, "token_type": "bearer"}


@app.get("/version")
async def get_version():
    return {"version": APP_VERSION}


@app.get("/languages")
async def get_languages():
    return GoogleTranslator().get_supported_languages(as_dict=True)


@app.post("/translate")
async def translate(request: TranslateRequest, current_user: models.User = Depends(get_current_user)):
    translations = {}
    for target_lang in request.target_langs:
        try:
            translations[target_lang] = GoogleTranslator(
                source=request.source_lang, target=target_lang
            ).translate(request.text)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail=f"Translation failed for target language '{target_lang}', check language codes",
            )

    return {
        "source_lang": request.source_lang,
        "original_text": request.text,
        "translations": translations,
    }
