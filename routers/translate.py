from deep_translator import GoogleTranslator
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

import models
from database import get_db
from security import get_current_user

router = APIRouter()


class TranslateRequest(BaseModel):
    text: str
    source_lang: str
    target_langs: list[str]


@router.get("/languages")
async def get_languages():
    return GoogleTranslator().get_supported_languages(as_dict=True)


@router.post("/translate")
async def translate(
    request: TranslateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    translations = {}
    for target_lang in request.target_langs:
        try:
            translated_text = GoogleTranslator(
                source=request.source_lang, target=target_lang
            ).translate(request.text)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail=f"Translation failed for target language '{target_lang}', check language codes",
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

    return {
        "source_lang": request.source_lang,
        "original_text": request.text,
        "translations": translations,
    }


@router.get("/translations")
async def get_translations(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    history = (
        db.query(models.Translation)
        .filter(models.Translation.user_id == current_user.id)
        .order_by(models.Translation.created_at.desc())
        .all()
    )
    return [
        {
            "id": t.id,
            "source_lang": t.source_lang,
            "target_lang": t.target_lang,
            "original_text": t.original_text,
            "translated_text": t.translated_text,
            "created_at": t.created_at,
        }
        for t in history
    ]
