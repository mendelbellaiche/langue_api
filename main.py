import logging
import os

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse, Response
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.middleware.cors import CORSMiddleware

from database import Base, engine, get_db
from limiter import limiter
from logging_config import configure_logging
from routers import auth, favorites, translate

configure_logging()
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

APP_VERSION = "1.1.0"

app = FastAPI()

allowed_origins = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,  # type: ignore[arg-type]
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)



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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
