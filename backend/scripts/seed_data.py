#!/usr/bin/env python3
"""
Seed data script for development and testing.

Run: python scripts/seed_data.py
"""

import asyncio
import sys
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.appointment import Appointment
from app.models.clinic import Clinic
from app.models.doctor import Doctor
from app.models.invoice import Invoice, InvoiceItem
from app.models.patient import Patient
from app.models.payment import Payment
from app.models.service import Service
from app.models.user import User


async def seed_database():
    """Seed the database with sample data."""

    engine = create_async_engine(settings.async_database_url, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check if data already exists
        result = await session.execute(text("SELECT COUNT(*) FROM clinics"))
        count = result.scalar()
        if count > 0:
            print("Database already seeded. Skipping...")
            return

        print("Seeding database...")

        # =====================
        # Create Clinic
        # =====================
        clinic = Clinic(
            id=uuid4(),
            name="DocAssist Demo Clinic",
            slug="demo-clinic",
            phone="+919876543210",
            email="demo@docassist.in",
            address="123 Health Street, Koramangala",
            city="Bangalore",
            state="Karnataka",
            pincode="560034",
            gst_number="29AABCD1234E1Z5",
            subscription_tier="professional",
            subscription_expires_at=datetime.now(timezone.utc) + timedelta(days=365),
            timezone="Asia/Kolkata",
            currency="INR",
            is_active=True,
        )
        session.add(clinic)
        await session.flush()
        print(f"Created clinic: {clinic.name}")

        # =====================
        # Create Admin User
        # =====================
        admin_user = User(
            id=uuid4(),
            email="admin@docassist.in",
            phone="+919876543211",
            password_hash=get_password_hash("admin123"),
            name="Admin User",
            role="admin",
            clinic_id=clinic.id,
            is_active=True,
            is_verified=True,
        )
        session.add(admin_user)
        print(f"Created admin user: {admin_user.email}")

        # =====================
        # Create Doctors
        # =====================
        doctors_data = [
            {
                "name": "Dr. Priya Sharma",
                "specialization": "General Medicine",
                "qualification": "MBBS, MD (Internal Medicine)",
                "registration_number": "KMC-12345",
                "experience_years": 12,
                "phone": "+919876543212",
                "email": "priya.sharma@docassist.in",
                "consultation_fee": Decimal("500.00"),
                "followup_fee": Decimal("300.00"),
                "slot_duration": 15,
                "languages": ["English", "Hindi", "Kannada"],
                "working_hours": {
                    "monday": [{"start": "09:00", "end": "13:00"}, {"start": "17:00", "end": "20:00"}],
                    "tuesday": [{"start": "09:00", "end": "13:00"}, {"start": "17:00", "end": "20:00"}],
                    "wednesday": [{"start": "09:00", "end": "13:00"}],
                    "thursday": [{"start": "09:00", "end": "13:00"}, {"start": "17:00", "end": "20:00"}],
                    "friday": [{"start": "09:00", "end": "13:00"}, {"start": "17:00", "end": "20:00"}],
                    "saturday": [{"start": "09:00", "end": "14:00"}],
                },
            },
            {
                "name": "Dr. Rajesh Kumar",
                "specialization": "Cardiology",
                "qualification": "MBBS, DM (Cardiology)",
                "registration_number": "KMC-23456",
                "experience_years": 18,
                "phone": "+919876543213",
                "email": "rajesh.kumar@docassist.in",
                "consultation_fee": Decimal("800.00"),
                "followup_fee": Decimal("500.00"),
                "slot_duration": 20,
                "languages": ["English", "Hindi"],
                "working_hours": {
                    "monday": [{"start": "10:00", "end": "14:00"}, {"start": "16:00", "end": "19:00"}],
                    "tuesday": [{"start": "10:00", "end": "14:00"}],
                    "wednesday": [{"start": "10:00", "end": "14:00"}, {"start": "16:00", "end": "19:00"}],
                    "thursday": [{"start": "10:00", "end": "14:00"}, {"start": "16:00", "end": "19:00"}],
                    "friday": [{"start": "10:00", "end": "14:00"}],
                },
            },
            {
                "name": "Dr. Anita Patel",
                "specialization": "Pediatrics",
                "qualification": "MBBS, DCH, DNB (Pediatrics)",
                "registration_number": "KMC-34567",
                "experience_years": 8,
                "phone": "+919876543214",
                "email": "anita.patel@docassist.in",
                "consultation_fee": Decimal("600.00"),
                "followup_fee": Decimal("400.00"),
                "slot_duration": 15,
                "languages": ["English", "Hindi", "Gujarati"],
                "working_hours": {
                    "monday": [{"start": "09:00", "end": "12:00"}, {"start": "16:00", "end": "20:00"}],
                    "tuesday": [{"start": "09:00", "end": "12:00"}, {"start": "16:00", "end": "20:00"}],
                    "wednesday": [{"start": "09:00", "end": "12:00"}, {"start": "16:00", "end": "20:00"}],
                    "thursday": [{"start": "09:00", "end": "12:00"}],
                    "friday": [{"start": "09:00", "end": "12:00"}, {"start": "16:00", "end": "20:00"}],
                    "saturday": [{"start": "09:00", "end": "13:00"}],
                },
            },
        ]

        doctors = []
        for doc_data in doctors_data:
            # Create user account for doctor
            doc_user = User(
                id=uuid4(),
                email=doc_data["email"],
                phone=doc_data["phone"],
                password_hash=get_password_hash("doctor123"),
                name=doc_data["name"],
                role="doctor",
                clinic_id=clinic.id,
                is_active=True,
                is_verified=True,
            )
            session.add(doc_user)

            doctor = Doctor(
                id=uuid4(),
                clinic_id=clinic.id,
                user_id=doc_user.id,
                **doc_data,
            )
            session.add(doctor)
            doctors.append(doctor)
            print(f"Created doctor: {doctor.name}")

        await session.flush()

        # =====================
        # Create Receptionist
        # =====================
        receptionist = User(
            id=uuid4(),
            email="reception@docassist.in",
            phone="+919876543220",
            password_hash=get_password_hash("reception123"),
            name="Rekha Menon",
            role="receptionist",
            clinic_id=clinic.id,
            is_active=True,
            is_verified=True,
        )
        session.add(receptionist)
        print(f"Created receptionist: {receptionist.name}")

        # =====================
        # Create Services
        # =====================
        services_data = [
            {"name": "General Consultation", "code": "CONS001", "category": "Consultation", "price": Decimal("500.00"), "duration_minutes": 15},
            {"name": "Follow-up Visit", "code": "CONS002", "category": "Consultation", "price": Decimal("300.00"), "duration_minutes": 10},
            {"name": "ECG", "code": "DIAG001", "category": "Diagnostics", "price": Decimal("350.00"), "tax_rate": Decimal("18.00"), "duration_minutes": 15},
            {"name": "Blood Pressure Check", "code": "DIAG002", "category": "Diagnostics", "price": Decimal("100.00"), "duration_minutes": 5},
            {"name": "Blood Sugar Test", "code": "LAB001", "category": "Laboratory", "price": Decimal("150.00"), "tax_rate": Decimal("18.00"), "duration_minutes": 10},
            {"name": "Complete Blood Count", "code": "LAB002", "category": "Laboratory", "price": Decimal("400.00"), "tax_rate": Decimal("18.00"), "duration_minutes": 15},
            {"name": "Vaccination", "code": "PROC001", "category": "Procedures", "price": Decimal("250.00"), "tax_rate": Decimal("5.00"), "duration_minutes": 10},
            {"name": "Wound Dressing", "code": "PROC002", "category": "Procedures", "price": Decimal("200.00"), "duration_minutes": 20},
        ]

        services = []
        for svc_data in services_data:
            service = Service(
                id=uuid4(),
                clinic_id=clinic.id,
                **svc_data,
            )
            session.add(service)
            services.append(service)
        print(f"Created {len(services)} services")

        await session.flush()

        # =====================
        # Create Patients
        # =====================
        patients_data = [
            {"first_name": "Rahul", "last_name": "Mehta", "phone": "+919876500001", "email": "rahul.mehta@email.com", "gender": "M", "date_of_birth": date(1985, 5, 15), "blood_group": "O+", "city": "Bangalore"},
            {"first_name": "Priyanka", "last_name": "Singh", "phone": "+919876500002", "email": "priyanka.singh@email.com", "gender": "F", "date_of_birth": date(1990, 8, 22), "blood_group": "A+", "city": "Bangalore"},
            {"first_name": "Amit", "last_name": "Sharma", "phone": "+919876500003", "email": "amit.sharma@email.com", "gender": "M", "date_of_birth": date(1978, 3, 10), "blood_group": "B+", "city": "Bangalore", "allergies": "Penicillin"},
            {"first_name": "Sneha", "last_name": "Reddy", "phone": "+919876500004", "email": "sneha.reddy@email.com", "gender": "F", "date_of_birth": date(1995, 11, 5), "blood_group": "AB+", "city": "Bangalore"},
            {"first_name": "Vikram", "last_name": "Joshi", "phone": "+919876500005", "email": "vikram.joshi@email.com", "gender": "M", "date_of_birth": date(1982, 7, 18), "blood_group": "O-", "city": "Bangalore"},
            {"first_name": "Kavitha", "last_name": "Nair", "phone": "+919876500006", "email": "kavitha.nair@email.com", "gender": "F", "date_of_birth": date(1988, 1, 30), "blood_group": "A-", "city": "Bangalore"},
            {"first_name": "Arjun", "last_name": "Kapoor", "phone": "+919876500007", "email": "arjun.kapoor@email.com", "gender": "M", "date_of_birth": date(2015, 4, 12), "blood_group": "B+", "city": "Bangalore"},
            {"first_name": "Meera", "last_name": "Iyer", "phone": "+919876500008", "email": "meera.iyer@email.com", "gender": "F", "date_of_birth": date(1972, 9, 25), "blood_group": "O+", "city": "Bangalore"},
        ]

        patients = []
        for pat_data in patients_data:
            patient = Patient(
                id=uuid4(),
                clinic_id=clinic.id,
                state="Karnataka",
                **pat_data,
            )
            session.add(patient)
            patients.append(patient)
        print(f"Created {len(patients)} patients")

        await session.flush()

        # =====================
        # Create Today's Appointments
        # =====================
        today = date.today()
        appointment_times = [
            ("09:00", "scheduled"),
            ("09:15", "scheduled"),
            ("09:30", "checked_in"),
            ("09:45", "checked_in"),
            ("10:00", "in_progress"),
            ("10:15", "completed"),
            ("10:30", "completed"),
            ("10:45", "scheduled"),
            ("11:00", "scheduled"),
            ("11:15", "cancelled"),
        ]

        appointments = []
        for i, (time_str, status) in enumerate(appointment_times):
            hour, minute = map(int, time_str.split(":"))
            start_time = datetime.combine(today, time(hour, minute), tzinfo=timezone.utc)

            appointment = Appointment(
                id=uuid4(),
                patient_id=patients[i % len(patients)].id,
                doctor_id=doctors[0].id,  # Dr. Priya Sharma
                scheduled_start=start_time,
                scheduled_end=start_time + timedelta(minutes=15),
                duration_minutes=15,
                status=status,
                appointment_type="new_consultation" if i % 2 == 0 else "follow_up",
                booking_source="app" if i % 3 == 0 else "walk_in",
                chief_complaint=["Headache and fever", "Follow-up for diabetes", "Cough and cold", "Routine checkup", "Back pain"][i % 5],
                token_number=i + 1 if status in ["checked_in", "in_progress", "completed"] else None,
                check_in_time=start_time - timedelta(minutes=10) if status in ["checked_in", "in_progress", "completed"] else None,
                start_time=start_time if status in ["in_progress", "completed"] else None,
                end_time=start_time + timedelta(minutes=12) if status == "completed" else None,
            )
            session.add(appointment)
            appointments.append(appointment)

        print(f"Created {len(appointments)} appointments for today")

        # =====================
        # Create Sample Invoice
        # =====================
        invoice = Invoice(
            id=uuid4(),
            invoice_number=f"INV-{today.strftime('%Y%m%d')}-0001",
            patient_id=patients[0].id,
            doctor_id=doctors[0].id,
            clinic_id=clinic.id,
            invoice_date=today,
            due_date=today + timedelta(days=7),
            subtotal=Decimal("500.00"),
            tax_amount=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("500.00"),
            paid_amount=Decimal("500.00"),
            status="paid",
            gstin=clinic.gst_number,
        )
        session.add(invoice)

        invoice_item = InvoiceItem(
            id=uuid4(),
            invoice_id=invoice.id,
            service_id=services[0].id,
            description="General Consultation",
            quantity=1,
            unit_price=Decimal("500.00"),
            tax_rate=Decimal("0.00"),
            subtotal=Decimal("500.00"),
            tax_amount=Decimal("0.00"),
            total=Decimal("500.00"),
        )
        session.add(invoice_item)

        # Create payment for invoice
        payment = Payment(
            id=uuid4(),
            invoice_id=invoice.id,
            amount=Decimal("500.00"),
            payment_method="upi",
            status="completed",
            payment_date=datetime.now(timezone.utc),
            upi_transaction_id="UPI123456789",
            collected_by=receptionist.name,
        )
        session.add(payment)
        print("Created sample invoice and payment")

        # Commit all changes
        await session.commit()
        print("\n✅ Database seeded successfully!")
        print("\n📋 Login Credentials:")
        print("   Admin:        admin@docassist.in / admin123")
        print("   Doctor:       priya.sharma@docassist.in / doctor123")
        print("   Receptionist: reception@docassist.in / reception123")


if __name__ == "__main__":
    asyncio.run(seed_database())
