import json

from fastapi import APIRouter, Path, Response

from app.database import repository
from app.services import scan_service
from app.services.report_service import build_history_csv, build_scan_report

router = APIRouter(tags=["reports"])


@router.get("/scans/{scan_id}/report.json")
def scan_report(scan_id: str = Path(pattern=r"^[a-f0-9]{32}$")) -> Response:
    scan = scan_service.fetch_scan(scan_id)
    body = json.dumps(build_scan_report(scan), indent=2, ensure_ascii=False)
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="phishguard-report-{scan_id[:8]}.json"'},
    )


@router.get("/reports/history.csv")
def history_csv() -> Response:
    content = build_history_csv(repository.iter_all_scans())
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="phishguard-history.csv"'},
    )
