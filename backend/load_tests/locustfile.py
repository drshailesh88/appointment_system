"""
Main Locust load test file for DocAssist Practice Manager.

This file contains the primary user classes and test scenarios.
Run with: locust -f locustfile.py --host=http://localhost:8000
"""

import json
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

from faker import Faker
from locust import HttpUser, between, task

from config import CONFIG

fake = Faker("en_IN")  # Indian locale for realistic data


class AuthenticatedUser(HttpUser):
    """Base class for authenticated users."""

    abstract = True
    access_token: Optional[str] = None
    clinic_id: Optional[str] = None
    doctor_id: Optional[str] = None

    def on_start(self):
        """Login and get access token when user starts."""
        self.login()

    def login(self):
        """Authenticate and store access token."""
        response = self.client.post(
            "/api/v1/auth/login/json",
            json={
                "email": CONFIG.admin_email,
                "password": CONFIG.admin_password,
            },
            name="/api/v1/auth/login",
        )

        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]
            self.clinic_id = CONFIG.test_clinic_id
            self.doctor_id = CONFIG.test_doctor_id
        else:
            print(f"Login failed: {response.status_code} - {response.text}")

    def get_headers(self) -> dict:
        """Get authorization headers."""
        if not self.access_token:
            self.login()
        return {"Authorization": f"Bearer {self.access_token}"}


class ReceptionistUser(AuthenticatedUser):
    """
    Simulates receptionist workflow:
    - Searching for patients
    - Booking appointments
    - Checking in patients
    - Managing waitlist
    """

    wait_time = between(1, 3)

    @task(5)
    def search_patients(self):
        """Search for patients (most common operation)."""
        search_term = random.choice(
            [
                fake.first_name(),
                fake.phone_number()[:10],
                fake.last_name(),
            ]
        )

        self.client.get(
            "/api/v1/patients/search",
            params={"q": search_term, "limit": 20},
            headers=self.get_headers(),
            name="/api/v1/patients/search",
        )

    @task(3)
    def list_patients(self):
        """List patients for a clinic."""
        self.client.get(
            "/api/v1/patients/",
            params={"clinic_id": self.clinic_id, "limit": 50},
            headers=self.get_headers(),
            name="/api/v1/patients/list",
        )

    @task(4)
    def get_today_appointments(self):
        """Get today's appointments (frequently checked)."""
        self.client.get(
            "/api/v1/appointments/today",
            params={"doctor_id": self.doctor_id} if self.doctor_id else {},
            headers=self.get_headers(),
            name="/api/v1/appointments/today",
        )

    @task(2)
    def list_appointments(self):
        """List appointments with date range."""
        today = datetime.now(timezone.utc).date()
        params = {
            "date_from": today.isoformat(),
            "date_to": (today + timedelta(days=7)).isoformat(),
            "limit": 100,
        }

        if self.doctor_id:
            params["doctor_id"] = self.doctor_id

        self.client.get(
            "/api/v1/appointments/",
            params=params,
            headers=self.get_headers(),
            name="/api/v1/appointments/list",
        )

    @task(2)
    def check_slot_availability(self):
        """Check available slots for booking."""
        if not self.doctor_id:
            return

        tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).date()

        self.client.post(
            "/api/v1/appointments/slots/availability",
            json={
                "doctor_id": self.doctor_id,
                "date": tomorrow.isoformat(),
                "duration_minutes": 15,
            },
            headers=self.get_headers(),
            name="/api/v1/appointments/slots/availability",
        )

    @task(1)
    def create_appointment(self):
        """Book a new appointment."""
        if not self.doctor_id or not CONFIG.test_patient_id:
            return

        # Schedule for tomorrow at 10 AM
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_time = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        # Add random minutes to avoid conflicts
        scheduled_time += timedelta(minutes=random.randint(0, 120))

        appointment_data = {
            "patient_id": CONFIG.test_patient_id,
            "doctor_id": self.doctor_id,
            "scheduled_start": scheduled_time.isoformat(),
            "duration_minutes": 15,
            "appointment_type": random.choice(
                ["CONSULTATION", "FOLLOW_UP", "PROCEDURE"]
            ),
            "booking_source": "FRONT_DESK",
            "chief_complaint": fake.sentence(nb_words=6),
        }

        if CONFIG.test_service_id:
            appointment_data["service_id"] = CONFIG.test_service_id

        self.client.post(
            "/api/v1/appointments/",
            json=appointment_data,
            headers=self.get_headers(),
            name="/api/v1/appointments/create",
        )

    @task(1)
    def get_waitlist(self):
        """Get waitlist for a clinic."""
        self.client.get(
            "/api/v1/waitlist/",
            params={"clinic_id": self.clinic_id} if self.clinic_id else {},
            headers=self.get_headers(),
            name="/api/v1/waitlist/list",
        )


