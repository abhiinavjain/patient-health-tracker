"""Clinical-note extraction: free text -> draft consultation for the clinician to review.

The endpoint never writes to the record. The clinician edits/approves the draft and submits it through
POST /patients/{id}/encounters as usual.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .. import audit
from ..deps import PatientCtx
from ..nlp.service import ExtractionResult, extract_note

router = APIRouter(tags=["notes"])


class NoteExtractIn(BaseModel):
    note: str = Field(min_length=10, max_length=20_000)
    visit_at: datetime | None = None


@router.post("/patients/{patient_id}/notes/extract", response_model=ExtractionResult)
def extract(body: NoteExtractIn, ctx: PatientCtx):
    ctx.require_clinician()
    # Extraction runs locally: the note never leaves this server.
    result = extract_note(body.note, ctx.patient, body.visit_at.date() if body.visit_at else None)
    # The note text itself is not stored in the audit log.
    audit.record(ctx.db, ctx.user, "extract", patient_id=ctx.patient.id, entity="note",
                 detail={"extractor": result.extractor,
                         "items": {k: sum(r.kind == k and r.status == "new" for r in result.review)
                                   for k in ("condition", "medication", "observation")}})
    ctx.db.commit()
    return result
