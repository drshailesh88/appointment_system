"""
API v1 module.
"""

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    appointments,
    patients,
    doctors,
    clinics,
    services,
    invoices,
    payments,
    insurance,
    voice,
    search,
    analytics,
    reports,
    waitlist,
    whatsapp,
    websocket,
    notifications,
    procedures,
    ai_chat,
    documents,
    calendar,
    emr,
    public,
    organizations,
    staff,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(clinics.router, prefix="/clinics", tags=["Clinics"])
api_router.include_router(doctors.router, prefix="/doctors", tags=["Doctors"])
api_router.include_router(patients.router, prefix="/patients", tags=["Patients"])
api_router.include_router(appointments.router, prefix="/appointments", tags=["Appointments"])
api_router.include_router(services.router, prefix="/services", tags=["Services"])
api_router.include_router(invoices.router, prefix="/invoices", tags=["Invoices"])
api_router.include_router(payments.router, prefix="/payments", tags=["Payments"])
api_router.include_router(insurance.router, prefix="/insurance", tags=["Insurance & Billing"])
api_router.include_router(voice.router, prefix="/voice", tags=["Voice Agent"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports & Exports"])
api_router.include_router(waitlist.router, prefix="/waitlist", tags=["Waitlist"])
api_router.include_router(whatsapp.router, prefix="/whatsapp", tags=["WhatsApp Bot"])
api_router.include_router(websocket.router, tags=["WebSocket"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Push Notifications"])
api_router.include_router(procedures.router, prefix="/procedures", tags=["Procedures"])
api_router.include_router(ai_chat.router, prefix="/ai", tags=["AI Assistant"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents & OCR"])
api_router.include_router(calendar.router, prefix="/calendar", tags=["Google Calendar"])
api_router.include_router(emr.router, prefix="/emr", tags=["EMR Integration"])
api_router.include_router(public.router, prefix="/public", tags=["Public Booking Portal"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["Organizations"])
api_router.include_router(staff.router, prefix="/staff", tags=["Staff Management"])
