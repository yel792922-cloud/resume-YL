"""Export routes: download the current user's analysis as CSV / JSON / XLSX.

CSV/JSON stay a flat fact dump (backward compatible). XLSX is a structured,
multi-sheet analysis workbook. All respect the raw/clean analysis mode.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy.orm import Session

from app.analysis import document_facts
from app.api.ownership import get_owned_document
from app.auth.deps import get_current_user
from app.core.db import get_db
from app.models.document import Document
from app.models.user import User
from app.summary import build_workbook, facts_to_csv, facts_to_json

router = APIRouter(prefix="/api/documents", tags=["export"])

_XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _facts(db: Session, document: Document, mode: str):
    # CSV/JSON default to raw for backward compatibility; ?mode=clean opts in.
    return document_facts(db, document, mode)


@router.get("/{document_id}/export.csv")
def export_csv(
    document_id: str,
    mode: str = Query("raw", pattern="^(raw|clean)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    doc = get_owned_document(db, document_id, user)
    csv_text = facts_to_csv(_facts(db, doc, mode))
    return PlainTextResponse(
        csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{document_id}_facts_{mode}.csv"'},
    )


@router.get("/{document_id}/export.json")
def export_json(
    document_id: str,
    mode: str = Query("raw", pattern="^(raw|clean)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    doc = get_owned_document(db, document_id, user)
    json_text = facts_to_json(_facts(db, doc, mode))
    return Response(
        json_text,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{document_id}_facts_{mode}.json"'},
    )


@router.get("/{document_id}/export.xlsx")
def export_xlsx(
    document_id: str,
    mode: str = Query("clean", pattern="^(raw|clean)$", description="Analysis mode for forecast/Q&A sheets"),
    question: str | None = Query(None, description="Optional question → adds a Q&A Evidence sheet"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Structured multi-sheet analysis workbook (raw + cleaned facts, forecast,
    source mapping, scenario assumptions, optional Q&A evidence)."""
    doc = get_owned_document(db, document_id, user)
    data = build_workbook(db, doc, mode=mode, question=question)
    return Response(
        content=data,
        media_type=_XLSX_MEDIA,
        headers={"Content-Disposition": f'attachment; filename="{document_id}_analysis_{mode}.xlsx"'},
    )
