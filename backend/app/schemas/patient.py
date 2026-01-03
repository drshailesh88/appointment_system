"""
Patient schemas for patient management.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class PatientBase(BaseModel):
    """Base patient schema."""

    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    phone: str = Field(..., min_length=10, max_length=15)
    email: EmailStr | None = None
    date_of_birth: date | None = None
    gender: str | None = Field(None, pattern=r"^[MFO]$")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate and normalize phone number."""
        v = v.replace(" ", "").replace("-", "")
        if not v.startswith("+"):
            if v.startswith("0"):
                v = "+91" + v[1:]
            else:
                v = "+91" + v
        return v


class PatientCreate(PatientBase):
    """Schema for creating a patient."""

    clinic_id: UUID
    address: str | None = None
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    pincode: str | None = Field(None, max_length=10)
    aadhaar_last_four: str | None = Field(None, min_length=4, max_length=4)
    blood_group: str | None = Field(None, max_length=5)
    allergies: str | None = None
    emergency_contact_name: str | None = Field(None, max_length=200)
    emergency_contact_phone: str | None = Field(None, max_length=15)
    preferred_language: str = "en"
    sms_consent: bool = True
    whatsapp_consent: bool = True


class PatientUpdate(BaseModel):
    """Schema for updating a patient."""

    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = None
    phone: str | None = Field(None, min_length=10, max_length=15)
    email: EmailStr | None = None
    date_of_birth: date | None = None
    gender: str | None = Field(None, pattern=r"^[MFO]$")
    address: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    aadhaar_last_four: str | None = None
    photo_url: str | None = None
    blood_group: str | None = None
    allergies: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    preferred_language: str | None = None
    sms_consent: bool | None = None
    whatsapp_consent: bool | None = None
    is_active: bool | None = None


class PatientResponse(BaseModel):
    """Schema for patient response."""

    id: UUID
    first_name: str
    last_name: str | None
    full_name: str
    phone: str
    email: str | None
    date_of_birth: date | None
    age: int | None
    gender: str | None
    address: str | None
    city: str | None
    state: str | None
    pincode: str | None
    aadhaar_last_four: str | None
    photo_url: str | None
    clinic_id: UUID
    emr_patient_id: str | None
    blood_group: str | None
    allergies: str | None
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    preferred_language: str
    sms_consent: bool
    whatsapp_consent: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PatientListResponse(BaseModel):
    """Schema for listing patients."""

    id: UUID
    first_name: str
    last_name: str | None
    full_name: str
    phone: str
    age: int | None
    gender: str | None
    is_active: bool
    last_visit: datetime | None = None

    model_config = {"from_attributes": True}


class PatientSearch(BaseModel):
    """Schema for patient search."""

    query: str = Field(..., min_length=2, max_length=100)
    clinic_id: UUID | None = None
    limit: int = Field(default=20, ge=1, le=100)
