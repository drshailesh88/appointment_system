"""
Appointment Booking Flow Load Test.

Tests the complete booking workflow:
1. Search for patient
2. Check slot availability
3. Book appointment
4. Verify booking
"""

import random
from datetime import datetime, timedelta, timezone

from faker import Faker
from locust import HttpUser, SequentialTaskSet, between, task

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import CONFIG

fake = Faker("en_IN")


class BookingFlowTaskSet(SequentialTaskSet):
    """Sequential booking flow tasks."""

    patient_id = None
    doctor_id = None
    appointment_id = None

    @task
    def step_1_search_patient(self):
        """Step 1: Search for a patient."""
        search_term = fake.first_name()

        response = self.client.get(
            "/api/v1/patients/search",
            params={"q": search_term, "limit": 20},
            headers=self.user.get_headers(),
            name="1_search_patient",
        )

        if response.status_code == 200:
            patients = response.json()
            if patients:
                self.patient_id = patients[0]["id"]
            else:
                # Use configured test patient
                self.patient_id = CONFIG.test_patient_id

            self.doctor_id = CONFIG.test_doctor_id

    @task
    def step_2_check_availability(self):
        """Step 2: Check slot availability."""
        if not self.doctor_id:
            return

        tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).date()

        response = self.client.post(
            "/api/v1/appointments/slots/availability",
            json={
                "doctor_id": self.doctor_id,
                "date": tomorrow.isoformat(),
                "duration_minutes": 15,
            },
            headers=self.user.get_headers(),
            name="2_check_availability",
        )

        if response.status_code == 200:
            data = response.json()
            # Find first available slot
            available_slots = [slot for slot in data.get("slots", []) if slot["is_available"]]
            if available_slots:
                # Store slot time for booking
                self.slot_time = available_slots[0]["start_time"]

    @task
    def step_3_book_appointment(self):
        """Step 3: Book the appointment."""
        if not self.patient_id or not self.doctor_id:
            return

        # Use found slot or generate a random time
        if hasattr(self, "slot_time"):
            scheduled_time = self.slot_time
        else:
            tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
            scheduled_time = tomorrow.replace(
                hour=10, minute=random.randint(0, 59), second=0, microsecond=0
            ).isoformat()

        appointment_data = {
            "patient_id": self.patient_id,
            "doctor_id": self.doctor_id,
            "scheduled_start": scheduled_time,
            "duration_minutes": 15,
            "appointment_type": "CONSULTATION",
            "booking_source": "FRONT_DESK",
            "chief_complaint": fake.sentence(nb_words=6),
        }

        if CONFIG.test_service_id:
            appointment_data["service_id"] = CONFIG.test_service_id

        response = self.client.post(
            "/api/v1/appointments/",
            json=appointment_data,
            headers=self.user.get_headers(),
            name="3_book_appointment",
        )

        if response.status_code == 201:
            data = response.json()
            self.appointment_id = data["id"]

    @task
    def step_4_verify_booking(self):
        """Step 4: Verify the booking."""
        if not self.appointment_id:
            return

        self.client.get(
            f"/api/v1/appointments/{self.appointment_id}",
            headers=self.user.get_headers(),
            name="4_verify_booking",
        )

    @task
    def step_5_view_today_appointments(self):
        """Step 5: View today's appointments to see the new booking."""
        self.client.get(
            "/api/v1/appointments/today",
            params={"doctor_id": self.doctor_id} if self.doctor_id else {},
            headers=self.user.get_headers(),
            name="5_view_today_appointments",
        )


class BookingFlowUser(HttpUser):
    """User simulating complete booking flow."""

    wait_time = between(1, 3)
    tasks = [BookingFlowTaskSet]
    access_token = None

    def on_start(self):
        """Login before starting tasks."""
        self.login()

    def login(self):
        """Authenticate and store access token."""
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
