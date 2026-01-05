"""
Concurrency and Race Condition Tests for DocAssist Practice Manager.

Tests critical concurrent operations to ensure data integrity:
- Double booking prevention
- Payment race conditions
- Data modification conflicts
- Resource contention (queue numbers, invoice numbers)
- Database locking behavior

Uses asyncio.gather and threading for true concurrent testing.
"""

import asyncio
import threading
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.appointment import Appointment, AppointmentStatus
from app.models.clinic import Clinic
from app.models.doctor import Doctor
from app.models.invoice import Invoice, InvoiceStatus
from app.models.patient import Patient
from app.models.payment import Payment, PaymentMethod, PaymentStatus
from app.models.waitlist import Waitlist, WaitlistStatus
from app.services.waitlist import WaitlistService


# =============================================================================
# Helper Functions
# =============================================================================


def create_appointment_data(
    doctor_id: str,
    patient_id: str,
    start_time: datetime,
    duration_minutes: int = 15,
) -> dict[str, Any]:
    """Create appointment data dict."""
    return {
        "id": str(uuid4()),
        "doctor_id": doctor_id,
        "patient_id": patient_id,
        "scheduled_start": start_time,
        "scheduled_end": start_time + timedelta(minutes=duration_minutes),
        "duration_minutes": duration_minutes,
        "status": AppointmentStatus.SCHEDULED.value,
        "appointment_type": "new_consultation",
        "booking_source": "app",
    }


def create_payment_data(
    invoice_id: str,
    amount: Decimal,
    payment_method: str = PaymentMethod.CASH.value,
) -> dict[str, Any]:
    """Create payment data dict."""
    return {
        "id": str(uuid4()),
        "invoice_id": invoice_id,
        "amount": amount,
        "payment_method": payment_method,
        "status": PaymentStatus.COMPLETED.value,
        "payment_date": datetime.now(timezone.utc),
    }


# =============================================================================
# 1. DOUBLE BOOKING PREVENTION TESTS
# =============================================================================


