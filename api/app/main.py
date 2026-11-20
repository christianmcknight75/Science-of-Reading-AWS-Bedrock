"""Reading Helper API. Phase 0: health check only."""

from fastapi import FastAPI

app = FastAPI(title="Reading Helper API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
