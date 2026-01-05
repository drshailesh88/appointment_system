"""
Mixed Load Test - Realistic Traffic Simulation.

Simulates realistic clinic traffic with:
- 40% Reception operations (search, booking, check-in)
- 30% Doctor operations (schedule viewing, patient details)
- 20% Analytics operations (dashboards, reports)
- 10% Management operations (staff, settings)

This represents typical usage patterns in a busy clinic.
"""

import random
from datetime import datetime, timedelta, timezone

from faker import Faker
from locust import HttpUser, between, task

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import CONFIG

fake = Faker("en_IN")


class RealisticClinicUser(HttpUser):
    """Simulates realistic mixed clinic operations."""

    wait_time = between(1, 5)  # Realistic think time
    access_token = None
    clinic_id = None
    doctor_id = None

    def on_start(self):
        """Login and initialize."""
        self.login()
        self.clinic_id = CONFIG.test_clinic_id
        self.doctor_id = CONFIG.test_doctor_id

    def login(self):
        """Authenticate."""
        response = self.client.post(
            "/api/v1/auth/login/json",
            json={
                "email": CONFIG.admin_email,
                "password": CONFIG.admin_password,
            },
            name="auth_login",
        )

        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]

    def get_headers(self) -> dict:
        """Get authorization headers."""
        if not self.access_token:
            self.login()
        return {"Authorization": f"Bearer {self.access_token}"}

    # ========== RECEPTION OPERATIONS (40% of traffic) ==========

    @task(15)
    def search_patient_quick(self):
        """Quick patient search (most common operation)."""
        search_terms = [
            fake.first_name(),
            fake.last_name(),
            fake.phone_number()[:10],
            f"{fake.first_name()} {fake.last_name()}",
        ]

        self.client.get(
            "/api/v1/patients/search",
            params={"q": random.choice(search_terms), "limit": 20},
            headers=self.get_headers(),
            name="reception_search_patient",
        )

    @task(10)
    def view_today_appointments(self):
        """View today's appointments (frequently checked)."""
        self.client.get(
            "/api/v1/appointments/today",
            params={"doctor_id": self.doctor_id} if self.doctor_id else {},
            headers=self.get_headers(),
            name="reception_today_appointments",
        )

    @task(7)
    def check_slot_availability(self):
        """Check available time slots."""
        if not self.doctor_id:
            return

        # Check for today, tomorrow, or next few days
        days_ahead = random.choice([0, 1, 2, 3, 7])
        target_date = (datetime.now(timezone.utc) + timedelta(days=days_ahead)).date()

        self.client.post(
            "/api/v1/appointments/slots/availability",
            json={
                "doctor_id": self.doctor_id,
                "date": target_date.isoformat(),
                "duration_minutes": random.choice([15, 30, 45]),
            },
            headers=self.get_headers(),
            name="reception_check_slots",
        )

    @task(5)
    def book_new_appointment(self):
        """Book a new appointment."""
        if not self.doctor_id or not CONFIG.test_patient_id:
            return

        # Schedule for random future date
        days_ahead = random.choice([1, 2, 3, 7])
        future_date = datetime.now(timezone.utc) + timedelta(days=days_ahead)
        scheduled_time = future_date.replace(
            hour=random.randint(9, 17), minute=random.choice([0, 15, 30, 45]), second=0, microsecond=0
        )

        appointment_data = {
            "patient_id": CONFIG.test_patient_id,
            "doctor_id": self.doctor_id,
            "scheduled_start": scheduled_time.isoformat(),
            "duration_minutes": random.choice([15, 30, 45]),
            "appointment_type": random.choice(
                ["CONSULTATION", "FOLLOW_UP", "PROCEDURE", "EMERGENCY"]
            ),
            "booking_source": random.choice(
                ["FRONT_DESK", "PHONE", "ONLINE", "WALK_IN"]
            ),
            "chief_complaint": fake.sentence(nb_words=random.randint(4, 10)),
        }

        if CONFIG.test_service_id:
            appointment_data["service_id"] = CONFIG.test_service_id

        self.client.post(
            "/api/v1/appointments/",
            json=appointment_data,
            headers=self.get_headers(),
            name="reception_book_appointment",
        )

    @task(3)
    def view_waitlist(self):
        """View clinic waitlist."""
        self.client.get(
            "/api/v1/waitlist/",
            params={"clinic_id": self.clinic_id} if self.clinic_id else {},
            headers=self.get_headers(),
            name="reception_view_waitlist",
        )

    @task(2)
    def list_patients(self):
        """List patients (for reference)."""
        self.client.get(
            "/api/v1/patients/",
            params={
                "clinic_id": self.clinic_id,
                "active_only": True,
                "limit": 50,
            },
            headers=self.get_headers(),
            name="reception_list_patients",
        )

    # ========== DOCTOR OPERATIONS (30% of traffic) ==========

    @task(12)
    def view_doctor_schedule(self):
        """View doctor's daily schedule."""
        if not self.doctor_id:
            return

        # View today, yesterday, or tomorrow
        days_offset = random.choice([0, -1, 1])
        target_date = (datetime.now(timezone.utc) + timedelta(days=days_offset)).date()

        self.client.get(
            f"/api/v1/appointments/doctor/{self.doctor_id}/schedule",
            params={"schedule_date": target_date.isoformat()},
            headers=self.get_headers(),
            name="doctor_view_schedule",
        )

    @task(8)
    def view_patient_details(self):
        """View patient details before consultation."""
        if not CONFIG.test_patient_id:
            return

        self.client.get(
            f"/api/v1/patients/{CONFIG.test_patient_id}",
            headers=self.get_headers(),
            name="doctor_view_patient",
        )

    @task(5)
    def view_patient_appointments_history(self):
        """View patient's appointment history."""
        if not CONFIG.test_patient_id:
            return

        self.client.get(
            "/api/v1/appointments/",
            params={
                "patient_id": CONFIG.test_patient_id,
                "limit": 50,
            },
            headers=self.get_headers(),
            name="doctor_patient_history",
        )

    @task(3)
    def view_upcoming_appointments(self):
        """View upcoming appointments for next week."""
        today = datetime.now(timezone.utc).date()
        next_week = today + timedelta(days=7)

        self.client.get(
            "/api/v1/appointments/",
            params={
                "doctor_id": self.doctor_id,
                "date_from": today.isoformat(),
                "date_to": next_week.isoformat(),
                "limit": 100,
            },
            headers=self.get_headers(),
            name="doctor_upcoming_appointments",
        )

    @task(2)
    def search_patient_for_consult(self):
        """Search for patient during consultation."""
        self.client.get(
            "/api/v1/patients/search",
            params={"q": fake.first_name(), "limit": 10},
            headers=self.get_headers(),
            name="doctor_search_patient",
        )

    # ========== ANALYTICS OPERATIONS (20% of traffic) ==========

    @task(8)
    def view_dashboard(self):
        """View analytics dashboard."""
        periods = ["today", "week", "month"]

        self.client.get(
            "/api/v1/analytics/dashboard",
            params={
                "period": random.choice(periods),
                "clinic_id": self.clinic_id,
            },
            headers=self.get_headers(),
            name="analytics_dashboard",
        )

    @task(4)
    def view_appointment_stats(self):
        """View appointment statistics."""
        today = datetime.now(timezone.utc).date()
        start_date = today - timedelta(days=random.choice([7, 14, 30, 90]))

        self.client.get(
            "/api/v1/analytics/appointments",
            params={
                "start_date": start_date.isoformat(),
                "end_date": today.isoformat(),
                "clinic_id": self.clinic_id,
            },
            headers=self.get_headers(),
            name="analytics_appointments",
        )

    @task(4)
    def view_revenue_stats(self):
        """View revenue statistics."""
        today = datetime.now(timezone.utc).date()
        start_date = today - timedelta(days=random.choice([7, 30, 90]))

        self.client.get(
            "/api/v1/analytics/revenue",
            params={
                "start_date": start_date.isoformat(),
                "end_date": today.isoformat(),
                "clinic_id": self.clinic_id,
            },
            headers=self.get_headers(),
            name="analytics_revenue",
        )

    @task(2)
    def view_doctor_utilization(self):
        """View doctor utilization metrics."""
        today = datetime.now(timezone.utc).date()

        self.client.get(
            "/api/v1/analytics/doctors/utilization",
            params={
                "start_date": (today - timedelta(days=7)).isoformat(),
                "end_date": today.isoformat(),
                "clinic_id": self.clinic_id,
            },
            headers=self.get_headers(),
            name="analytics_doctor_utilization",
        )

    @task(2)
    def view_patient_demographics(self):
        """View patient demographics."""
        today = datetime.now(timezone.utc).date()

        self.client.get(
            "/api/v1/analytics/patients/demographics",
            params={
                "start_date": (today - timedelta(days=30)).isoformat(),
                "end_date": today.isoformat(),
                "clinic_id": self.clinic_id,
            },
            headers=self.get_headers(),
            name="analytics_demographics",
        )

    # ========== MANAGEMENT OPERATIONS (10% of traffic) ==========

    @task(3)
    def list_doctors(self):
        """List doctors in clinic."""
        self.client.get(
            "/api/v1/doctors/",
            params={"clinic_id": self.clinic_id} if self.clinic_id else {},
            headers=self.get_headers(),
            name="management_list_doctors",
        )

    @task(2)
    def list_services(self):
        """List clinic services."""
        self.client.get(
            "/api/v1/services/",
            params={"clinic_id": self.clinic_id} if self.clinic_id else {},
            headers=self.get_headers(),
            name="management_list_services",
        )

    @task(2)
    def view_clinic_info(self):
        """View clinic information."""
        if self.clinic_id:
            self.client.get(
                f"/api/v1/clinics/{self.clinic_id}",
                headers=self.get_headers(),
                name="management_clinic_info",
            )

    @task(1)
    def list_invoices(self):
        """List recent invoices."""
        self.client.get(
            "/api/v1/invoices/",
            params={
                "clinic_id": self.clinic_id,
                "limit": 50,
            },
            headers=self.get_headers(),
            name="management_list_invoices",
        )

    @task(1)
    def list_payments(self):
        """List recent payments."""
        today = datetime.now(timezone.utc).date()

        self.client.get(
            "/api/v1/payments/",
            params={
                "start_date": (today - timedelta(days=7)).isoformat(),
                "end_date": today.isoformat(),
                "limit": 50,
            },
            headers=self.get_headers(),
            name="management_list_payments",
        )
