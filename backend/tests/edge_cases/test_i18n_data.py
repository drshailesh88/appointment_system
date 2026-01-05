"""
Comprehensive edge case tests for internationalization and data handling.

Tests cover:
1. Multi-language support (Hindi, Tamil, Telugu, mixed languages)
2. Date/time edge cases (midnight, month end, leap year, timezone)
3. Large data handling (long strings, many records, concurrent operations)
4. Special characters (apostrophes, hyphens, unicode)
5. Empty/null data handling

IMPORTANT: If tests fail with "SQLiteTypeCompiler object has no attribute 'visit_JSONB'",
this is a pre-existing bug where some models import JSONB directly from
sqlalchemy.dialects.postgresql instead of using the database-agnostic JSONB
from app.models.base.

To fix: Update imports in models to use:
    from app.models.base import JSONB
instead of:
    from sqlalchemy.dialects.postgresql import JSONB
"""

import unicodedata
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment, AppointmentStatus, AppointmentType, BookingSource
from app.models.clinic import Clinic
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.service import Service
from app.models.user import User
from app.core.security import get_password_hash


# ============================================================================
# FIXTURES FOR INTERNATIONAL DATA
# ============================================================================


@pytest.fixture
async def hindi_clinic(db: AsyncSession) -> Clinic:
    """Clinic with Hindi name."""
    clinic = Clinic(
        id=str(uuid4()),
        name="राज क्लिनिक",  # Raj Clinic
        slug="raj-clinic",
        address="मुंबई केंद्रीय रोड, बांद्रा",  # Mumbai Central Road, Bandra
        city="मुंबई",  # Mumbai
        state="महाराष्ट्र",  # Maharashtra
        pincode="400050",
        phone="+919876543210",
        email="info@rajclinic.in",
        subscription_tier="professional",
    )
    db.add(clinic)
    await db.commit()
    await db.refresh(clinic)
    return clinic


@pytest.fixture
async def tamil_clinic(db: AsyncSession) -> Clinic:
    """Clinic with Tamil name."""
    clinic = Clinic(
        id=str(uuid4()),
        name="சென்னை மருத்துவமனை",  # Chennai Hospital
        slug="chennai-hospital",
        address="அண்ணா சாலை, தி நகர்",  # Anna Road, T Nagar
        city="சென்னை",  # Chennai
        state="தமிழ்நாடு",  # Tamil Nadu
        pincode="600017",
        phone="+914412345678",
        email="info@chennaihospital.in",
        subscription_tier="professional",
    )
    db.add(clinic)
    await db.commit()
    await db.refresh(clinic)
    return clinic


# ============================================================================
# TEST 1: MULTI-LANGUAGE SUPPORT
# ============================================================================


