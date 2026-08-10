from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from slowapi.errors import RateLimitExceeded

from database import Base, engine
from limiter import limiter
from routers import auth, translate

Base.metadata.create_all(bind=engine)

APP_VERSION = "1.1.0"

app = FastAPI()

app.state.limiter = limiter


def handle_rate_limit_exceeded(request: Request, exc: Exception) -> Response:
    assert isinstance(exc, RateLimitExceeded)
    return JSONResponse({"error": f"Rate limit exceeded: {exc.detail}"}, status_code=429)


app.add_exception_handler(RateLimitExceeded, handle_rate_limit_exceeded)

app.include_router(auth.router)
app.include_router(translate.router)


@app.get("/version")
async def get_version():
    return {"version": APP_VERSION}