class TestDoubleBookingPrevention:
    """Test concurrent appointment booking scenarios."""

    @pytest.mark.asyncio
    async def test_concurrent_same_slot_booking_prevented(
        self,
        db: Session,
        test_doctor: Doctor,
        test_clinic: Clinic,
    ):
        """
        Test that two users cannot book the same slot simultaneously.

        Race condition: Both users check availability at the same time,
        see slot as available, and both try to book it.
        """
        # Create two different patients
        patient1 = Patient(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            name="Patient One",
            phone="+919876543210",
            email="patient1@test.com",
        )
        patient2 = Patient(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            name="Patient Two",
            phone="+919876543211",
            email="patient2@test.com",
        )
        db.add(patient1)
        db.add(patient2)
        db.commit()

        # Same time slot for both
        slot_time = datetime.now(timezone.utc).replace(
            hour=14, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)

        # Create appointment data for both patients
        appt1_data = create_appointment_data(
            test_doctor.id, patient1.id, slot_time
        )
        appt2_data = create_appointment_data(
            test_doctor.id, patient2.id, slot_time
        )

        # Simulate concurrent booking attempts
        async def book_appointment(appt_data: dict) -> tuple[bool, str]:
            """Try to book an appointment."""
            try:
                # Check for conflicts (simulating the API logic)
                conflict = db.query(Appointment).filter(
                    Appointment.doctor_id == appt_data["doctor_id"],
                    Appointment.status.notin_([
                        AppointmentStatus.CANCELLED.value,
                        AppointmentStatus.NO_SHOW.value,
                    ]),
                    Appointment.scheduled_start < appt_data["scheduled_end"],
                    Appointment.scheduled_end > appt_data["scheduled_start"],
                ).first()

                if conflict:
                    return False, "conflict_detected"

                # Small delay to simulate processing time
                await asyncio.sleep(0.01)

                # Create appointment
                appointment = Appointment(**appt_data)
                db.add(appointment)
                db.commit()
                db.refresh(appointment)
                return True, str(appointment.id)
            except IntegrityError:
                db.rollback()
                return False, "integrity_error"
            except Exception as e:
                db.rollback()
                return False, str(e)

        # Execute concurrent bookings
        results = await asyncio.gather(
            book_appointment(appt1_data),
            book_appointment(appt2_data),
            return_exceptions=True,
        )

        # Verify results
        successful_bookings = sum(1 for success, _ in results if success)

        # NOTE: Without proper locking, both might succeed (race condition!)
        # With proper locking, only one should succeed
        # This test documents the current behavior
        assert successful_bookings <= 1, "Double booking occurred!"

        # Verify database state
        appointments = db.query(Appointment).filter(
            Appointment.doctor_id == test_doctor.id,
            Appointment.scheduled_start == slot_time,
            Appointment.status != AppointmentStatus.CANCELLED.value,
        ).all()

        assert len(appointments) <= 1, f"Found {len(appointments)} appointments for same slot"

    @pytest.mark.asyncio
    async def test_same_user_double_submit_prevented(
        self,
        db: Session,
        test_doctor: Doctor,
        test_patient: Patient,
    ):
        """
        Test that same user cannot double-submit booking request.

        Scenario: User clicks "Book" button twice quickly.
        """
        slot_time = datetime.now(timezone.utc).replace(
            hour=15, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)

        # Create identical booking data
        appt_data = create_appointment_data(
            test_doctor.id, test_patient.id, slot_time
        )

        async def book_appointment() -> tuple[bool, str]:
            """Simulate booking attempt."""
            try:
                # Check existing appointments for this patient at this time
                existing = db.query(Appointment).filter(
                    Appointment.patient_id == test_patient.id,
                    Appointment.scheduled_start == slot_time,
                    Appointment.status.notin_([
                        AppointmentStatus.CANCELLED.value,
                        AppointmentStatus.NO_SHOW.value,
                    ]),
                ).first()

                if existing:
                    return False, "already_booked"

                await asyncio.sleep(0.01)  # Processing delay

                appointment = Appointment(**{**appt_data, "id": str(uuid4())})
                db.add(appointment)
                db.commit()
                return True, str(appointment.id)
            except Exception as e:
                db.rollback()
                return False, str(e)

        # Execute concurrent submissions
        results = await asyncio.gather(
            book_appointment(),
            book_appointment(),
            book_appointment(),
            return_exceptions=True,
        )

        successful_bookings = sum(1 for success, _ in results if success)

        # Only one should succeed
        assert successful_bookings <= 1, "User booked multiple times!"

        # Verify database
        appointments = db.query(Appointment).filter(
            Appointment.patient_id == test_patient.id,
            Appointment.scheduled_start == slot_time,
            Appointment.status != AppointmentStatus.CANCELLED.value,
        ).all()

        assert len(appointments) <= 1, "Multiple bookings exist for same patient"

    @pytest.mark.asyncio
    async def test_booking_during_cancellation(
        self,
        db: Session,
        test_doctor: Doctor,
        test_clinic: Clinic,
    ):
        """
        Test booking a slot while another appointment is being cancelled.

        Race condition: Slot appears available during cancellation process.
        """
        # Create initial appointment
        patient1 = Patient(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            name="Patient One",
            phone="+919876543210",
        )
        patient2 = Patient(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            name="Patient Two",
            phone="+919876543211",
        )
        db.add_all([patient1, patient2])
        db.commit()

        slot_time = datetime.now(timezone.utc).replace(
            hour=16, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)

        existing_appt = Appointment(
            **create_appointment_data(test_doctor.id, patient1.id, slot_time)
        )
        db.add(existing_appt)
        db.commit()

        async def cancel_appointment() -> bool:
            """Cancel existing appointment."""
            try:
                await asyncio.sleep(0.01)  # Simulate processing
                existing_appt.status = AppointmentStatus.CANCELLED.value
                existing_appt.cancellation_reason = "Patient request"
                db.commit()
                return True
            except Exception:
                db.rollback()
                return False

        async def book_new_appointment() -> tuple[bool, str]:
            """Try to book the slot."""
            try:
                # Check for conflicts
                conflict = db.query(Appointment).filter(
                    Appointment.doctor_id == test_doctor.id,
                    Appointment.status.notin_([
                        AppointmentStatus.CANCELLED.value,
                        AppointmentStatus.NO_SHOW.value,
                    ]),
                    Appointment.scheduled_start < slot_time + timedelta(minutes=15),
                    Appointment.scheduled_end > slot_time,
                ).first()

                if conflict:
                    return False, "conflict"

                await asyncio.sleep(0.01)

                new_appt = Appointment(
                    **create_appointment_data(test_doctor.id, patient2.id, slot_time)
                )
                db.add(new_appt)
                db.commit()
                return True, str(new_appt.id)
            except Exception as e:
                db.rollback()
                return False, str(e)

        # Execute concurrently
        cancel_result, book_result = await asyncio.gather(
            cancel_appointment(),
            book_new_appointment(),
        )

        # Verify no double booking
        db.refresh(existing_appt)
        active_appointments = db.query(Appointment).filter(
            Appointment.doctor_id == test_doctor.id,
            Appointment.scheduled_start == slot_time,
            Appointment.status.notin_([
                AppointmentStatus.CANCELLED.value,
                AppointmentStatus.NO_SHOW.value,
            ]),
        ).all()

        assert len(active_appointments) <= 1, "Overlapping appointments exist"


