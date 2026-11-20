"""Reading Helper API. Phase 0: health check only."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .accounts import router as accounts_router
from .admin import router as admin_router
from .config import get_settings
from .features_api import router as features_router
from .qa import router as qa_router

app = FastAPI(title="Reading Helper API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().cors_origins.split(",") if o.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(admin_router)
app.include_router(accounts_router)
app.include_router(qa_router)
app.include_router(features_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(RequestValidationError)
async def _bad_input(_: Request, exc: RequestValidationError) -> JSONResponse:
    """The app shows `detail` to teachers, so it is a plain sentence, not a validation list."""
    return JSONResponse(
        status_code=422,
        content={"detail": "Please check what you entered and try again."},
    )
