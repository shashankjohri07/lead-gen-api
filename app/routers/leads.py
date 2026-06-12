from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Optional
import math

from app.database import get_db
from app.models import Lead, SourceType, GenderType
from app.schemas import LeadOut, LeadListResponse, StatsResponse

router = APIRouter(prefix="/api/v1/leads", tags=["Leads"])


@router.get("", response_model=LeadListResponse)
def get_leads(
    state: Optional[str] = Query(None, description="Filter by state name e.g. Maharashtra"),
    district: Optional[str] = Query(None, description="Filter by district e.g. Pune"),
    city: Optional[str] = Query(None, description="Filter by city"),
    pincode: Optional[str] = Query(None),
    age_min: Optional[int] = Query(None, ge=1, le=120),
    age_max: Optional[int] = Query(None, ge=1, le=120),
    gender: Optional[GenderType] = Query(None),
    source: Optional[SourceType] = Query(None),
    has_phone: Optional[bool] = Query(None, description="Only return leads with phone number"),
    has_email: Optional[bool] = Query(None),
    search: Optional[str] = Query(None, description="Search by name"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(Lead)

    if state:
        query = query.filter(Lead.state.ilike(f"%{state}%"))
    if district:
        query = query.filter(Lead.district.ilike(f"%{district}%"))
    if city:
        query = query.filter(Lead.city.ilike(f"%{city}%"))
    if pincode:
        query = query.filter(Lead.pincode == pincode)
    if age_min is not None:
        query = query.filter(Lead.age >= age_min)
    if age_max is not None:
        query = query.filter(Lead.age <= age_max)
    if gender:
        query = query.filter(Lead.gender == gender)
    if source:
        query = query.filter(Lead.source == source)
    if has_phone is True:
        query = query.filter(Lead.phone_primary.isnot(None))
    if has_phone is False:
        query = query.filter(Lead.phone_primary.is_(None))
    if has_email is True:
        query = query.filter(Lead.email.isnot(None))
    if has_email is False:
        query = query.filter(Lead.email.is_(None))
    if search:
        query = query.filter(Lead.full_name.ilike(f"%{search}%"))

    total = query.count()
    offset = (page - 1) * limit
    leads = query.order_by(Lead.id).offset(offset).limit(limit).all()

    return LeadListResponse(
        total=total,
        page=page,
        limit=limit,
        pages=math.ceil(total / limit) if total > 0 else 0,
        data=leads,
    )


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    total = db.query(Lead).count()
    with_phone = db.query(Lead).filter(Lead.phone_primary.isnot(None)).count()
    with_email = db.query(Lead).filter(Lead.email.isnot(None)).count()

    by_state = (
        db.query(Lead.state, func.count(Lead.id).label("count"))
        .filter(Lead.state.isnot(None))
        .group_by(Lead.state)
        .order_by(func.count(Lead.id).desc())
        .limit(30)
        .all()
    )

    by_source = (
        db.query(Lead.source, func.count(Lead.id).label("count"))
        .group_by(Lead.source)
        .all()
    )

    return StatsResponse(
        total_leads=total,
        with_phone=with_phone,
        with_email=with_email,
        by_state=[{"state": r.state, "count": r.count} for r in by_state],
        by_source=[{"source": r.source, "count": r.count} for r in by_source],
    )


@router.get("/districts", response_model=list[dict])
def get_districts(
    state: str = Query(..., description="State name"),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Lead.district, func.count(Lead.id).label("count"))
        .filter(Lead.state.ilike(f"%{state}%"))
        .filter(Lead.district.isnot(None))
        .group_by(Lead.district)
        .order_by(Lead.district)
        .all()
    )
    return [{"district": r.district, "count": r.count} for r in rows]


@router.get("/states", response_model=list[dict])
def get_states(db: Session = Depends(get_db)):
    rows = (
        db.query(Lead.state, func.count(Lead.id).label("count"))
        .filter(Lead.state.isnot(None))
        .group_by(Lead.state)
        .order_by(Lead.state)
        .all()
    )
    return [{"state": r.state, "count": r.count} for r in rows]


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.delete("/{lead_id}")
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    db.delete(lead)
    db.commit()
    return {"message": "deleted"}