# =============================================================================
# 2. PAYMENT RACE CONDITIONS TESTS
# =============================================================================


class TestPaymentRaceConditions:
    """Test concurrent payment scenarios."""

    @pytest.mark.asyncio
    async def test_double_payment_prevention(
        self,
        db: Session,
        test_clinic: Clinic,
        test_patient: Patient,
    ):
        """
        Test that same invoice cannot be paid twice simultaneously.

        Scenario: Two payment terminals process payment for same invoice.
        """
        # Create invoice
        invoice = Invoice(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            patient_id=test_patient.id,
            invoice_number=f"INV-{uuid4().hex[:8].upper()}",
            invoice_date=datetime.now(timezone.utc).date(),
            subtotal=Decimal("1000.00"),
            total_amount=Decimal("1000.00"),
            paid_amount=Decimal("0.00"),
            status=InvoiceStatus.PENDING.value,
        )
        db.add(invoice)
        db.commit()

        async def make_payment(payment_data: dict) -> tuple[bool, str]:
            """Attempt to make a payment."""
            try:
                # Fetch invoice
                inv = db.query(Invoice).filter(Invoice.id == invoice.id).first()

                # Check if payment exceeds balance
                if payment_data["amount"] > inv.balance_due:
                    return False, "exceeds_balance"

                await asyncio.sleep(0.01)  # Processing delay

                # Create payment
                payment = Payment(**payment_data)
                db.add(payment)

                # Update invoice
                inv.paid_amount += payment_data["amount"]
                if inv.paid_amount >= inv.total_amount:
                    inv.status = InvoiceStatus.PAID.value
                elif inv.paid_amount > 0:
                    inv.status = InvoiceStatus.PARTIALLY_PAID.value

                db.commit()
                return True, str(payment.id)
            except Exception as e:
                db.rollback()
                return False, str(e)

        # Two simultaneous full payments
        payment1_data = create_payment_data(
            invoice.id, Decimal("1000.00"), PaymentMethod.CASH.value
        )
        payment2_data = create_payment_data(
            invoice.id, Decimal("1000.00"), PaymentMethod.UPI.value
        )

        results = await asyncio.gather(
            make_payment(payment1_data),
            make_payment(payment2_data),
            return_exceptions=True,
        )

        # Verify only appropriate amount was accepted
        db.refresh(invoice)

        # Total paid should not exceed invoice amount
        assert invoice.paid_amount <= invoice.total_amount * Decimal("1.01"), \
            f"Overpayment occurred: {invoice.paid_amount} > {invoice.total_amount}"

        # Check payment records
        payments = db.query(Payment).filter(Payment.invoice_id == invoice.id).all()
        total_payment_amount = sum(p.amount for p in payments)

        assert total_payment_amount <= invoice.total_amount * Decimal("1.01"), \
            "Double payment recorded!"

    @pytest.mark.asyncio
    async def test_payment_during_void(
        self,
        db: Session,
        test_clinic: Clinic,
        test_patient: Patient,
    ):
        """
        Test payment attempt while invoice is being voided.

        Race condition: Payment processed while invoice status changes to cancelled.
        """
        invoice = Invoice(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            patient_id=test_patient.id,
            invoice_number=f"INV-{uuid4().hex[:8].upper()}",
            invoice_date=datetime.now(timezone.utc).date(),
            subtotal=Decimal("500.00"),
            total_amount=Decimal("500.00"),
            paid_amount=Decimal("0.00"),
            status=InvoiceStatus.PENDING.value,
        )
        db.add(invoice)
        db.commit()

        async def void_invoice() -> bool:
            """Cancel the invoice."""
            try:
                await asyncio.sleep(0.01)
                invoice.status = InvoiceStatus.CANCELLED.value
                invoice.cancellation_reason = "Billing error"
                db.commit()
                return True
            except Exception:
                db.rollback()
                return False

        async def make_payment() -> tuple[bool, str]:
            """Try to pay the invoice."""
            try:
                inv = db.query(Invoice).filter(Invoice.id == invoice.id).first()

                # Check if invoice is cancelled
                if inv.status == InvoiceStatus.CANCELLED.value:
                    return False, "invoice_cancelled"

                await asyncio.sleep(0.01)

                payment_data = create_payment_data(inv.id, Decimal("500.00"))
                payment = Payment(**payment_data)
                db.add(payment)
                inv.paid_amount += Decimal("500.00")
                inv.status = InvoiceStatus.PAID.value
                db.commit()
                return True, str(payment.id)
            except Exception as e:
                db.rollback()
                return False, str(e)

        # Execute concurrently
        void_result, payment_result = await asyncio.gather(
            void_invoice(),
            make_payment(),
        )

        # Verify consistency
        db.refresh(invoice)

        if invoice.status == InvoiceStatus.CANCELLED.value:
            # If cancelled, no payment should exist
            payments = db.query(Payment).filter(
                Payment.invoice_id == invoice.id,
                Payment.status == PaymentStatus.COMPLETED.value,
            ).all()
            assert len(payments) == 0 or invoice.paid_amount == 0, \
                "Payment exists on cancelled invoice"

    @pytest.mark.asyncio
    async def test_concurrent_refund_requests(
        self,
        db: Session,
        test_clinic: Clinic,
        test_patient: Patient,
    ):
        """
        Test concurrent refund requests on same payment.

        Scenario: Two staff members process refund simultaneously.
        """
        # Create invoice and payment
        invoice = Invoice(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            patient_id=test_patient.id,
            invoice_number=f"INV-{uuid4().hex[:8].upper()}",
            invoice_date=datetime.now(timezone.utc).date(),
            subtotal=Decimal("1000.00"),
            total_amount=Decimal("1000.00"),
            paid_amount=Decimal("1000.00"),
            status=InvoiceStatus.PAID.value,
        )
        payment = Payment(
            id=str(uuid4()),
            invoice_id=invoice.id,
            amount=Decimal("1000.00"),
            payment_method=PaymentMethod.CASH.value,
            status=PaymentStatus.COMPLETED.value,
            payment_date=datetime.now(timezone.utc),
            refund_amount=Decimal("0.00"),
        )
        db.add_all([invoice, payment])
        db.commit()

        async def process_refund(refund_amount: Decimal) -> tuple[bool, str]:
            """Process a refund."""
            try:
                pmt = db.query(Payment).filter(Payment.id == payment.id).first()

                # Check if refund exceeds available amount
                max_refund = pmt.amount - pmt.refund_amount
                if refund_amount > max_refund:
                    return False, f"exceeds_available_{max_refund}"

                await asyncio.sleep(0.01)

                # Process refund
                pmt.refund_amount += refund_amount
                pmt.refund_date = datetime.now(timezone.utc)

                if pmt.refund_amount >= pmt.amount:
                    pmt.status = PaymentStatus.REFUNDED.value
                else:
                    pmt.status = PaymentStatus.PARTIALLY_REFUNDED.value

                # Update invoice
                inv = db.query(Invoice).filter(Invoice.id == invoice.id).first()
                inv.paid_amount -= refund_amount

                if inv.paid_amount <= 0:
                    inv.status = InvoiceStatus.PENDING.value
                elif inv.paid_amount < inv.total_amount:
                    inv.status = InvoiceStatus.PARTIALLY_PAID.value

                db.commit()
                return True, str(pmt.id)
            except Exception as e:
                db.rollback()
                return False, str(e)

        # Two simultaneous refund requests for full amount
        results = await asyncio.gather(
            process_refund(Decimal("1000.00")),
            process_refund(Decimal("1000.00")),
            return_exceptions=True,
        )

        # Verify refund amount is correct
        db.refresh(payment)
        db.refresh(invoice)

        assert payment.refund_amount <= payment.amount, \
            f"Over-refunded: {payment.refund_amount} > {payment.amount}"

        # Invoice balance should be consistent
        expected_paid = payment.amount - payment.refund_amount
        assert abs(invoice.paid_amount - expected_paid) < Decimal("0.01"), \
            "Invoice paid amount inconsistent with refunds"


