from typing import Literal

from fastapi import APIRouter, Path, Query

from app.core.errors import AppError
from app.database import repository
from app.schemas.scan import (
    ClearResponse,
    ScanListResponse,
    ScanResult,
    SeedResponse,
    StatsResponse,
)
from app.services import scan_service

router = APIRouter(tags=["history"])

SCAN_ID = Path(pattern=r"^[a-f0-9]{32}$", description="32-character hex scan id")


@router.get("/scans", response_model=ScanListResponse)
def list_scans(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    category: Literal["low", "suspicious", "high"] | None = None,
    input_type: Literal["url", "email"] | None = None,
) -> ScanListResponse:
    items, total = repository.list_scans(limit=limit, offset=offset, category=category, input_type=input_type)
    return ScanListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/scans/{scan_id}", response_model=ScanResult)
def get_scan(scan_id: str = SCAN_ID) -> ScanResult:
    return scan_service.fetch_scan(scan_id)


@router.delete("/scans", response_model=ClearResponse)
def clear_scans(confirm: bool = False, demo_only: bool = False) -> ClearResponse:
    """Delete local scan history. Requires ?confirm=true so it cannot happen by accident."""
    if not confirm:
        raise AppError("Add confirm=true to delete scan history.", code="confirmation_required", status_code=400)
    return ClearResponse(deleted=repository.clear_scans(demo_only=demo_only))


@router.get("/stats", response_model=StatsResponse)
def stats() -> StatsResponse:
    return repository.get_stats()


@router.post("/demo/seed", response_model=SeedResponse)
def seed_demo() -> SeedResponse:
    """Add clearly-labelled DEMO scans (synthetic inputs) so the dashboard is not empty."""
    inserted = scan_service.seed_demo_data()
    note = (
        "Demo scans added. They use synthetic example inputs and are marked DEMO everywhere."
        if inserted
        else "Demo data already exists; nothing was added."
    )
    return SeedResponse(inserted=inserted, note=note)
