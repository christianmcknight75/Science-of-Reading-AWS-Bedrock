"""Reading Helper API. Phase 0: health check only."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .admin import router as admin_router
from .qa import router as qa_router

app = FastAPI(title="Reading Helper API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # local dev only
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(admin_router)
app.include_router(qa_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
