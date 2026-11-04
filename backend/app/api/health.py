from fastapi import APIRouter

from app.core.config import get_settings
from app.database.db import check_db
from app.schemas.scan import HealthResponse
from app.services.ml_service import get_ml_service

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Used by run.bat / the frontend to confirm the backend is up."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.version,
        model_available=get_ml_service().available,
        database_ok=check_db(),
    )
