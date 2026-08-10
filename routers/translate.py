import logging
from functools import lru_cache

from deep_translator import GoogleTranslator
from deep_translator.exceptions import (
    InvalidSourceOrTargetLanguage,
    LanguageNotSupportedException,
    NotValidLength,
    NotValidPayload,
    RequestError,
    ServerException,
    TooManyRequests,
    TranslationNotFound,
)
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

import models
from database import get_db
from security import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


class TranslateRequest(BaseModel):
    text: str
    source_lang: str
    target_langs: list[str]


@lru_cache
def _get_supported_languages() -> dict[str, str]:
    return GoogleTranslator().get_supported_languages(as_dict=True)


@router.get("/languages")
async def get_languages():
    return _get_supported_languages()


@router.post("/translate")
async def translate(
    http_request: Request,
    request: TranslateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ip = get_remote_address(http_request)
    translations = {}
    for target_lang in request.target_langs:
        try:
            translated_text = GoogleTranslator(
                source=request.source_lang, target=target_lang
            ).translate(request.text)
        except (
            InvalidSourceOrTargetLanguage,
            LanguageNotSupportedException,
            NotValidLength,
            NotValidPayload,
        ):
            logger.warning(
                "Invalid translation request: user_id=%s source=%s target=%s ip=%s",
                current_user.id, request.source_lang, target_lang, ip,
            )
            raise HTTPException(
                status_code=400,
                detail=f"Invalid request for target language '{target_lang}', check language codes and text",
            )
        except TooManyRequests:
            logger.error("Translation provider rate limit reached for target=%s ip=%s", target_lang, ip)
            raise HTTPException(
                status_code=429,
                detail="Translation provider rate limit reached, try again later",
            )
        except (RequestError, ServerException, TranslationNotFound):
            logger.error("Translation provider unavailable for target=%s ip=%s", target_lang, ip)
            raise HTTPException(
                status_code=502,
                detail=f"Translation provider unavailable for target language '{target_lang}'",
            )

        translations[target_lang] = translated_text
        db.add(
            models.Translation(
                user_id=current_user.id,
                source_lang=request.source_lang,
                target_lang=target_lang,
                original_text=request.text,
                translated_text=translated_text,
            )
        )

    db.commit()
    logger.info(
        "Translation completed: user_id=%s source=%s targets=%s ip=%s",
        current_user.id, request.source_lang, list(translations.keys()), ip,
    )

    return {
        "source_lang": request.source_lang,
        "original_text": request.text,
        "translations": translations,
    }


@router.get("/translations")
async def get_translations(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(models.Translation).filter(models.Translation.user_id == current_user.id)
    total = query.count()
    history = (
        query.order_by(models.Translation.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": t.id,
                "source_lang": t.source_lang,
                "target_lang": t.target_lang,
                "original_text": t.original_text,
                "translated_text": t.translated_text,
                "created_at": t.created_at,
            }
            for t in history
        ],
    }
