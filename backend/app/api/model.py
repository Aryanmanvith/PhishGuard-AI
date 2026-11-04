from typing import Any

from fastapi import APIRouter

from app.services.ml_service import get_ml_service

router = APIRouter(tags=["model"])


@router.get("/model")
def model_info() -> dict[str, Any]:
    """Training metadata and evaluation metrics, exactly as recorded by ml/train.py.

    If no model has been trained, returns {"available": false, "reason": "..."}.
    """
    return get_ml_service().describe()