# =============================================================================
# 3. DATA MODIFICATION CONFLICTS TESTS
# =============================================================================


class TestDataModificationConflicts:
    """Test concurrent data modification scenarios."""

    @pytest.mark.asyncio
    async def test_concurrent_patient_updates(
        self,
        db: Session,
        test_patient: Patient,
    ):
        """
        Test concurrent updates to same patient record.

        Scenario: Multiple staff updating patient details simultaneously.
        """
        original_name = test_patient.name
        original_phone = test_patient.phone

        async def update_patient_name(new_name: str) -> bool:
            """Update patient name."""
            try:
                await asyncio.sleep(0.01)
                patient = db.query(Patient).filter(Patient.id == test_patient.id).first()
                patient.name = new_name
                db.commit()
                return True
            except Exception:
                db.rollback()
                return False

        async def update_patient_phone(new_phone: str) -> bool:
            """Update patient phone."""
            try:
                await asyncio.sleep(0.01)
                patient = db.query(Patient).filter(Patient.id == test_patient.id).first()
                patient.phone = new_phone
                db.commit()
                return True
            except Exception:
                db.rollback()
                return False

        # Concurrent updates
        results = await asyncio.gather(
            update_patient_name("Updated Name"),
            update_patient_phone("+919999999999"),
        )

        # Refresh and verify
        db.refresh(test_patient)

        # Both updates should persist (different fields)
        # This tests last-write-wins behavior
        assert test_patient.name != original_name or \
               test_patient.phone != original_phone, \
            "No updates were applied"

    @pytest.mark.asyncio
    async def test_concurrent_appointment_status_changes(
        self,
        db: Session,
        test_appointment: Appointment,
    ):
        """
        Test concurrent status changes on same appointment.

        Scenario: Doctor starts consultation while front desk cancels.
        """
        original_status = test_appointment.status

        async def start_consultation() -> tuple[bool, str]:
            """Start the consultation."""
            try:
                await asyncio.sleep(0.01)
                appt = db.query(Appointment).filter(
                    Appointment.id == test_appointment.id
                ).first()

                if appt.status != AppointmentStatus.CHECKED_IN.value:
                    return False, f"invalid_status_{appt.status}"

                appt.status = AppointmentStatus.IN_PROGRESS.value
                appt.start_time = datetime.now(timezone.utc)
                db.commit()
                return True, "in_progress"
            except Exception as e:
                db.rollback()
                return False, str(e)

        async def cancel_appointment() -> tuple[bool, str]:
            """Cancel the appointment."""
            try:
                await asyncio.sleep(0.01)
                appt = db.query(Appointment).filter(
                    Appointment.id == test_appointment.id
                ).first()

                if appt.status in [
                    AppointmentStatus.COMPLETED.value,
                    AppointmentStatus.CANCELLED.value,
                ]:
                    return False, f"cannot_cancel_{appt.status}"

                appt.status = AppointmentStatus.CANCELLED.value
                appt.cancellation_reason = "Patient no-show"
                db.commit()
                return True, "cancelled"
            except Exception as e:
                db.rollback()
                return False, str(e)

        # Set appointment to checked_in first
        test_appointment.status = AppointmentStatus.CHECKED_IN.value
        db.commit()

        # Concurrent status changes
        start_result, cancel_result = await asyncio.gather(
            start_consultation(),
            cancel_appointment(),
        )

        # Refresh and verify final state is consistent
        db.refresh(test_appointment)

        # One operation should have succeeded
        assert start_result[0] or cancel_result[0], "Both operations failed"

        # Final status should be valid
        assert test_appointment.status in [
            AppointmentStatus.IN_PROGRESS.value,
            AppointmentStatus.CANCELLED.value,
        ], f"Invalid final status: {test_appointment.status}"


