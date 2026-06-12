from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Lead
from app.schemas import LeadOut
from scrapers.phone_enricher import lookup_phone
from scrapers.email_enricher import lookup_email

router = APIRouter(prefix="/api/v1/enrich", tags=["Enrichment"])


@router.post("/{lead_id}/phone", response_model=LeadOut)
def enrich_phone(lead_id: int, db: Session = Depends(get_db)):
    """
    Try to find phone number for a lead using Truecaller API or Google Maps.
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    phone = lookup_phone(name=lead.full_name, address=lead.address_line, company=lead.company_name)
    if phone:
        lead.phone_primary = phone
        lead.phone_verified = True
        db.commit()
        db.refresh(lead)

    return lead


@router.post("/{lead_id}/email", response_model=LeadOut)
def enrich_email(lead_id: int, db: Session = Depends(get_db)):
    """
    Find email for a lead using Hunter.io (company domain + name pattern).
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    email = lookup_email(name=lead.full_name, company=lead.company_name)
    if email:
        lead.email = email
        lead.email_verified = True
        db.commit()
        db.refresh(lead)

    return lead


@router.post("/bulk-phone")
def bulk_enrich_phone(
    state: str = None,
    district: str = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    Bulk enrich phone for leads missing phone number.
    Runs synchronously — keep limit small (50-100).
    """
    query = db.query(Lead).filter(Lead.phone_primary.is_(None))
    if state:
        query = query.filter(Lead.state.ilike(f"%{state}%"))
    if district:
        query = query.filter(Lead.district.ilike(f"%{district}%"))

    leads = query.limit(limit).all()
    enriched = 0

    for lead in leads:
        phone = lookup_phone(name=lead.full_name, address=lead.address_line, company=lead.company_name)
        if phone:
            lead.phone_primary = phone
            lead.phone_verified = True
            enriched += 1

    db.commit()
    return {"processed": len(leads), "enriched": enriched}