class DoctorUser(AuthenticatedUser):
    """
    Simulates doctor workflow:
    - Viewing daily schedule
    - Checking appointments
    - Viewing analytics
    """

    wait_time = between(2, 5)

    @task(5)
    def get_daily_schedule(self):
        """Get doctor's daily schedule (most frequent check)."""
        if not self.doctor_id:
            return

        today = datetime.now(timezone.utc).date()

        self.client.get(
            f"/api/v1/appointments/doctor/{self.doctor_id}/schedule",
            params={"schedule_date": today.isoformat()},
            headers=self.get_headers(),
            name="/api/v1/appointments/doctor/schedule",
        )

    @task(3)
    def get_today_appointments(self):
        """Get today's appointments."""
        self.client.get(
            "/api/v1/appointments/today",
            params={"doctor_id": self.doctor_id} if self.doctor_id else {},
            headers=self.get_headers(),
            name="/api/v1/appointments/today",
        )

    @task(2)
    def view_patient_details(self):
        """View patient details."""
        if not CONFIG.test_patient_id:
            return

        self.client.get(
            f"/api/v1/patients/{CONFIG.test_patient_id}",
            headers=self.get_headers(),
            name="/api/v1/patients/get",
        )

    @task(1)
    def get_analytics(self):
        """View analytics dashboard."""
        self.client.get(
            "/api/v1/analytics/dashboard",
            params={
                "period": "week",
                "clinic_id": self.clinic_id,
            },
            headers=self.get_headers(),
            name="/api/v1/analytics/dashboard",
        )


class AnalyticsUser(AuthenticatedUser):
    """
    Simulates analytics-heavy usage:
    - Dashboard queries
    - Report generation
    - Statistics retrieval
    """

    wait_time = between(3, 8)

    @task(3)
    def get_dashboard_summary(self):
        """Get dashboard summary."""
        periods = ["today", "week", "month"]

        self.client.get(
            "/api/v1/analytics/dashboard",
            params={
                "period": random.choice(periods),
                "clinic_id": self.clinic_id,
            },
            headers=self.get_headers(),
            name="/api/v1/analytics/dashboard",
        )

    @task(2)
    def get_appointment_stats(self):
        """Get appointment statistics."""
        today = datetime.now(timezone.utc).date()

        self.client.get(
            "/api/v1/analytics/appointments",
            params={
                "start_date": (today - timedelta(days=30)).isoformat(),
                "end_date": today.isoformat(),
                "clinic_id": self.clinic_id,
            },
            headers=self.get_headers(),
            name="/api/v1/analytics/appointments",
        )

    @task(2)
    def get_revenue_stats(self):
        """Get revenue statistics."""
        today = datetime.now(timezone.utc).date()

        self.client.get(
            "/api/v1/analytics/revenue",
            params={
                "start_date": (today - timedelta(days=30)).isoformat(),
                "end_date": today.isoformat(),
                "clinic_id": self.clinic_id,
            },
            headers=self.get_headers(),
            name="/api/v1/analytics/revenue",
        )

    @task(1)
    def get_doctor_utilization(self):
        """Get doctor utilization metrics."""
        today = datetime.now(timezone.utc).date()

        self.client.get(
            "/api/v1/analytics/doctors/utilization",
            params={
                "start_date": (today - timedelta(days=7)).isoformat(),
                "end_date": today.isoformat(),
                "clinic_id": self.clinic_id,
            },
            headers=self.get_headers(),
            name="/api/v1/analytics/doctors/utilization",
        )