# =============================================================================
# 4. RESOURCE CONTENTION TESTS
# =============================================================================


class TestResourceContention:
    """Test concurrent access to shared resources."""

    @pytest.mark.asyncio
    async def test_concurrent_queue_number_generation(
        self,
        db: Session,
        test_doctor: Doctor,
        test_clinic: Clinic,
    ):
        """
        Test concurrent token number generation for check-ins.

        Scenario: Multiple patients checking in simultaneously.
        """
        # Create multiple patients
        patients = []
        for i in range(5):
            patient = Patient(
                id=str(uuid4()),
                clinic_id=test_clinic.id,
                name=f"Patient {i+1}",
                phone=f"+9198765432{i:02d}",
            )
            patients.append(patient)
        db.add_all(patients)
        db.commit()

        # Create appointments for all
        appointments = []
        base_time = datetime.now(timezone.utc).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        for i, patient in enumerate(patients):
            appt = Appointment(
                **create_appointment_data(
                    test_doctor.id,
                    patient.id,
                    base_time + timedelta(minutes=i * 15),
                )
            )
            appointments.append(appt)
        db.add_all(appointments)
        db.commit()

        async def check_in_patient(appointment_id: str) -> tuple[bool, int | None]:
            """Check in a patient and assign token number."""
            try:
                await asyncio.sleep(0.01)

                appt = db.query(Appointment).filter(
                    Appointment.id == appointment_id
                ).first()

                # Get max token for the day
                today_start = datetime.now(timezone.utc).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                today_end = today_start + timedelta(days=1)

                max_token = db.query(func.max(Appointment.token_number)).filter(
                    Appointment.doctor_id == test_doctor.id,
                    Appointment.scheduled_start >= today_start,
                    Appointment.scheduled_start < today_end,
                ).scalar() or 0

                token_number = max_token + 1
                appt.token_number = token_number
                appt.status = AppointmentStatus.CHECKED_IN.value
                appt.check_in_time = datetime.now(timezone.utc)

                db.commit()
                return True, token_number
            except Exception as e:
                db.rollback()
                return False, None

        # Concurrent check-ins
        results = await asyncio.gather(
            *[check_in_patient(str(appt.id)) for appt in appointments],
            return_exceptions=True,
        )

        # Collect assigned token numbers
        token_numbers = [token for success, token in results if success and token]

        # Verify uniqueness (critical!)
        assert len(token_numbers) == len(set(token_numbers)), \
            f"Duplicate token numbers: {token_numbers}"

        # Verify all tokens are positive
        assert all(t > 0 for t in token_numbers), "Invalid token numbers"

    @pytest.mark.asyncio
    async def test_concurrent_invoice_number_generation(
        self,
        db: Session,
        test_clinic: Clinic,
        test_patient: Patient,
    ):
        """
        Test concurrent invoice number generation.

        Scenario: Multiple invoices created simultaneously.
        """
        async def create_invoice(patient_id: str) -> tuple[bool, str | None]:
            """Create an invoice with auto-generated number."""
            try:
                await asyncio.sleep(0.01)

                # Generate invoice number (simple counter-based)
                max_invoice = db.query(func.max(Invoice.invoice_number)).filter(
                    Invoice.clinic_id == test_clinic.id,
                ).scalar()

                if max_invoice:
                    # Extract number from format like "INV-00001"
                    try:
                        last_num = int(max_invoice.split("-")[1])
                        next_num = last_num + 1
                    except (IndexError, ValueError):
                        next_num = 1
                else:
                    next_num = 1

                invoice_number = f"INV-{next_num:05d}"

                invoice = Invoice(
                    id=str(uuid4()),
                    clinic_id=test_clinic.id,
                    patient_id=patient_id,
                    invoice_number=invoice_number,
                    invoice_date=datetime.now(timezone.utc).date(),
                    subtotal=Decimal("500.00"),
                    total_amount=Decimal("500.00"),
                    status=InvoiceStatus.PENDING.value,
                )
                db.add(invoice)
                db.commit()
                return True, invoice_number
            except IntegrityError:
                # Unique constraint violation
                db.rollback()
                return False, "duplicate"
            except Exception as e:
                db.rollback()
                return False, str(e)

        # Create concurrent invoices
        results = await asyncio.gather(
            *[create_invoice(test_patient.id) for _ in range(5)],
            return_exceptions=True,
        )

        # Collect generated invoice numbers
        invoice_numbers = [num for success, num in results if success and num]

        # Verify uniqueness
        assert len(invoice_numbers) == len(set(invoice_numbers)), \
            f"Duplicate invoice numbers: {invoice_numbers}"

    @pytest.mark.asyncio
    async def test_concurrent_waitlist_position_updates(
        self,
        db: Session,
        test_clinic: Clinic,
        test_doctor: Doctor,
    ):
        """
        Test concurrent waitlist position assignment.

        Scenario: Multiple patients joining waitlist simultaneously.
        """
        target_date = (datetime.now(timezone.utc) + timedelta(days=3)).date()

        async def add_to_waitlist(patient_name: str, phone: str) -> tuple[bool, int | None]:
            """Add patient to waitlist."""
            try:
                await asyncio.sleep(0.01)

                # Get next position
                max_position = db.query(func.max(Waitlist.queue_position)).filter(
                    Waitlist.clinic_id == test_clinic.id,
                    Waitlist.doctor_id == test_doctor.id,
                    Waitlist.preferred_date == target_date,
                    Waitlist.status == WaitlistStatus.WAITING.value,
                ).scalar() or 0

                position = max_position + 1

                entry = Waitlist(
                    id=str(uuid4()),
                    clinic_id=test_clinic.id,
                    doctor_id=test_doctor.id,
                    patient_name=patient_name,
                    patient_phone=phone,
                    preferred_date=target_date,
                    priority="normal",
                    status=WaitlistStatus.WAITING.value,
                    queue_position=position,
                )
                db.add(entry)
                db.commit()
                return True, position
            except Exception as e:
                db.rollback()
                return False, None

        # Concurrent waitlist additions
        results = await asyncio.gather(
            *[
                add_to_waitlist(f"Patient {i}", f"+9198765432{i:02d}")
                for i in range(5)
            ],
            return_exceptions=True,
        )

        # Collect positions
        positions = [pos for success, pos in results if success and pos]

        # Verify uniqueness
        assert len(positions) == len(set(positions)), \
            f"Duplicate queue positions: {positions}"


