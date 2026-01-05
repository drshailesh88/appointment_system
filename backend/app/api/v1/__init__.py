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
    voice,
    search,
    nl_search,
    analytics,
    waitlist,
    whatsapp,
    websocket,
    notifications,
    reports,
    insurance,
    labs,
    calendar_sync,
    health,
    slot_optimizer,
    noshow,
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
api_router.include_router(voice.router, prefix="/voice", tags=["Voice Agent"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(nl_search.router, prefix="/nl-search", tags=["Natural Language Search"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(waitlist.router, prefix="/waitlist", tags=["Waitlist"])
api_router.include_router(whatsapp.router, prefix="/whatsapp", tags=["WhatsApp Bot"])
api_router.include_router(websocket.router, tags=["WebSocket"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Push Notifications"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(insurance.router, prefix="/insurance", tags=["Insurance"])
api_router.include_router(labs.router, prefix="/labs", tags=["Lab Results"])
api_router.include_router(calendar_sync.router, prefix="/calendar", tags=["Calendar Sync"])
api_router.include_router(health.router, prefix="/health", tags=["Health Integration"])
api_router.include_router(slot_optimizer.router, prefix="/slots", tags=["Slot Optimizer"])
api_router.include_router(noshow.router, prefix="/noshow", tags=["No-Show Prediction"])
