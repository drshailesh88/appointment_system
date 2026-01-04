"""
Pydantic schemas for API validation.
"""

from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
    Token,
    TokenPayload,
)
from app.schemas.clinic import (
    ClinicCreate,
    ClinicResponse,
    ClinicUpdate,
)
from app.schemas.doctor import (
    DoctorCreate,
    DoctorResponse,
    DoctorUpdate,
    WorkingHours,
)
from app.schemas.patient import (
    PatientCreate,
    PatientResponse,
    PatientUpdate,
    PatientSearch,
)
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentResponse,
    AppointmentUpdate,
    AppointmentSlot,
    SlotAvailabilityRequest,
)
from app.schemas.service import (
    ServiceCreate,
    ServiceResponse,
    ServiceUpdate,
)
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceResponse,
    InvoiceUpdate,
    InvoiceItemCreate,
    InvoiceItemResponse,
)
from app.schemas.payment import (
    PaymentCreate,
    PaymentResponse,
    PaymentUpdate,
)
from app.schemas.procedure import (
    ProcedureCreate,
    ProcedureResponse,
    ProcedureUpdate,
    ProcedureListResponse,
    ProcedureStats,
    ProcedureQuickLog,
    ProcedureTemplatesResponse,
)
from app.schemas.document import (
    DocumentCreate,
    DocumentResponse,
    DocumentUpdate,
    DocumentListResponse,
    DocumentOCRRequest,
    DocumentOCRResponse,
    DocumentTextResponse,
    DocumentUploadResponse,
    DocumentStats,
)
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
    OrganizationStats,
    OrganizationAddClinic,
    OrganizationRemoveClinic,
)
from app.schemas.staff import (
    StaffRoleCreate,
    StaffRoleResponse,
    StaffRoleUpdate,
    StaffAssignmentCreate,
    StaffAssignmentResponse,
    StaffAssignmentUpdate,
    StaffPerformanceMetrics,
    PermissionCheckRequest,
    PermissionCheckResponse,
    StaffTransferRequest,
)

__all__ = [
    # User
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "UserUpdate",
    "Token",
    "TokenPayload",
    # Clinic
    "ClinicCreate",
    "ClinicResponse",
    "ClinicUpdate",
    # Doctor
    "DoctorCreate",
    "DoctorResponse",
    "DoctorUpdate",
    "WorkingHours",
    # Patient
    "PatientCreate",
    "PatientResponse",
    "PatientUpdate",
    "PatientSearch",
    # Appointment
    "AppointmentCreate",
    "AppointmentResponse",
    "AppointmentUpdate",
    "AppointmentSlot",
    "SlotAvailabilityRequest",
    # Service
    "ServiceCreate",
    "ServiceResponse",
    "ServiceUpdate",
    # Invoice
    "InvoiceCreate",
    "InvoiceResponse",
    "InvoiceUpdate",
    "InvoiceItemCreate",
    "InvoiceItemResponse",
    # Payment
    "PaymentCreate",
    "PaymentResponse",
    "PaymentUpdate",
    # Procedure
    "ProcedureCreate",
    "ProcedureResponse",
    "ProcedureUpdate",
    "ProcedureListResponse",
    "ProcedureStats",
    "ProcedureQuickLog",
    "ProcedureTemplatesResponse",
    # Document
    "DocumentCreate",
    "DocumentResponse",
    "DocumentUpdate",
    "DocumentListResponse",
    "DocumentOCRRequest",
    "DocumentOCRResponse",
    "DocumentTextResponse",
    "DocumentUploadResponse",
    "DocumentStats",
    # Organization
    "OrganizationCreate",
    "OrganizationResponse",
    "OrganizationUpdate",
    "OrganizationStats",
    "OrganizationAddClinic",
    "OrganizationRemoveClinic",
    # Staff
    "StaffRoleCreate",
    "StaffRoleResponse",
    "StaffRoleUpdate",
    "StaffAssignmentCreate",
    "StaffAssignmentResponse",
    "StaffAssignmentUpdate",
    "StaffPerformanceMetrics",
    "PermissionCheckRequest",
    "PermissionCheckResponse",
    "StaffTransferRequest",
]