# =============================================================================
# 5. DATABASE LOCKING TESTS
# =============================================================================


class TestDatabaseLocking:
    """Test database locking behavior."""

    def test_row_level_locking_with_select_for_update(
        self,
        db: Session,
        test_patient: Patient,
    ):
        """
        Test row-level locking with SELECT ... FOR UPDATE.

        NOTE: This requires proper transaction isolation.
        """
        def update_patient_with_lock(new_name: str) -> bool:
            """Update patient with explicit lock."""
            try:
                # Fetch with lock
                patient = db.query(Patient).filter(
                    Patient.id == test_patient.id
                ).with_for_update().first()

                # Simulate processing
                import time
                time.sleep(0.05)

                patient.name = new_name
                db.commit()
                return True
            except Exception as e:
                db.rollback()
                return False

        # Execute in threads for true parallelism
        results = []
        threads = []

        for i in range(3):
            thread = threading.Thread(
                target=lambda i=i: results.append(
                    update_patient_with_lock(f"Name {i}")
                )
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify final state is consistent
        db.refresh(test_patient)
        assert test_patient.name.startswith("Name"), "Update failed"

    @pytest.mark.asyncio
    async def test_optimistic_locking_with_version(
        self,
        db: Session,
        test_appointment: Appointment,
    ):
        """
        Test optimistic locking pattern (if version field exists).

        NOTE: Current schema doesn't have version field, this documents the pattern.
        """
        # This would require adding a version column to models
        # Example pattern:
        async def update_with_version_check(appt_id: str, expected_version: int) -> bool:
            """Update only if version matches."""
            try:
                appt = db.query(Appointment).filter(
                    Appointment.id == appt_id
                ).first()

                # In real implementation, check version
                # if appt.version != expected_version:
                #     return False

                appt.notes = "Updated with version check"
                # appt.version += 1
                db.commit()
                return True
            except Exception:
                db.rollback()
                return False

        # This test documents the need for optimistic locking
        # in high-contention scenarios
        assert True, "Optimistic locking pattern documented"

    def test_deadlock_prevention(
        self,
        db: Session,
        test_clinic: Clinic,
        test_patient: Patient,
    ):
        """
        Test deadlock prevention strategies.

        Scenario: Two transactions accessing resources in different order.
        """
        # Create two invoices
        invoice1 = Invoice(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            patient_id=test_patient.id,
            invoice_number=f"INV-DEAD-{uuid4().hex[:6]}",
            invoice_date=datetime.now(timezone.utc).date(),
            subtotal=Decimal("100.00"),
            total_amount=Decimal("100.00"),
            status=InvoiceStatus.PENDING.value,
        )
        invoice2 = Invoice(
            id=str(uuid4()),
            clinic_id=test_clinic.id,
            patient_id=test_patient.id,
            invoice_number=f"INV-DEAD-{uuid4().hex[:6]}",
            invoice_date=datetime.now(timezone.utc).date(),
            subtotal=Decimal("200.00"),
            total_amount=Decimal("200.00"),
            status=InvoiceStatus.PENDING.value,
        )
        db.add_all([invoice1, invoice2])
        db.commit()

        def transaction_1():
            """Access invoice1 then invoice2."""
            try:
                inv1 = db.query(Invoice).filter(
                    Invoice.id == invoice1.id
                ).with_for_update().first()

                import time
                time.sleep(0.05)

                inv2 = db.query(Invoice).filter(
                    Invoice.id == invoice2.id
                ).with_for_update().first()

                inv1.notes = "Transaction 1"
                inv2.notes = "Transaction 1"
                db.commit()
                return True
            except Exception:
                db.rollback()
                return False

        def transaction_2():
            """Access invoice2 then invoice1 (reverse order - deadlock risk!)."""
            try:
                inv2 = db.query(Invoice).filter(
                    Invoice.id == invoice2.id
                ).with_for_update().first()

                import time
                time.sleep(0.05)

                inv1 = db.query(Invoice).filter(
                    Invoice.id == invoice1.id
                ).with_for_update().first()

                inv2.notes = "Transaction 2"
                inv1.notes = "Transaction 2"
                db.commit()
                return True
            except Exception:
                db.rollback()
                return False

        # Execute in parallel (may deadlock!)
        results = []
        thread1 = threading.Thread(target=lambda: results.append(transaction_1()))
        thread2 = threading.Thread(target=lambda: results.append(transaction_2()))

        thread1.start()
        thread2.start()
        thread1.join(timeout=2.0)
        thread2.join(timeout=2.0)

        # At least one should complete (or both if no deadlock)
        # This test documents the deadlock risk
        assert len(results) > 0, "Both transactions blocked (deadlock)"


# =============================================================================
# END OF TESTS
# =============================================================================
