from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from typing import Optional
import re

from app.database import get_db
from app.models import Lead, SourceType, GenderType

router = APIRouter(prefix="/api/v1/capture", tags=["Lead Capture"])


class CaptureIn(BaseModel):
    full_name: str
    phone_primary: str
    email: Optional[str] = None
    age: Optional[int] = None
    city: Optional[str] = None
    state: Optional[str] = None
    interest: Optional[str] = None      # "Family health", "Senior citizen", etc.
    consent: bool                        # MUST be true — legal requirement
    utm_source: Optional[str] = None

    @field_validator("phone_primary")
    @classmethod
    def validate_phone(cls, v):
        digits = re.sub(r"\D", "", v)
        if len(digits) < 10:
            raise ValueError("Phone number kam se kam 10 digit ka hona chahiye")
        return digits[-10:]  # last 10 digits store karo

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, v):
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Naam zaroori hai")
        return v.title()


@router.post("", status_code=201)
def capture_lead(payload: CaptureIn, request: Request, db: Session = Depends(get_db)):
    """
    Public endpoint — landing page form yahan submit karta hai.
    Consent zaroori hai (legal requirement under DPDP Act).
    """
    if not payload.consent:
        raise HTTPException(
            status_code=400,
            detail="Consent zaroori hai — user ko contact hone ki permission deni hogi",
        )

    # Duplicate phone check (last 7 days mein same number)
    existing = (
        db.query(Lead)
        .filter(Lead.phone_primary == payload.phone_primary)
        .filter(Lead.source == SourceType.LANDING_PAGE)
        .first()
    )
    if existing:
        return {
            "status": "already_registered",
            "message": "Aapki request pehle se mil chuki hai, hum jald contact karenge",
            "lead_id": existing.id,
        }

    lead = Lead(
        full_name=payload.full_name,
        phone_primary=payload.phone_primary,
        email=payload.email,
        age=payload.age,
        city=payload.city,
        state=payload.state,
        district=payload.city,  # landing page se city = district maan lo
        interest=payload.interest,
        consent=True,
        utm_source=payload.utm_source or request.headers.get("referer", "direct"),
        source=SourceType.LANDING_PAGE,
        phone_verified=True,  # user ne khud diya hai
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    return {
        "status": "success",
        "message": "Dhanyavaad! Hamari team jald aapse sampark karegi.",
        "lead_id": lead.id,
    }