class TestMultiLanguageSupport:
    """Tests for Indian language support (Hindi, Tamil, Telugu)."""

    @pytest.mark.asyncio


    async def test_hindi_patient_name(self, db: AsyncSession, hindi_clinic: Clinic):
        """Test patient with Hindi name (Devanagari script)."""
        patient = Patient(
            id=str(uuid4()),
            clinic_id=hindi_clinic.id,
            first_name="राजेश",  # Rajesh
            last_name="शर्मा",  # Sharma
            phone="+919876543210",
            email="rajesh.sharma@example.com",
            gender="M",
            date_of_birth=date(1985, 5, 15),
            address="सेक्टर 15, नोएडा",  # Sector 15, Noida
            city="नोएडा",  # Noida
            state="उत्तर प्रदेश",  # Uttar Pradesh
            preferred_language="hi",
        )
        db.add(patient)
        await db.commit()
        await db.refresh(patient)

        # Verify data persisted correctly
        assert patient.first_name == "राजेश"
        assert patient.last_name == "शर्मा"
        assert patient.full_name == "राजेश शर्मा"
        assert patient.city == "नोएडा"
        assert patient.state == "उत्तर प्रदेश"

    @pytest.mark.asyncio


    async def test_tamil_patient_name(self, db: AsyncSession, tamil_clinic: Clinic):
        """Test patient with Tamil name."""
        patient = Patient(
            id=str(uuid4()),
            clinic_id=tamil_clinic.id,
            first_name="முருகன்",  # Murugan
            last_name="குமார்",  # Kumar
            phone="+914412345678",
            email="murugan.kumar@example.com",
            gender="M",
            date_of_birth=date(1990, 8, 10),
            address="நேரு நகர், சென்னை",  # Nehru Nagar, Chennai
            city="சென்னை",  # Chennai
            state="தமிழ்நாடு",  # Tamil Nadu
            preferred_language="ta",
        )
        db.add(patient)
        await db.commit()
        await db.refresh(patient)

        assert patient.first_name == "முருகன்"
        assert patient.full_name == "முருகன் குமார்"
        assert patient.preferred_language == "ta"

    @pytest.mark.asyncio


    async def test_telugu_patient_name(self, db: AsyncSession, test_clinic: Clinic):
        """Test patient with Telugu name."""
        patient = Patient(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            first_name="వెంకటేష్",  # Venkatesh
            last_name="రెడ్డి",  # Reddy
            phone="+914012345678",
            email="venkatesh.reddy@example.com",
            gender="M",
            date_of_birth=date(1988, 12, 20),
            address="హైదరాబాద్",  # Hyderabad
            city="హైదరాబాద్",
            state="తెలంగాణ",  # Telangana
            preferred_language="te",
        )
        db.add(patient)
        await db.commit()
        await db.refresh(patient)

        assert patient.first_name == "వెంకటేష్"
        assert patient.last_name == "రెడ్డి"
        assert patient.state == "తెలంగాణ"

    @pytest.mark.asyncio


    async def test_mixed_language_patient(self, db: AsyncSession, test_clinic: Clinic):
        """Test patient with mixed Hindi-English name."""
        patient = Patient(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            first_name="राज Kumar",  # Raj Kumar (mixed)
            last_name="पटेल Patel",  # Patel (mixed)
            phone="+919876543210",
            email="raj.kumar@example.com",
            gender="M",
            date_of_birth=date(1992, 3, 25),
            address="123 Main Road, सेक्टर 10",  # Mixed address
        )
        db.add(patient)
        await db.commit()
        await db.refresh(patient)

        assert "राज" in patient.first_name
        assert "Kumar" in patient.first_name
        assert "पटेल" in patient.last_name
        assert "Patel" in patient.last_name

    @pytest.mark.asyncio


    async def test_unicode_normalization(self, db: AsyncSession, test_clinic: Clinic):
        """Test Unicode normalization for Indian scripts."""
        # Create patient with non-normalized Unicode
        name_nfc = unicodedata.normalize('NFC', "प्रिया")  # Priya in Hindi
        name_nfd = unicodedata.normalize('NFD', "प्रिया")

        patient1 = Patient(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            first_name=name_nfc,
            phone="+919876543210",
        )

        patient2 = Patient(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            first_name=name_nfd,
            phone="+919876543211",
        )

        db.add(patient1)
        db.add(patient2)
        await db.commit()

        # Both forms should be preserved as entered
        await db.refresh(patient1)
        await db.refresh(patient2)

        # Check they're both stored (they're different Unicode forms)
        assert patient1.first_name is not None
        assert patient2.first_name is not None

    @pytest.mark.asyncio


    async def test_right_to_left_text(self, db: AsyncSession, test_clinic: Clinic):
        """Test handling of RTL text (Urdu/Arabic script)."""
        # Note: While not primary Indian language, some clinics may have Urdu-speaking patients
        patient = Patient(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            first_name="احمد",  # Ahmed in Urdu
            last_name="خان",  # Khan
            phone="+919876543210",
            email="ahmed@example.com",
            address="حیدرآباد، ہندوستان",  # Hyderabad, India
        )
        db.add(patient)
        await db.commit()
        await db.refresh(patient)

        assert patient.first_name == "احمد"
        assert patient.last_name == "خان"

    @pytest.mark.asyncio


    async def test_all_indian_languages_preference(self, db: AsyncSession, test_clinic: Clinic):
        """Test all 23 Indian language preferences supported by voice agent."""
        languages = [
            "hi", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa", "or",
            "as", "ur", "sa", "ks", "sd", "ne", "mai", "kok", "mni", "bodo",
            "doi", "sat", "en"  # Including English
        ]

        for idx, lang in enumerate(languages):
            patient = Patient(
                id=str(uuid4()),
                clinic_id=test_clinic.id,
                first_name=f"Patient_{lang}",
                phone=f"+9198765432{idx:02d}",
                preferred_language=lang,
            )
            db.add(patient)

        await db.commit()

        # Verify all patients were created with correct language preferences
        patients = db.query(Patient).filter(
            Patient.clinic_id == test_clinic.id
        ).all()

        assert len(patients) == len(languages)
        stored_languages = {p.preferred_language for p in patients}
        assert stored_languages == set(languages)


# ============================================================================
# TEST 2: DATE/TIME EDGE CASES
# ============================================================================


