from fastapi import APIRouter

from app.api import analyze, health, model, reports, scans

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(analyze.router)
api_router.include_router(scans.router)
api_router.include_router(reports.router)
api_router.include_router(model.router)
