import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

import models
from database import get_db
from models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

JWT_SECRET_KEY = os.environ["JWT_SECRET_KEY"]
JWT_ALGORITHM = "HS256"
JWT_EXPIRES_MINUTES = 15
REFRESH_TOKEN_EXPIRES_DAYS = 7
MAX_ACTIVE_REFRESH_TOKENS_PER_USER = 5


def utcnow_naive() -> datetime:
    """UTC now without tzinfo, matching the naive DateTime columns stored in the DB."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def create_access_token(email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRES_MINUTES)
    payload = {"sub": email, "exp": expire}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _enforce_active_refresh_token_limit(user: User, db: Session) -> None:
    active_tokens = (
        db.query(models.RefreshToken)
        .filter(
            models.RefreshToken.user_id == user.id,
            models.RefreshToken.revoked.is_(False),
            models.RefreshToken.expires_at >= utcnow_naive(),
        )
        .order_by(models.RefreshToken.created_at.desc())
        .all()
    )
    for stale_token in active_tokens[MAX_ACTIVE_REFRESH_TOKENS_PER_USER - 1 :]:
        stale_token.revoked = True


def create_refresh_token(user: User, db: Session) -> str:
    _enforce_active_refresh_token_limit(user, db)

    token = secrets.token_urlsafe(32)
    expires_at = utcnow_naive() + timedelta(days=REFRESH_TOKEN_EXPIRES_DAYS)
    db.add(
        models.RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(token),
            expires_at=expires_at,
        )
    )
    db.commit()
    return token


def get_valid_refresh_token(token: str, db: Session) -> models.RefreshToken:
    token_hash = hash_refresh_token(token)
    stored = db.query(models.RefreshToken).filter(models.RefreshToken.token_hash == token_hash).first()

    if stored is None or stored.revoked or stored.expires_at < utcnow_naive():
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    return stored


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
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