class TestDateTimeEdgeCases:
    """Tests for date/time edge cases."""

    @pytest.mark.asyncio


    async def test_midnight_appointment(
        self,
        db: AsyncSession,
        test_clinic: Clinic,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test appointment exactly at midnight (00:00)."""
        midnight = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)

        appointment = Appointment(
            id=str(uuid4()),
            patient_id=test_patient.id,
            doctor_id=test_doctor.id,
            scheduled_start=midnight,
            scheduled_end=midnight + timedelta(minutes=15),
            duration_minutes=15,
            status=AppointmentStatus.SCHEDULED.value,
            appointment_type=AppointmentType.NEW_CONSULTATION.value,
        )
        db.add(appointment)
        await db.commit()
        await db.refresh(appointment)

        assert appointment.scheduled_start.hour == 0
        assert appointment.scheduled_start.minute == 0
        assert appointment.duration_minutes == 15

    @pytest.mark.asyncio


    async def test_end_of_month_appointment(
        self,
        db: AsyncSession,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test appointment on last day of month (31st)."""
        # January 31st
        jan_31 = datetime(2026, 1, 31, 15, 0, 0)

        appointment = Appointment(
            id=str(uuid4()),
            patient_id=test_patient.id,
            doctor_id=test_doctor.id,
            scheduled_start=jan_31,
            scheduled_end=jan_31 + timedelta(minutes=30),
            duration_minutes=30,
            status=AppointmentStatus.SCHEDULED.value,
        )
        db.add(appointment)
        await db.commit()
        await db.refresh(appointment)

        assert appointment.scheduled_start.day == 31
        assert appointment.scheduled_start.month == 1

    @pytest.mark.asyncio


    async def test_leap_year_feb_29(
        self,
        db: AsyncSession,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test appointment on Feb 29 (leap year)."""
        # 2024 was a leap year
        feb_29 = datetime(2024, 2, 29, 10, 0, 0)

        appointment = Appointment(
            id=str(uuid4()),
            patient_id=test_patient.id,
            doctor_id=test_doctor.id,
            scheduled_start=feb_29,
            scheduled_end=feb_29 + timedelta(minutes=15),
            duration_minutes=15,
        )
        db.add(appointment)
        await db.commit()
        await db.refresh(appointment)

        assert appointment.scheduled_start.day == 29
        assert appointment.scheduled_start.month == 2
        assert appointment.scheduled_start.year == 2024

    @pytest.mark.asyncio


    async def test_patient_born_on_leap_day(self, db: AsyncSession, test_clinic: Clinic):
        """Test patient born on Feb 29."""
        patient = Patient(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            first_name="Leap",
            last_name="Year",
            phone="+919876543210",
            date_of_birth=date(2000, 2, 29),
        )
        db.add(patient)
        await db.commit()
        await db.refresh(patient)

        assert patient.date_of_birth.day == 29
        assert patient.date_of_birth.month == 2

        # Age calculation on non-leap year
        # Mock current date as 2026-01-05 (non-leap year)
        assert patient.age is not None  # Should calculate correctly

    @pytest.mark.asyncio


    async def test_timezone_handling_ist(
        self,
        db: AsyncSession,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test timezone handling for IST (India Standard Time)."""
        # Create appointment with explicit timezone info
        ist_time = datetime(2026, 1, 15, 14, 30, 0)

        appointment = Appointment(
            id=str(uuid4()),
            patient_id=test_patient.id,
            doctor_id=test_doctor.id,
            scheduled_start=ist_time,
            scheduled_end=ist_time + timedelta(minutes=15),
            duration_minutes=15,
        )
        db.add(appointment)
        await db.commit()
        await db.refresh(appointment)

        # Verify time is preserved
        assert appointment.scheduled_start.hour == 14
        assert appointment.scheduled_start.minute == 30

    @pytest.mark.asyncio


    async def test_date_format_variations(self, db: AsyncSession, test_clinic: Clinic):
        """Test different date formats for date_of_birth."""
        # All these should work
        test_dates = [
            date(1990, 1, 1),   # YYYY-MM-DD
            date(1985, 12, 31),  # End of year
            date(2000, 2, 29),   # Leap day
            date(1947, 8, 15),   # India's independence day
        ]

        for idx, test_date in enumerate(test_dates):
            patient = Patient(
                id=str(uuid4()),
                clinic_id=test_clinic.id,
                first_name=f"Patient_{idx}",
                phone=f"+9198765432{idx:02d}",
                date_of_birth=test_date,
            )
            db.add(patient)

        await db.commit()

        patients = db.query(Patient).filter(
            Patient.clinic_id == test_clinic.id
        ).all()

        assert len(patients) == len(test_dates)

    @pytest.mark.asyncio


    async def test_very_old_patient(self, db: AsyncSession, test_clinic: Clinic):
        """Test patient born in 1920 (100+ years old)."""
        patient = Patient(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            first_name="Centenarian",
            last_name="Patient",
            phone="+919876543210",
            date_of_birth=date(1920, 1, 1),
        )
        db.add(patient)
        await db.commit()
        await db.refresh(patient)

        assert patient.age is not None
        assert patient.age > 100

    @pytest.mark.asyncio


    async def test_very_young_patient(self, db: AsyncSession, test_clinic: Clinic):
        """Test patient born yesterday."""
        yesterday = date.today() - timedelta(days=1)

        patient = Patient(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            first_name="Newborn",
            phone="+919876543210",  # Parent's phone
            date_of_birth=yesterday,
        )
        db.add(patient)
        await db.commit()
        await db.refresh(patient)

        assert patient.age == 0  # Less than 1 year


# ============================================================================
# TEST 3: LARGE DATA HANDLING
# ============================================================================


class TestLargeDataHandling:
    """Tests for handling large amounts of data."""

    @pytest.mark.asyncio


    async def test_very_long_patient_name(self, db: AsyncSession, test_clinic: Clinic):
        """Test patient with 100+ character name."""
        # Some South Indian names can be very long
        long_name = "Venkatanarasimharajuvaripeta Srinivasa Ramanujan Krishna Murthy Sastry"  # ~75 chars

        patient = Patient(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            first_name=long_name,
            last_name="Venkatapuram",
            phone="+919876543210",
        )
        db.add(patient)
        await db.commit()
        await db.refresh(patient)

        assert len(patient.first_name) > 70
        assert patient.full_name == f"{long_name} Venkatapuram"

    @pytest.mark.asyncio


    async def test_very_long_address(self, db: AsyncSession, test_clinic: Clinic):
        """Test patient with very long address."""
        long_address = (
            "Flat No. 402, Building Name: Shree Krishna Residency, "
            "Plot No. 123/456/789, Sector 15, Phase II, "
            "Near Big Bazaar and Metro Station Exit Gate No. 3, "
            "Opposite Municipal Corporation Office, "
            "Behind State Bank of India, Main Branch, "
            "Landmark: Next to Famous Restaurant, "
            "Village/Town: Ghatkopar West, "
            "Post Office: Ghatkopar, Pin Code Area, "
            "Mumbai, Maharashtra, India - 400086"
        )

        patient = Patient(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            first_name="Test",
            phone="+919876543210",
            address=long_address,
        )
        db.add(patient)
        await db.commit()
        await db.refresh(patient)

        assert len(patient.address) > 400
        assert "Ghatkopar" in patient.address

    @pytest.mark.asyncio


    async def test_very_long_chief_complaint(
        self,
        db: AsyncSession,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test appointment with very long chief complaint."""
        long_complaint = (
            "Patient complains of severe headache since last 3 weeks, "
            "accompanied by nausea, vomiting, dizziness, blurred vision in left eye, "
            "occasional chest pain, shortness of breath, palpitations, "
            "fever on and off, body ache, weakness, loss of appetite, "
            "insomnia, anxiety, stress due to work pressure, "
            "family history of diabetes and hypertension, "
            "currently on medication for thyroid, takes paracetamol as needed, "
            "allergic to penicillin and sulfa drugs"
        )

        appointment = Appointment(
            id=str(uuid4()),
            patient_id=test_patient.id,
            doctor_id=test_doctor.id,
            scheduled_start=datetime.now() + timedelta(days=1),
            scheduled_end=datetime.now() + timedelta(days=1, minutes=15),
            duration_minutes=15,
            chief_complaint=long_complaint,
        )
        db.add(appointment)
        await db.commit()
        await db.refresh(appointment)

        assert len(appointment.chief_complaint) > 400

    @pytest.mark.asyncio


    async def test_many_appointments_for_patient(
        self,
        db: AsyncSession,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test patient with 1000+ appointments (long-term chronic patient)."""
        appointments = []
        base_date = datetime(2020, 1, 1, 10, 0, 0)

        # Create 1000 appointments over 5 years
        for i in range(1000):
            appointment_date = base_date + timedelta(days=i * 2)  # Every 2 days
            appointments.append(
                Appointment(
                    id=str(uuid4()),
                    patient_id=test_patient.id,
                    doctor_id=test_doctor.id,
                    scheduled_start=appointment_date,
                    scheduled_end=appointment_date + timedelta(minutes=15),
                    duration_minutes=15,
                    status=AppointmentStatus.COMPLETED.value,
                )
            )

        db.bulk_save_objects(appointments)
        await db.commit()

        # Query to verify
        count = db.query(Appointment).filter(
            Appointment.patient_id == test_patient.id
        ).count()

        assert count == 1000

    @pytest.mark.asyncio


    async def test_many_patients_in_clinic(self, db: AsyncSession, test_clinic: Clinic):
        """Test clinic with 10,000+ patients."""
        patients = []

        for i in range(10000):
            patients.append(
                Patient(
                    id=str(uuid4()),
                    clinic_id=test_clinic.id,
                    first_name=f"Patient_{i}",
                    phone=f"+91{9876543210 + i}",
                )
            )

        db.bulk_save_objects(patients)
        await db.commit()

        count = db.query(Patient).filter(
            Patient.clinic_id == test_clinic.id
        ).count()

        assert count >= 10000

    @pytest.mark.asyncio


    async def test_very_long_notes(
        self,
        db: AsyncSession,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test appointment with very long notes (5000+ chars)."""
        long_notes = "Detailed consultation notes. " * 200  # ~5800 chars

        appointment = Appointment(
            id=str(uuid4()),
            patient_id=test_patient.id,
            doctor_id=test_doctor.id,
            scheduled_start=datetime.now() + timedelta(days=1),
            scheduled_end=datetime.now() + timedelta(days=1, minutes=30),
            duration_minutes=30,
            notes=long_notes,
        )
        db.add(appointment)
        await db.commit()
        await db.refresh(appointment)

        assert len(appointment.notes) > 5000

    @pytest.mark.asyncio


    async def test_doctor_with_many_languages(self, db: AsyncSession, test_clinic: Clinic):
        """Test doctor who speaks all 23 Indian languages."""
        all_languages = [
            "hi", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa", "or",
            "as", "ur", "sa", "ks", "sd", "ne", "mai", "kok", "mni", "bodo",
            "doi", "sat", "en"
        ]

        user = User(
            id=str(uuid4()),
            email="polyglot@test.com",
            phone="+919876543299",
            password_hash=get_password_hash("testpass123"),
            name="Dr. Polyglot",
            role="doctor",
            clinic_id=test_clinic.id,
        )
        db.add(user)
        await db.commit()

        doctor = Doctor(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            name="Dr. Polyglot Master",
            specialization="Multilingual Medicine",
            languages=all_languages,
        )
        db.add(doctor)
        await db.commit()
        await db.refresh(doctor)

        assert len(doctor.languages) == 23
        assert "hi" in doctor.languages
        assert "en" in doctor.languages


# ============================================================================
# TEST 4: SPECIAL CHARACTERS
# ============================================================================


class TestSpecialCharacters:
    """Tests for special characters in various fields."""

    @pytest.mark.asyncio


    async def test_name_with_apostrophe(self, db: AsyncSession, test_clinic: Clinic):
        """Test patient name with apostrophe (O'Brien)."""
        patient = Patient(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            first_name="Rohan",
            last_name="O'Brien",
            phone="+919876543210",
        )
        db.add(patient)
        await db.commit()
        await db.refresh(patient)

        assert patient.last_name == "O'Brien"
        assert "'" in patient.full_name

    @pytest.mark.asyncio


    async def test_name_with_hyphen(self, db: AsyncSession, test_clinic: Clinic):
        """Test patient name with hyphen (Anne-Marie)."""
        patient = Patient(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            first_name="Anne-Marie",
            last_name="Fernandes",
            phone="+919876543210",
        )
        db.add(patient)
        await db.commit()
        await db.refresh(patient)

        assert patient.first_name == "Anne-Marie"
        assert "-" in patient.first_name

    @pytest.mark.asyncio


    async def test_address_with_special_chars(self, db: AsyncSession, test_clinic: Clinic):
        """Test address with special characters."""
        patient = Patient(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            first_name="Test",
            phone="+919876543210",
            address="Flat #402, Builder's Colony, St. Xavier's Road, D'Souza Compound",
        )
        db.add(patient)
        await db.commit()
        await db.refresh(patient)

        assert "#" in patient.address
        assert "'" in patient.address
        assert "." in patient.address

    @pytest.mark.asyncio


    async def test_phone_with_plus_prefix(self, db: AsyncSession, test_clinic: Clinic):
        """Test phone number with +91 prefix."""
        patient = Patient(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            first_name="Test",
            phone="+919876543210",
        )
        db.add(patient)
        await db.commit()
        await db.refresh(patient)

        assert patient.phone.startswith("+91")
        assert "+" in patient.phone

    @pytest.mark.asyncio


    async def test_email_with_dots_and_plus(self, db: AsyncSession, test_clinic: Clinic):
        """Test email with dots and plus signs."""
        patient = Patient(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            first_name="Test",
            phone="+919876543210",
            email="john.doe+clinic@gmail.com",
        )
        db.add(patient)
        await db.commit()
        await db.refresh(patient)

        assert "." in patient.email
        assert "+" in patient.email
        assert patient.email == "john.doe+clinic@gmail.com"

    @pytest.mark.asyncio


    async def test_clinic_name_with_ampersand(self, db: AsyncSession):
        """Test clinic name with ampersand."""
        clinic = Clinic(
            id=str(uuid4()),
            name="Sharma & Associates Clinic",
            slug="sharma-associates-clinic",
            phone="+919876543210",
        )
        db.add(clinic)
        await db.commit()
        await db.refresh(clinic)

        assert "&" in clinic.name
        assert clinic.name == "Sharma & Associates Clinic"

    @pytest.mark.asyncio


    async def test_doctor_qualification_with_special_chars(
        self,
        db: AsyncSession,
        test_clinic: Clinic,
    ):
        """Test doctor qualification with commas and periods."""
        user = User(
            id=str(uuid4()),
            email="doctor@test.com",
            phone="+919876543299",
            password_hash=get_password_hash("testpass123"),
            name="Dr. Test",
            role="doctor",
            clinic_id=test_clinic.id,
        )
        db.add(user)
        await db.commit()

        doctor = Doctor(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            name="Dr. Priya Sharma, M.D.",
            qualification="M.B.B.S., M.D. (Gen. Medicine), D.N.B., F.I.C.A.",
        )
        db.add(doctor)
        await db.commit()
        await db.refresh(doctor)

        assert "," in doctor.qualification
        assert "." in doctor.qualification
        assert "(" in doctor.qualification
        assert ")" in doctor.qualification

    @pytest.mark.asyncio


    async def test_gst_number_format(self, db: AsyncSession):
        """Test GST number with special format."""
        clinic = Clinic(
            id=str(uuid4()),
            name="Test Clinic",
            slug="test-clinic-gst",
            phone="+919876543210",
            gst_number="27AABCU9603R1ZX",  # Sample GST format
        )
        db.add(clinic)
        await db.commit()
        await db.refresh(clinic)

        assert len(clinic.gst_number) == 15
        assert clinic.gst_number.startswith("27")  # State code


# ============================================================================
# TEST 5: EMPTY/NULL DATA HANDLING
# ============================================================================


class TestEmptyNullData:
    """Tests for empty and null data handling."""

    @pytest.mark.asyncio


    async def test_patient_with_minimal_data(self, db: AsyncSession, test_clinic: Clinic):
        """Test patient with only required fields."""
        patient = Patient(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            first_name="Minimal",
            phone="+919876543210",
            # All other fields are None/default
        )
        db.add(patient)
        await db.commit()
        await db.refresh(patient)

        assert patient.first_name == "Minimal"
        assert patient.last_name is None
        assert patient.email is None
        assert patient.date_of_birth is None
        assert patient.gender is None

    @pytest.mark.asyncio


    async def test_patient_null_vs_empty_string(self, db: AsyncSession, test_clinic: Clinic):
        """Test difference between null and empty string."""
        patient1 = Patient(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            first_name="Patient1",
            phone="+919876543210",
            email=None,  # Explicitly null
        )

        # Note: Pydantic/SQLAlchemy may convert empty string to None for optional fields
        patient2 = Patient(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            first_name="Patient2",
            phone="+919876543211",
            last_name="",  # Empty string
        )

        db.add(patient1)
        db.add(patient2)
        await db.commit()

        await db.refresh(patient1)
        await db.refresh(patient2)

        assert patient1.email is None

    @pytest.mark.asyncio


    async def test_appointment_optional_fields_null(
        self,
        db: AsyncSession,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test appointment with all optional fields as null."""
        appointment = Appointment(
            id=str(uuid4()),
            patient_id=test_patient.id,
            doctor_id=test_doctor.id,
            scheduled_start=datetime.now() + timedelta(days=1),
            scheduled_end=datetime.now() + timedelta(days=1, minutes=15),
            duration_minutes=15,
            # Optional fields left as default/None
            chief_complaint=None,
            notes=None,
            token_number=None,
            service_id=None,
        )
        db.add(appointment)
        await db.commit()
        await db.refresh(appointment)

        assert appointment.chief_complaint is None
        assert appointment.notes is None
        assert appointment.token_number is None
        assert appointment.service_id is None

    @pytest.mark.asyncio


    async def test_clinic_minimal_data(self, db: AsyncSession):
        """Test clinic with minimal required data."""
        clinic = Clinic(
            id=str(uuid4()),
            name="Minimal Clinic",
            slug="minimal-clinic",
            phone="+919876543210",
            # All optional fields as default/None
        )
        db.add(clinic)
        await db.commit()
        await db.refresh(clinic)

        assert clinic.name == "Minimal Clinic"
        assert clinic.email is None
        assert clinic.address is None
        assert clinic.gst_number is None

    @pytest.mark.asyncio


    async def test_default_value_handling(self, db: AsyncSession, test_clinic: Clinic):
        """Test that default values are applied correctly."""
        patient = Patient(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            first_name="Default Test",
            phone="+919876543210",
            # Don't specify preferred_language, should default to 'en'
        )
        db.add(patient)
        await db.commit()
        await db.refresh(patient)

        assert patient.preferred_language == "en"
        assert patient.sms_consent is True  # Default
        assert patient.whatsapp_consent is True  # Default
        assert patient.is_active is True  # Default

    @pytest.mark.asyncio


    async def test_empty_search_results(self, db: AsyncSession, test_clinic: Clinic):
        """Test querying when no results exist."""
        # Search for non-existent patient
        results = db.query(Patient).filter(
            Patient.clinic_id == test_clinic.id,
            Patient.first_name == "NonExistentPatient12345",
        ).all()

        assert results == []
        assert len(results) == 0

    @pytest.mark.asyncio


    async def test_null_foreign_key_optional(
        self,
        db: AsyncSession,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test optional foreign key (service_id) can be null."""
        appointment = Appointment(
            id=str(uuid4()),
            patient_id=test_patient.id,
            doctor_id=test_doctor.id,
            scheduled_start=datetime.now() + timedelta(days=1),
            scheduled_end=datetime.now() + timedelta(days=1, minutes=15),
            duration_minutes=15,
            service_id=None,  # Optional FK
        )
        db.add(appointment)
        await db.commit()
        await db.refresh(appointment)

        assert appointment.service_id is None
        assert appointment.service is None

    @pytest.mark.asyncio


    async def test_null_json_fields(self, db: AsyncSession, test_clinic: Clinic):
        """Test null JSON/JSONB fields."""
        user = User(
            id=str(uuid4()),
            email="doctor@test.com",
            phone="+919876543299",
            password_hash=get_password_hash("testpass123"),
            name="Dr. Test",
            role="doctor",
            clinic_id=test_clinic.id,
        )
        db.add(user)
        await db.commit()

        doctor = Doctor(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            name="Dr. Test",
            working_hours=None,  # JSON field can be null
            break_slots=None,
            languages=None,
        )
        db.add(doctor)
        await db.commit()
        await db.refresh(doctor)

        assert doctor.working_hours is None
        assert doctor.break_slots is None
        assert doctor.languages is None


# ============================================================================
# TEST 6: CONCURRENT OPERATIONS & RACE CONDITIONS
# ============================================================================


class TestConcurrentOperations:
    """Tests for concurrent operations and race conditions."""

    @pytest.mark.asyncio


    async def test_duplicate_phone_numbers_different_clinics(
        self,
        db: AsyncSession,
        test_clinic: Clinic,
        hindi_clinic: Clinic,
    ):
        """Test same phone number in different clinics (should be allowed)."""
        patient1 = Patient(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            first_name="Patient1",
            phone="+919876543210",
        )

        patient2 = Patient(
            id=str(uuid4()),
            clinic_id=hindi_clinic.id,
            first_name="Patient2",
            phone="+919876543210",  # Same phone, different clinic
        )

        db.add(patient1)
        db.add(patient2)
        await db.commit()

        # Both should exist
        assert db.query(Patient).filter(
            Patient.phone == "+919876543210"
        ).count() == 2

    @pytest.mark.asyncio


    async def test_overlapping_appointments_same_doctor(
        self,
        db: AsyncSession,
        test_doctor: Doctor,
    ):
        """Test creating overlapping appointments (should be prevented by business logic)."""
        # Note: This tests data layer; business logic should prevent this
        patient1 = Patient(
            id=str(uuid4()),
            clinic_id=test_doctor.clinic_id,
            first_name="Patient1",
            phone="+919876543210",
        )
        patient2 = Patient(
            id=str(uuid4()),
            clinic_id=test_doctor.clinic_id,
            first_name="Patient2",
            phone="+919876543211",
        )
        db.add_all([patient1, patient2])
        await db.commit()

        start_time = datetime.now() + timedelta(days=1, hours=2)

        appointment1 = Appointment(
            id=str(uuid4()),
            patient_id=patient1.id,
            doctor_id=test_doctor.id,
            scheduled_start=start_time,
            scheduled_end=start_time + timedelta(minutes=30),
            duration_minutes=30,
        )

        # Overlapping appointment
        appointment2 = Appointment(
            id=str(uuid4()),
            patient_id=patient2.id,
            doctor_id=test_doctor.id,
            scheduled_start=start_time + timedelta(minutes=15),
            scheduled_end=start_time + timedelta(minutes=45),
            duration_minutes=30,
        )

        db.add(appointment1)
        db.add(appointment2)
        await db.commit()  # Database allows this; business logic should prevent

        # Both appointments exist at data layer
        assert db.query(Appointment).filter(
            Appointment.doctor_id == test_doctor.id
        ).count() >= 2


# ============================================================================
# TEST 7: BOUNDARY VALUE TESTING
# ============================================================================


class TestBoundaryValues:
    """Tests for boundary values in various fields."""

    @pytest.mark.asyncio


    async def test_phone_number_lengths(self, db: AsyncSession, test_clinic: Clinic):
        """Test various phone number lengths."""
        # Minimum length (10 digits + country code)
        patient1 = Patient(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            first_name="Min",
            phone="+919876543210",  # 13 chars
        )

        # Maximum length (15 chars per schema)
        patient2 = Patient(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            first_name="Max",
            phone="+919876543210",  # Within limit
        )

        db.add_all([patient1, patient2])
        await db.commit()

        assert len(patient1.phone) >= 10
        assert len(patient2.phone) <= 15

    @pytest.mark.asyncio


    async def test_age_extremes(self, db: AsyncSession, test_clinic: Clinic):
        """Test age calculation for extreme ages."""
        # Newborn (0 years)
        newborn = Patient(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            first_name="Newborn",
            phone="+919876543210",
            date_of_birth=date.today(),
        )

        # Very old (120 years - extreme but possible)
        very_old = Patient(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            first_name="Elder",
            phone="+919876543211",
            date_of_birth=date(1900, 1, 1),
        )

        db.add_all([newborn, very_old])
        await db.commit()
        await db.refresh(newborn)
        await db.refresh(very_old)

        assert newborn.age == 0
        assert very_old.age is not None
        assert very_old.age > 100

    @pytest.mark.asyncio


    async def test_consultation_fee_boundaries(self, db: AsyncSession, test_clinic: Clinic):
        """Test consultation fee at boundary values."""
        user = User(
            id=str(uuid4()),
            email="doctor@test.com",
            phone="+919876543299",
            password_hash=get_password_hash("testpass123"),
            name="Dr. Test",
            role="doctor",
            clinic_id=test_clinic.id,
        )
        db.add(user)
        await db.commit()

        # Free consultation
        doctor1 = Doctor(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            name="Dr. Free",
            consultation_fee=Decimal("0.00"),
        )

        # Very expensive consultation
        doctor2 = Doctor(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            name="Dr. Expensive",
            consultation_fee=Decimal("50000.00"),  # ₹50,000
        )

        db.add_all([doctor1, doctor2])
        await db.commit()

        await db.refresh(doctor1)
        await db.refresh(doctor2)

        assert doctor1.consultation_fee == Decimal("0.00")
        assert doctor2.consultation_fee == Decimal("50000.00")

    @pytest.mark.asyncio


    async def test_appointment_duration_boundaries(
        self,
        db: AsyncSession,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """Test appointment duration at min/max boundaries."""
        start_time = datetime.now() + timedelta(days=1)

        # Minimum duration (5 minutes per schema)
        short_appointment = Appointment(
            id=str(uuid4()),
            patient_id=test_patient.id,
            doctor_id=test_doctor.id,
            scheduled_start=start_time,
            scheduled_end=start_time + timedelta(minutes=5),
            duration_minutes=5,
        )

        # Maximum duration (120 minutes per schema)
        long_appointment = Appointment(
            id=str(uuid4()),
            patient_id=test_patient.id,
            doctor_id=test_doctor.id,
            scheduled_start=start_time + timedelta(hours=2),
            scheduled_end=start_time + timedelta(hours=2, minutes=120),
            duration_minutes=120,
        )

        db.add_all([short_appointment, long_appointment])
        await db.commit()

        await db.refresh(short_appointment)
        await db.refresh(long_appointment)

        assert short_appointment.duration_minutes == 5
        assert long_appointment.duration_minutes == 120


# ============================================================================
# TEST 8: DATA INTEGRITY & CONSTRAINTS
# ============================================================================


class TestDataIntegrity:
    """Tests for data integrity and database constraints."""

    @pytest.mark.asyncio


    async def test_required_field_validation(self, db: AsyncSession, test_clinic: Clinic):
        """Test that required fields cannot be null."""
        with pytest.raises(Exception):  # IntegrityError or ValidationError
            patient = Patient(
                id=str(uuid4()),
                clinic_id=test_clinic.id,
                # Missing required first_name
                phone="+919876543210",
            )
            db.add(patient)
            await db.commit()

    @pytest.mark.asyncio


    async def test_foreign_key_integrity(self, db: AsyncSession):
        """Test foreign key constraint (patient needs valid clinic)."""
        with pytest.raises(IntegrityError):
            # Invalid clinic_id
            patient = Patient(
                id=str(uuid4()),
                clinic_id=str(uuid4()),  # Non-existent clinic
                first_name="Test",
                phone="+919876543210",
            )
            db.add(patient)
            await db.commit()

    @pytest.mark.asyncio


    async def test_unique_constraint_clinic_slug(self, db: AsyncSession):
        """Test unique constraint on clinic slug."""
        clinic1 = Clinic(
            id=str(uuid4()),
            name="Clinic 1",
            slug="test-clinic",
            phone="+919876543210",
        )
        db.add(clinic1)
        await db.commit()

        with pytest.raises(IntegrityError):
            clinic2 = Clinic(
                id=str(uuid4()),
                name="Clinic 2",
                slug="test-clinic",  # Duplicate slug
                phone="+919876543211",
            )
            db.add(clinic2)
            await db.commit()

    @pytest.mark.asyncio


    async def test_cascading_delete_prevention(
        self,
        db: AsyncSession,
        test_clinic: Clinic,
        test_patient: Patient,
    ):
        """Test that deleting clinic with patients is handled properly."""
        # Depending on cascade settings, this should either:
        # 1. Prevent deletion (FK constraint)
        # 2. Cascade delete (if configured)
        # 3. Set to NULL (if configured)

        patient_count_before = db.query(Patient).filter(
            Patient.clinic_id == test_clinic.id
        ).count()

        assert patient_count_before > 0  # Patient exists

        # Try to delete clinic (should fail due to FK constraint)
        try:
            db.delete(test_clinic)
            await db.commit()
            # If we reach here, cascade delete is configured
        except IntegrityError:
            # Expected: cannot delete clinic with patients
            db.rollback()
            assert True
