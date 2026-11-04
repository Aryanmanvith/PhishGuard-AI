from fastapi import APIRouter

from app.schemas.scan import EmailRequest, ScanResult, UrlRequest
from app.services import scan_service

router = APIRouter(prefix="/analyze", tags=["analysis"])


@router.post("/url", response_model=ScanResult)
def analyze_url_endpoint(payload: UrlRequest) -> ScanResult:
    """Static analysis of a URL. The URL is never opened or fetched."""
    return scan_service.scan_url(payload.url)


@router.post("/email", response_model=ScanResult)
def analyze_email_endpoint(payload: EmailRequest) -> ScanResult:
    """Analyze pasted email text locally. The raw body is not stored."""
    return scan_service.scan_email(payload.body, payload.sender, payload.reply_to, payload.subject)
