"""
API v1 module.
"""

from fastapi import APIRouter

from app.api.v1 import auth, appointments, patients, doctors, clinics, services, invoices, payments, voice, search

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
