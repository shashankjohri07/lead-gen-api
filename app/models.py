from sqlalchemy import Column, Integer, String, Date, DateTime, Enum, Index, Text, Boolean
from sqlalchemy.sql import func
import enum
from app.database import Base


class SourceType(str, enum.Enum):
    MCA_DIRECTOR = "mca_director"
    VOTER_ROLL = "voter_roll"
    GOOGLE_MAPS = "google_maps"
    MANUAL = "manual"


class GenderType(str, enum.Enum):
    MALE = "M"
    FEMALE = "F"
    OTHER = "O"
    UNKNOWN = "U"


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)

    # Identity
    full_name = Column(String(200), nullable=False)
    gender = Column(Enum(GenderType), default=GenderType.UNKNOWN)
    date_of_birth = Column(Date, nullable=True)
    age = Column(Integer, nullable=True)

    # Contact
    phone_primary = Column(String(15), nullable=True)
    phone_secondary = Column(String(15), nullable=True)
    email = Column(String(200), nullable=True)

    # Address
    address_line = Column(Text, nullable=True)
    area = Column(String(200), nullable=True)
    city = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True, index=True)
    state = Column(String(100), nullable=True, index=True)
    pincode = Column(String(10), nullable=True)

    # Source-specific IDs
    source = Column(Enum(SourceType), nullable=False)
    source_id = Column(String(100), nullable=True)  # DIN / Voter ID / Place ID

    # MCA-specific
    din = Column(String(20), nullable=True)
    company_name = Column(String(300), nullable=True)
    designation = Column(String(100), nullable=True)

    # Voter-specific
    voter_id = Column(String(30), nullable=True)
    constituency = Column(String(200), nullable=True)
    booth_no = Column(String(20), nullable=True)

    # Enrichment flags
    phone_verified = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("ix_leads_state_district", "state", "district"),
        Index("ix_leads_age", "age"),
        Index("ix_leads_source", "source"),
        Index("ix_leads_phone", "phone_primary"),
        Index("ix_leads_name", "full_name"),
    )
