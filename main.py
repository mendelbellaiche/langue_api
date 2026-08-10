from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from database import Base, engine
from limiter import limiter
from routers import auth, translate

Base.metadata.create_all(bind=engine)

APP_VERSION = "1.1.0"

app = FastAPI()

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth.router)
app.include_router(translate.router)


@app.get("/version")
async def get_version():
    return {"version": APP_VERSION}
