from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from app.models import SourceType, GenderType


class LeadOut(BaseModel):
    id: int
    full_name: str
    gender: Optional[GenderType]
    age: Optional[int]
    date_of_birth: Optional[date]

    phone_primary: Optional[str]
    phone_secondary: Optional[str]
    email: Optional[str]

    address_line: Optional[str]
    area: Optional[str]
    city: Optional[str]
    district: Optional[str]
    state: Optional[str]
    pincode: Optional[str]

    source: SourceType
    source_id: Optional[str]
    din: Optional[str]
    company_name: Optional[str]
    designation: Optional[str]
    voter_id: Optional[str]
    constituency: Optional[str]

    # Lead-capture fields
    interest: Optional[str] = None
    consent: Optional[bool] = None
    utm_source: Optional[str] = None
    contacted: Optional[bool] = None

    phone_verified: bool
    email_verified: bool
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class LeadListResponse(BaseModel):
    total: int
    page: int
    limit: int
    pages: int
    data: List[LeadOut]


class StatsResponse(BaseModel):
    total_leads: int
    with_phone: int
    with_email: int
    by_state: List[dict]
    by_source: List[dict]


class IngestStatusResponse(BaseModel):
    task_id: str
    status: str
    message: str
