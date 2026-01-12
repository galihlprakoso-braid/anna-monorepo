from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.core.config import get_settings
from data.core.database import init_db
from api.task.router import router as task_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize on startup."""
    print("Initializing database...")
    init_db()
    print("Database ready!")
    yield

app = FastAPI(
    title="ANNA Task API",
    version="0.1.0",
    description="Task management API for ANNA",
    lifespan=lifespan
)

# CORS (switchable)
settings = get_settings()
if settings.bypass_cors:
    # Development mode: Allow all origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # Production mode: Strict CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Routes
app.include_router(task_router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload
    )
