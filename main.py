import logging

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse, Response
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from limiter import limiter
from logging_config import configure_logging
from routers import auth, favorites, translate

configure_logging()
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

APP_VERSION = "1.1.0"

app = FastAPI()

app.state.limiter = limiter


def handle_rate_limit_exceeded(request: Request, exc: Exception) -> Response:
    assert isinstance(exc, RateLimitExceeded)
    logger.warning("Rate limit exceeded for ip=%s on %s", get_remote_address(request), request.url.path)
    return JSONResponse({"error": f"Rate limit exceeded: {exc.detail}"}, status_code=429)


app.add_exception_handler(RateLimitExceeded, handle_rate_limit_exceeded)

app.include_router(auth.router)
app.include_router(translate.router)
app.include_router(favorites.router)


@app.get("/version")
async def get_version():
    return {"version": APP_VERSION}


@app.get("/health")
async def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Health check failed: database unreachable")
        return JSONResponse({"status": "unhealthy", "database": "unreachable"}, status_code=503)
    return {"status": "ok", "database": "reachable"}
