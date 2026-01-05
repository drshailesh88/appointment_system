"""
Load test configuration.

Environment-based settings for load testing different environments.
"""

import os
from dataclasses import dataclass
from typing import Dict


@dataclass
class LoadTestConfig:
    """Load test configuration."""

    host: str
    admin_email: str
    admin_password: str
    test_clinic_id: str
    test_doctor_id: str
    test_patient_id: str
    test_service_id: str

    # Performance targets
    target_response_time_ms: int = 200  # p95
    target_rps: int = 500
    target_concurrent_users: int = 1000
    target_error_rate: float = 0.001  # 0.1%

    # Test duration
    spawn_rate: int = 10  # users per second
    run_time: str = "5m"

    @property
    def base_url(self) -> str:
        """Get base URL."""
        return f"{self.host}/api/v1"


def get_config(environment: str = "dev") -> LoadTestConfig:
    """Get configuration for specific environment."""
    configs: Dict[str, LoadTestConfig] = {
        "dev": LoadTestConfig(
            host=os.getenv("DEV_HOST", "http://localhost:8000"),
            admin_email=os.getenv("DEV_ADMIN_EMAIL", "admin@clinic.com"),
            admin_password=os.getenv("DEV_ADMIN_PASSWORD", "admin123"),
            test_clinic_id=os.getenv("DEV_CLINIC_ID", ""),
            test_doctor_id=os.getenv("DEV_DOCTOR_ID", ""),
            test_patient_id=os.getenv("DEV_PATIENT_ID", ""),
            test_service_id=os.getenv("DEV_SERVICE_ID", ""),
        ),
        "staging": LoadTestConfig(
            host=os.getenv("STAGING_HOST", "https://staging.docassist.com"),
            admin_email=os.getenv("STAGING_ADMIN_EMAIL", ""),
            admin_password=os.getenv("STAGING_ADMIN_PASSWORD", ""),
            test_clinic_id=os.getenv("STAGING_CLINIC_ID", ""),
            test_doctor_id=os.getenv("STAGING_DOCTOR_ID", ""),
            test_patient_id=os.getenv("STAGING_PATIENT_ID", ""),
            test_service_id=os.getenv("STAGING_SERVICE_ID", ""),
            target_response_time_ms=200,
            target_rps=500,
            target_concurrent_users=1000,
        ),
        "prod": LoadTestConfig(
            host=os.getenv("PROD_HOST", "https://api.docassist.com"),
            admin_email=os.getenv("PROD_ADMIN_EMAIL", ""),
            admin_password=os.getenv("PROD_ADMIN_PASSWORD", ""),
            test_clinic_id=os.getenv("PROD_CLINIC_ID", ""),
            test_doctor_id=os.getenv("PROD_DOCTOR_ID", ""),
            test_patient_id=os.getenv("PROD_PATIENT_ID", ""),
            test_service_id=os.getenv("PROD_SERVICE_ID", ""),
            target_response_time_ms=200,
            target_rps=1000,
            target_concurrent_users=2000,
            spawn_rate=20,
        ),
    }

    return configs.get(environment, configs["dev"])


# Global config instance
CONFIG = get_config(os.getenv("TEST_ENV", "dev"))
