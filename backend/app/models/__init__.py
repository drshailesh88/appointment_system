"""
SQLAlchemy models for DocAssist Practice Manager.
"""

from app.models.user import User
from app.models.organization import Organization
from app.models.clinic import Clinic
from app.models.staff import StaffRole, StaffAssignment, DEFAULT_PERMISSIONS
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.appointment import Appointment
from app.models.service import Service
from app.models.invoice import Invoice, InvoiceItem
from app.models.payment import Payment
from app.models.waitlist import Waitlist, WaitlistPriority, WaitlistStatus
from app.models.device_token import DeviceToken, DevicePlatform
from app.models.procedure import (
    Procedure,
    ProcedureOutcome,
    ProcedureSeverity,
    PROCEDURE_TEMPLATES,
)
from app.models.document import Document, DOCUMENT_TYPES
from app.models.insurance import (
    InsuranceCompany,
    PatientInsurance,
    InsuranceClaim,
    PreAuthorization,
    CoverageType,
    ClaimStatus,
    PreAuthStatus,
)
from app.models.otp import OTP
from app.models.insight import (
    ProactiveInsight,
    FollowupSchedule,
    UserDigestPreferences,
    InsightType,
    InsightPriority,
)
from app.models.phone_call import (
    PhoneCall,
    CallTranscriptSegment,
    CallStatus,
    CallDirection,
    CallIntent,
)
from app.models.consultation import (
    Consultation,
    ConsultationParticipant,
    ConsultationRecording,
    ConsultationStatus,
    ParticipantRole,
    ConnectionType,
    ConnectionQuality,
)

__all__ = [
    "User",
    "Organization",
    "Clinic",
    "StaffRole",
    "StaffAssignment",
    "DEFAULT_PERMISSIONS",
    "Doctor",
    "Patient",
    "Appointment",
    "Service",
    "Invoice",
    "InvoiceItem",
    "Payment",
    "Waitlist",
    "WaitlistPriority",
    "WaitlistStatus",
    "DeviceToken",
    "DevicePlatform",
    "Procedure",
    "ProcedureOutcome",
    "ProcedureSeverity",
    "PROCEDURE_TEMPLATES",
    "Document",
    "DOCUMENT_TYPES",
    "InsuranceCompany",
    "PatientInsurance",
    "InsuranceClaim",
    "PreAuthorization",
    "CoverageType",
    "ClaimStatus",
    "PreAuthStatus",
    "OTP",
    "ProactiveInsight",
    "FollowupSchedule",
    "UserDigestPreferences",
    "InsightType",
    "InsightPriority",
    "PhoneCall",
    "CallTranscriptSegment",
    "CallStatus",
    "CallDirection",
    "CallIntent",
    "Consultation",
    "ConsultationParticipant",
    "ConsultationRecording",
    "ConsultationStatus",
    "ParticipantRole",
    "ConnectionType",
    "ConnectionQuality",
]
