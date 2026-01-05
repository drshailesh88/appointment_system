"""
Search-Heavy Load Test.

Tests search-intensive operations:
- RAG semantic search
- Patient search (by name, phone)
- Appointment search
- Analytics queries

This simulates intensive search usage patterns.
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


class SearchHeavyUser(HttpUser):
    """User performing intensive search operations."""

    wait_time = between(0.5, 2)  # Faster for search-heavy
    access_token = None

    def on_start(self):
        """Login before starting."""
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

    @task(10)
    def rag_search(self):
        """RAG semantic search (most intensive)."""
        queries = [
            "diabetes patient visited last month",
            "hypertension follow-up needed",
            "echo procedure scheduled this week",
            "patient with chest pain symptoms",
            "emergency contact mobile number",
            "blood pressure medication prescribed",
            "ECG report pending",
            "patient age above 60 years",
            "consultation cancelled yesterday",
            "payment pending for last month",
            "female patients with cardiac issues",
            "follow-up appointments for next week",
            "patients from Mumbai area",
            "ultrasound reports from last quarter",
            "patients with allergies to penicillin",
        ]

        self.client.post(
            "/api/v1/search/rag",
            json={
                "query": random.choice(queries),
                "limit": 10,
            },
            headers=self.get_headers(),
            name="rag_search",
        )

    @task(8)
    def search_patients_by_name(self):
        """Search patients by name."""
        # Mix of single names and full names
        search_terms = [
            fake.first_name(),
            fake.last_name(),
            f"{fake.first_name()} {fake.last_name()}",
            fake.first_name()[:3],  # Partial search
        ]

        self.client.get(
            "/api/v1/patients/search",
            params={"q": random.choice(search_terms), "limit": 20},
            headers=self.get_headers(),
            name="search_patients_by_name",
        )

    @task(6)
    def search_patients_by_phone(self):
        """Search patients by phone number."""
        # Generate realistic Indian phone patterns
        phone_patterns = [
            f"9{random.randint(100000000, 999999999)}",  # Full number
            f"98{random.randint(10000000, 99999999)}",  # Partial
            f"+91 9{random.randint(100000000, 999999999)}",  # With country code
        ]

        self.client.get(
            "/api/v1/patients/search",
            params={"q": random.choice(phone_patterns)[:7], "limit": 20},
            headers=self.get_headers(),
            name="search_patients_by_phone",
        )

    @task(5)
    def search_appointments_by_date_range(self):
        """Search appointments by date range."""
        today = datetime.now(timezone.utc).date()

        # Different date ranges
        ranges = [
            (today, today + timedelta(days=1)),  # Today
            (today - timedelta(days=7), today),  # Last week
            (today, today + timedelta(days=7)),  # Next week
            (today - timedelta(days=30), today),  # Last month
        ]

        start_date, end_date = random.choice(ranges)

        params = {
            "date_from": start_date.isoformat(),
            "date_to": end_date.isoformat(),
            "limit": 100,
        }

        if CONFIG.test_doctor_id:
            params["doctor_id"] = CONFIG.test_doctor_id

        self.client.get(
            "/api/v1/appointments/",
            params=params,
            headers=self.get_headers(),
            name="search_appointments_by_date",
        )

    @task(4)
    def search_appointments_by_status(self):
        """Search appointments by status."""
        statuses = ["SCHEDULED", "COMPLETED", "CANCELLED", "CHECKED_IN", "IN_PROGRESS"]

        params = {
            "status_filter": random.choice(statuses),
            "limit": 50,
        }

        if CONFIG.test_clinic_id:
            # Would need clinic filtering in appointments endpoint
            pass

        self.client.get(
            "/api/v1/appointments/",
            params=params,
            headers=self.get_headers(),
            name="search_appointments_by_status",
        )

    @task(3)
    def search_appointments_for_patient(self):
        """Search all appointments for a specific patient."""
        if not CONFIG.test_patient_id:
            return

        self.client.get(
            "/api/v1/appointments/",
            params={
                "patient_id": CONFIG.test_patient_id,
                "limit": 100,
            },
            headers=self.get_headers(),
            name="search_appointments_for_patient",
        )

    @task(2)
    def list_patients_paginated(self):
        """List patients with pagination (simulating scrolling)."""
        skip = random.choice([0, 50, 100, 150, 200])

        params = {
            "skip": skip,
            "limit": 50,
        }

        if CONFIG.test_clinic_id:
            params["clinic_id"] = CONFIG.test_clinic_id

        self.client.get(
            "/api/v1/patients/",
            params=params,
            headers=self.get_headers(),
            name="list_patients_paginated",
        )

    @task(2)
    def get_patient_by_phone_direct(self):
        """Get patient by phone number (direct lookup)."""
        # Generate or use test phone
        test_phones = [
            "+919876543210",
            "+919123456789",
            "9876543210",
        ]

        phone = random.choice(test_phones)

        if CONFIG.test_clinic_id:
            self.client.get(
                f"/api/v1/patients/phone/{phone}",
                params={"clinic_id": CONFIG.test_clinic_id},
                headers=self.get_headers(),
                name="get_patient_by_phone_direct",
            )

    @task(1)
    def complex_analytics_query(self):
        """Complex analytics query."""
        today = datetime.now(timezone.utc).date()

        self.client.get(
            "/api/v1/analytics/dashboard",
            params={
                "period": "month",
                "clinic_id": CONFIG.test_clinic_id,
                "start_date": (today - timedelta(days=90)).isoformat(),
                "end_date": today.isoformat(),
            },
            headers=self.get_headers(),
            name="complex_analytics_query",
        )


class RAGOnlyUser(HttpUser):
    """User performing only RAG searches (extreme case)."""

    wait_time = between(0.2, 1)  # Very fast for stress testing
    access_token = None

    def on_start(self):
        """Login before starting."""
        response = self.client.post(
            "/api/v1/auth/login/json",
            json={
                "email": CONFIG.admin_email,
                "password": CONFIG.admin_password,
            },
        )

        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]

    def get_headers(self) -> dict:
        """Get authorization headers."""
        return {"Authorization": f"Bearer {self.access_token}"}

    @task
    def rag_search_only(self):
        """Continuous RAG search."""
        medical_queries = [
            "diabetes type 2 patients",
            "hypertension medication history",
            "cardiac echo reports",
            "blood pressure above 140",
            "cholesterol levels high",
            "ECG abnormal readings",
            "chest pain emergency",
            "follow-up needed urgently",
            "medication allergies",
            "surgical procedures done",
            "lab reports pending",
            "vaccination records",
            "elderly patients over 70",
            "pediatric consultations",
            "pregnancy checkups scheduled",
        ]

        self.client.post(
            "/api/v1/search/rag",
            json={
                "query": random.choice(medical_queries),
                "limit": 15,
            },
            headers=self.get_headers(),
            name="rag_search_extreme",
        )
