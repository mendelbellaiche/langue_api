import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

import models
from database import get_db
from security import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


class FavoriteCreateRequest(BaseModel):
    source_lang: str
    target_lang: str
    original_text: str
    translated_text: str


class FavoriteUpdateRequest(BaseModel):
    source_lang: str
    target_lang: str
    original_text: str
    translated_text: str


def _get_owned_favorite(favorite_id: int, current_user: models.User, db: Session) -> models.Favorite:
    favorite = (
        db.query(models.Favorite)
        .filter(models.Favorite.id == favorite_id, models.Favorite.user_id == current_user.id)
        .first()
    )
    if favorite is None:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return favorite


def _serialize(favorite: models.Favorite) -> dict:
    return {
        "id": favorite.id,
        "source_lang": favorite.source_lang,
        "target_lang": favorite.target_lang,
        "original_text": favorite.original_text,
        "translated_text": favorite.translated_text,
        "created_at": favorite.created_at,
        "updated_at": favorite.updated_at,
    }


@router.post("/favorites")
async def create_favorite(
    request: FavoriteCreateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    favorite = models.Favorite(
        user_id=current_user.id,
        source_lang=request.source_lang,
        target_lang=request.target_lang,
        original_text=request.original_text,
        translated_text=request.translated_text,
    )
    db.add(favorite)
    db.commit()
    db.refresh(favorite)
    logger.info("Favorite created: id=%s user_id=%s", favorite.id, current_user.id)
    return _serialize(favorite)


@router.get("/favorites")
async def get_favorites(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    source_lang: str | None = Query(default=None),
    target_lang: str | None = Query(default=None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(models.Favorite).filter(models.Favorite.user_id == current_user.id)
    if source_lang is not None:
        query = query.filter(models.Favorite.source_lang == source_lang)
    if target_lang is not None:
        query = query.filter(models.Favorite.target_lang == target_lang)
    total = query.count()
    favorites = query.order_by(models.Favorite.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [_serialize(favorite) for favorite in favorites],
    }


@router.put("/favorites/{favorite_id}")
async def update_favorite(
    favorite_id: int,
    request: FavoriteUpdateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    favorite = _get_owned_favorite(favorite_id, current_user, db)
    favorite.source_lang = request.source_lang
    favorite.target_lang = request.target_lang
    favorite.original_text = request.original_text
    favorite.translated_text = request.translated_text
    db.commit()
    db.refresh(favorite)
    logger.info("Favorite updated: id=%s user_id=%s", favorite.id, current_user.id)
    return _serialize(favorite)


@router.delete("/favorites/{favorite_id}")
async def delete_favorite(
    favorite_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    favorite = _get_owned_favorite(favorite_id, current_user, db)
    db.delete(favorite)
    db.commit()
    logger.info("Favorite deleted: id=%s user_id=%s", favorite_id, current_user.id)
    return {"message": "Favorite deleted"}
