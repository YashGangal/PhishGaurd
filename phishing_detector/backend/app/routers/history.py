"""Scan history endpoints."""

from math import ceil
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.models.database import ScanHistory, get_db
from app.schemas.schemas import HistoryResponse, Pagination

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=HistoryResponse)
def get_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    prediction: Literal["phishing", "legitimate"] | None = None,
    db: Session = Depends(get_db),
) -> HistoryResponse:
    """Return newest scans with optional prediction filtering."""

    query = db.query(ScanHistory)
    if prediction:
        query = query.filter(ScanHistory.prediction == prediction)
    total = query.count()
    rows = query.order_by(ScanHistory.scanned_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    items = [{"scan_id": row.id, "url": row.url, "prediction": row.prediction, "confidence": row.confidence, "risk_level": row.risk_level, "needs_review": bool(row.needs_review), "blocklist_hit": bool(row.blocklist_hit), "scanned_at": row.scanned_at} for row in rows]
    return HistoryResponse(items=items, pagination=Pagination(page=page, per_page=per_page, total_items=total, total_pages=ceil(total / per_page) if total else 0))


@router.delete("/{scan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scan(scan_id: int, db: Session = Depends(get_db)) -> Response:
    """Delete one scan history row by id."""

    row = db.query(ScanHistory).filter(ScanHistory.id == scan_id).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
