from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import engine, Base
import app.models  # noqa: F401 — ensure all ORM models are registered before create_all
from app.api.v1_auth import router as auth_router
from app.api.v1_content import router as content_router
from app.api.v1_telemetry import router as telemetry_router
from app.api.v1_manager import router as manager_router

app = FastAPI(title="OnboardIQ API", redirect_slashes=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)


app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(content_router, prefix="/api/v1/content", tags=["Content"])
app.include_router(telemetry_router, prefix="/api/v1/telemetry", tags=["Telemetry"])
app.include_router(manager_router, prefix="/api/v1/manager", tags=["Manager"])


@app.get("/health")
def health_check():
    return {"status": "ok"}