class SearchHeavyUser(AuthenticatedUser):
    """
    Simulates search-intensive operations:
    - RAG search
    - Patient search
    - Appointment search
    """

    wait_time = between(1, 2)

    @task(5)
    def rag_search_patients(self):
        """Perform RAG search (most intensive)."""
        queries = [
            "diabetes patient visited last month",
            "hypertension follow-up needed",
            "echo procedure scheduled",
            "patient with chest pain",
            "emergency contact mobile number",
        ]

        self.client.post(
            "/api/v1/search/rag",
            json={
                "query": random.choice(queries),
                "limit": 10,
            },
            headers=self.get_headers(),
            name="/api/v1/search/rag",
        )

    @task(4)
    def search_patients(self):
        """Basic patient search."""
        search_term = random.choice(
            [
                fake.first_name(),
                fake.last_name(),
                fake.phone_number()[:10],
            ]
        )

        self.client.get(
            "/api/v1/patients/search",
            params={"q": search_term, "limit": 20},
            headers=self.get_headers(),
            name="/api/v1/patients/search",
        )

    @task(2)
    def search_appointments(self):
        """Search appointments by patient."""
        if not CONFIG.test_patient_id:
            return

        self.client.get(
            "/api/v1/appointments/",
            params={
                "patient_id": CONFIG.test_patient_id,
                "limit": 50,
            },
            headers=self.get_headers(),
            name="/api/v1/appointments/search",
        )


class MixedLoadUser(AuthenticatedUser):
    """
    Simulates realistic mixed traffic pattern.
    This represents typical clinic usage with varied operations.
    """

    wait_time = between(1, 4)

    # Reception tasks (40% of traffic)
    @task(10)
    def search_patients(self):
        """Search for patients."""
        search_term = random.choice([fake.first_name(), fake.phone_number()[:10]])

        self.client.get(
            "/api/v1/patients/search",
            params={"q": search_term, "limit": 20},
            headers=self.get_headers(),
            name="/api/v1/patients/search",
        )

    @task(8)
    def get_today_appointments(self):
        """Get today's appointments."""
        self.client.get(
            "/api/v1/appointments/today",
            headers=self.get_headers(),
            name="/api/v1/appointments/today",
        )

    @task(5)
    def check_availability(self):
        """Check slot availability."""
        if not self.doctor_id:
            return

        tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).date()

        self.client.post(
            "/api/v1/appointments/slots/availability",
            json={
                "doctor_id": self.doctor_id,
                "date": tomorrow.isoformat(),
            },
            headers=self.get_headers(),
            name="/api/v1/appointments/slots/availability",
        )

    # Doctor tasks (30% of traffic)
    @task(7)
    def view_schedule(self):
        """View doctor schedule."""
        if not self.doctor_id:
            return

        self.client.get(
            f"/api/v1/appointments/doctor/{self.doctor_id}/schedule",
            headers=self.get_headers(),
            name="/api/v1/appointments/doctor/schedule",
        )

    @task(5)
    def view_patient(self):
        """View patient details."""
        if not CONFIG.test_patient_id:
            return

        self.client.get(
            f"/api/v1/patients/{CONFIG.test_patient_id}",
            headers=self.get_headers(),
            name="/api/v1/patients/get",
        )

    # Analytics tasks (20% of traffic)
    @task(4)
    def view_dashboard(self):
        """View analytics dashboard."""
        self.client.get(
            "/api/v1/analytics/dashboard",
            params={"period": "week", "clinic_id": self.clinic_id},
            headers=self.get_headers(),
            name="/api/v1/analytics/dashboard",
        )

    # Booking tasks (10% of traffic)
    @task(2)
    def book_appointment(self):
        """Book new appointment."""
        if not self.doctor_id or not CONFIG.test_patient_id:
            return

        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled_time = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
        scheduled_time += timedelta(minutes=random.randint(0, 120))

        self.client.post(
            "/api/v1/appointments/",
            json={
                "patient_id": CONFIG.test_patient_id,
                "doctor_id": self.doctor_id,
                "scheduled_start": scheduled_time.isoformat(),
                "duration_minutes": 15,
                "appointment_type": "CONSULTATION",
                "booking_source": "FRONT_DESK",
                "chief_complaint": fake.sentence(nb_words=6),
            },
            headers=self.get_headers(),
            name="/api/v1/appointments/create",
        )
