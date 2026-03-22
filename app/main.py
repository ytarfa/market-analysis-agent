from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(
    title="Market Analysis Agent",
    description="Agentic market intelligence system for e-commerce",
    version="0.1.0",
)

app.include_router(router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
