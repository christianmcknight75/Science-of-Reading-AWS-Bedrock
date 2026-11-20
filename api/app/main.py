"""Reading Helper API. Phase 0: health check only."""

from fastapi import FastAPI

from .admin import router as admin_router

app = FastAPI(title="Reading Helper API", version="0.1.0")
app.include_router(admin_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
