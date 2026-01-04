"""
Insurance Verification Service.

Provides insurance eligibility verification through various providers.
Supports Indian insurance providers (IRDA regulated) and TPAs.

Common Indian Insurance Providers:
- Star Health and Allied Insurance
- ICICI Lombard
- Max Bupa Health Insurance
- HDFC ERGO
- Care Health Insurance
- Bajaj Allianz
- Religare Health Insurance
- Aditya Birla Health Insurance

Common TPAs (Third-Party Administrators):
- Medi Assist
- Paramount Health Services
- Vidal Health
- MD India Healthcare Services
- Raksha Health Insurance TPA
- Good Health TPA Services
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Optional
from uuid import UUID

import httpx

logger = logging.getLogger(__name__)


class VerificationStatus(str, Enum):
    """Verification status."""

    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    EXPIRED = "expired"


@dataclass
class EligibilityResult:
    """Insurance eligibility verification result."""

    status: VerificationStatus
    is_eligible: bool | None = None
    eligibility_start_date: date | None = None
    eligibility_end_date: date | None = None
    coverage_details: dict | None = None
    copay_info: dict | None = None
    deductible_info: dict | None = None
    benefits: dict | None = None
    limitations: str | None = None
    error_message: str | None = None
    provider_response: dict | None = None
    expires_at: datetime | None = None


class InsuranceVerificationProvider(ABC):
    """
    Abstract base class for insurance verification providers.

    Implementations should connect to specific insurance provider APIs
    (e.g., Availity, Change Healthcare, or Indian TPA APIs).
    """

    @abstractmethod
    async def verify_eligibility(
        self,
        policy_number: str,
        provider_name: str,
        patient_dob: date,
        service_date: date | None = None,
        procedure_codes: list[str] | None = None,
        additional_info: dict | None = None,
    ) -> EligibilityResult:
        """
        Verify patient insurance eligibility.

        Args:
            policy_number: Insurance policy number
            provider_name: Insurance provider name
            patient_dob: Patient date of birth (for verification)
            service_date: Date of service (defaults to today)
            procedure_codes: List of procedure codes to check
            additional_info: Additional provider-specific info (group number, TPA ID, etc.)

        Returns:
            EligibilityResult with verification details
        """
        pass

    @abstractmethod
    async def check_coverage(
        self,
        policy_number: str,
        provider_name: str,
        procedure_codes: list[str],
        additional_info: dict | None = None,
    ) -> dict:
        """
        Check coverage for specific procedures.

        Args:
            policy_number: Insurance policy number
            provider_name: Insurance provider name
            procedure_codes: List of procedure codes
            additional_info: Additional info

        Returns:
            Dictionary with coverage details per procedure
        """
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if provider is properly configured."""
        pass


class MockInsuranceProvider(InsuranceVerificationProvider):
    """
    Mock insurance verification provider for testing.

    Simulates insurance verification responses without calling real APIs.
    Useful for development and testing.
    """

    def __init__(self, success_rate: float = 0.9):
        """
        Initialize mock provider.

        Args:
            success_rate: Probability of successful verification (0.0 to 1.0)
        """
        self.success_rate = success_rate

    async def verify_eligibility(
        self,
        policy_number: str,
        provider_name: str,
        patient_dob: date,
        service_date: date | None = None,
        procedure_codes: list[str] | None = None,
        additional_info: dict | None = None,
    ) -> EligibilityResult:
        """Mock eligibility verification."""
        import random

        # Simulate API delay
        import asyncio
        await asyncio.sleep(0.5)

        # Simulate success/failure based on success_rate
        if random.random() > self.success_rate:
            return EligibilityResult(
                status=VerificationStatus.FAILED,
                is_eligible=None,
                error_message="Mock verification failed: Provider temporarily unavailable",
            )

        # Mock successful verification
        service_dt = service_date or date.today()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=48)

        # Generate mock coverage details
        coverage_details = {
            "plan_name": f"{provider_name} Premium Health Plan",
            "coverage_level": "individual",
            "network_status": "in-network",
            "covered_services": [
                "consultation",
                "diagnostic_tests",
                "preventive_care",
                "specialist_visits",
            ],
            "excluded_services": ["cosmetic_surgery", "experimental_treatments"],
            "max_coverage_amount": 500000.0,  # 5 lakh
            "remaining_coverage": 475000.0,
        }

        # Mock copay info
        copay_info = {
            "amount": 500.0,
            "percentage": None,
            "description": "Fixed copay per consultation",
            "applies_to": "consultation",
        }

        # Mock deductible info
        deductible_info = {
            "total_deductible": 25000.0,
            "remaining_deductible": 15000.0,
            "met_amount": 10000.0,
            "family_deductible": None,
            "reset_date": date(service_dt.year + 1, 4, 1),  # Indian fiscal year
        }

        # Mock benefits
        benefits = {}
        if procedure_codes:
            for code in procedure_codes:
                benefits[code] = {
                    "covered": True,
                    "copay": 500.0,
                    "requires_preauth": False,
                    "notes": "Covered under plan",
                }

        return EligibilityResult(
            status=VerificationStatus.SUCCESS,
            is_eligible=True,
            eligibility_start_date=date(service_dt.year, 1, 1),
            eligibility_end_date=date(service_dt.year, 12, 31),
            coverage_details=coverage_details,
            copay_info=copay_info,
            deductible_info=deductible_info,
            benefits=benefits,
            limitations="Pre-authorization required for hospitalization and surgery",
            provider_response={
                "mock": True,
                "provider": provider_name,
                "policy": policy_number,
                "verified_at": datetime.now(timezone.utc).isoformat(),
            },
            expires_at=expires_at,
        )

    async def check_coverage(
        self,
        policy_number: str,
        provider_name: str,
        procedure_codes: list[str],
        additional_info: dict | None = None,
    ) -> dict:
        """Mock coverage check."""
        result = {}
        for code in procedure_codes:
            result[code] = {
                "covered": True,
                "copay_amount": 500.0,
                "requires_preauth": code.startswith("SUR"),  # Surgery codes
                "coverage_percentage": 80.0,
                "notes": f"Coverage for {code}",
            }
        return result

    def is_configured(self) -> bool:
        """Mock provider is always configured."""
        return True


class RealInsuranceProvider(InsuranceVerificationProvider):
    """
    Real insurance verification provider.

    Placeholder for integration with actual insurance verification APIs:
    - Availity (US)
    - Change Healthcare (US)
    - Indian TPA APIs (Medi Assist, Paramount, etc.)
    - IRDA registered insurance companies

    To implement:
    1. Register with insurance provider/TPA
    2. Obtain API credentials
    3. Implement authentication
    4. Map request/response to standard format
    """

    def __init__(
        self,
        api_url: str,
        api_key: str,
        api_secret: str | None = None,
        provider_type: str = "generic",
    ):
        """
        Initialize real insurance provider.

        Args:
            api_url: Base URL for insurance verification API
            api_key: API key/client ID
            api_secret: API secret/client secret (optional)
            provider_type: Type of provider (availity, change_healthcare, tpa, etc.)
        """
        self.api_url = api_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.provider_type = provider_type
        self._client: Optional[httpx.AsyncClient] = None

    def is_configured(self) -> bool:
        """Check if provider is configured."""
        return bool(self.api_url and self.api_key)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            self._client = httpx.AsyncClient(
                base_url=self.api_url,
                headers=headers,
                timeout=30.0,
            )
        return self._client

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def verify_eligibility(
        self,
        policy_number: str,
        provider_name: str,
        patient_dob: date,
        service_date: date | None = None,
        procedure_codes: list[str] | None = None,
        additional_info: dict | None = None,
    ) -> EligibilityResult:
        """
        Verify eligibility using real API.

        This is a placeholder implementation. Actual implementation should:
        1. Format request according to provider API spec
        2. Handle authentication
        3. Send eligibility request
        4. Parse response
        5. Map to standardized EligibilityResult
        """
        if not self.is_configured():
            return EligibilityResult(
                status=VerificationStatus.FAILED,
                error_message="Insurance provider not configured",
            )

        try:
            client = await self._get_client()

            # Example request format (adapt to actual provider API)
            request_payload = {
                "policy_number": policy_number,
                "provider": provider_name,
                "date_of_birth": patient_dob.isoformat(),
                "service_date": (service_date or date.today()).isoformat(),
                "procedure_codes": procedure_codes or [],
                **( additional_info or {}),
            }

            # Make API call
            response = await client.post(
                "/eligibility/verify",
                json=request_payload,
            )

            if response.status_code == 200:
                data = response.json()

                # Parse response (adapt to actual API format)
                return EligibilityResult(
                    status=VerificationStatus.SUCCESS,
                    is_eligible=data.get("eligible", False),
                    eligibility_start_date=(
                        date.fromisoformat(data["coverage_start"])
                        if "coverage_start" in data
                        else None
                    ),
                    eligibility_end_date=(
                        date.fromisoformat(data["coverage_end"])
                        if "coverage_end" in data
                        else None
                    ),
                    coverage_details=data.get("coverage"),
                    copay_info=data.get("copay"),
                    deductible_info=data.get("deductible"),
                    benefits=data.get("benefits"),
                    limitations=data.get("limitations"),
                    provider_response=data,
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
                )
            else:
                return EligibilityResult(
                    status=VerificationStatus.FAILED,
                    error_message=f"API error: {response.status_code} - {response.text}",
                )

        except Exception as e:
            logger.error(f"Insurance verification error: {e}")
            return EligibilityResult(
                status=VerificationStatus.FAILED,
                error_message=f"Verification failed: {str(e)}",
            )

    async def check_coverage(
        self,
        policy_number: str,
        provider_name: str,
        procedure_codes: list[str],
        additional_info: dict | None = None,
    ) -> dict:
        """
        Check coverage for procedures.

        Placeholder implementation - adapt to actual provider API.
        """
        if not self.is_configured():
            return {}

        try:
            client = await self._get_client()

            request_payload = {
                "policy_number": policy_number,
                "provider": provider_name,
                "procedure_codes": procedure_codes,
                **(additional_info or {}),
            }

            response = await client.post(
                "/coverage/check",
                json=request_payload,
            )

            if response.status_code == 200:
                return response.json()
            return {}

        except Exception as e:
            logger.error(f"Coverage check error: {e}")
            return {}


class InsuranceVerificationService:
    """
    Main insurance verification service.

    Manages multiple insurance providers and handles caching.
    """

    def __init__(self, provider: InsuranceVerificationProvider | None = None):
        """
        Initialize verification service.

        Args:
            provider: Insurance provider implementation (defaults to mock)
        """
        self.provider = provider or MockInsuranceProvider()

    async def verify_eligibility(
        self,
        policy_number: str,
        provider_name: str,
        patient_dob: date,
        service_date: date | None = None,
        procedure_codes: list[str] | None = None,
        additional_info: dict | None = None,
    ) -> EligibilityResult:
        """
        Verify patient eligibility.

        Delegates to configured provider implementation.
        """
        return await self.provider.verify_eligibility(
            policy_number=policy_number,
            provider_name=provider_name,
            patient_dob=patient_dob,
            service_date=service_date,
            procedure_codes=procedure_codes,
            additional_info=additional_info,
        )

    async def check_coverage(
        self,
        policy_number: str,
        provider_name: str,
        procedure_codes: list[str],
        additional_info: dict | None = None,
    ) -> dict:
        """Check coverage for procedures."""
        return await self.provider.check_coverage(
            policy_number=policy_number,
            provider_name=provider_name,
            procedure_codes=procedure_codes,
            additional_info=additional_info,
        )

    def is_configured(self) -> bool:
        """Check if service is configured."""
        return self.provider.is_configured()

    async def close(self):
        """Close service and cleanup resources."""
        if hasattr(self.provider, "close"):
            await self.provider.close()


# Singleton instance
_insurance_service: Optional[InsuranceVerificationService] = None


def get_insurance_service() -> InsuranceVerificationService:
    """Get insurance verification service singleton."""
    global _insurance_service
    if _insurance_service is None:
        # Default to mock provider
        # In production, configure with real provider based on settings
        _insurance_service = InsuranceVerificationService(
            provider=MockInsuranceProvider()
        )
    return _insurance_service


def configure_insurance_service(provider: InsuranceVerificationProvider):
    """
    Configure insurance service with specific provider.

    Args:
        provider: Insurance provider implementation
    """
    global _insurance_service
    _insurance_service = InsuranceVerificationService(provider=provider)


# Indian Insurance Provider List
INDIAN_INSURANCE_PROVIDERS = [
    {
        "code": "star_health",
        "name": "Star Health and Allied Insurance",
        "country": "IN",
        "supports_verification": False,
        "supports_claims": False,
        "tpa_required": True,
    },
    {
        "code": "icici_lombard",
        "name": "ICICI Lombard General Insurance",
        "country": "IN",
        "supports_verification": False,
        "supports_claims": False,
        "tpa_required": True,
    },
    {
        "code": "max_bupa",
        "name": "Niva Bupa Health Insurance (formerly Max Bupa)",
        "country": "IN",
        "supports_verification": False,
        "supports_claims": False,
        "tpa_required": True,
    },
    {
        "code": "hdfc_ergo",
        "name": "HDFC ERGO Health Insurance",
        "country": "IN",
        "supports_verification": False,
        "supports_claims": False,
        "tpa_required": True,
    },
    {
        "code": "care_health",
        "name": "Care Health Insurance (formerly Religare)",
        "country": "IN",
        "supports_verification": False,
        "supports_claims": False,
        "tpa_required": True,
    },
    {
        "code": "bajaj_allianz",
        "name": "Bajaj Allianz General Insurance",
        "country": "IN",
        "supports_verification": False,
        "supports_claims": False,
        "tpa_required": True,
    },
    {
        "code": "aditya_birla",
        "name": "Aditya Birla Health Insurance",
        "country": "IN",
        "supports_verification": False,
        "supports_claims": False,
        "tpa_required": True,
    },
]

# Common Indian TPAs
INDIAN_TPAS = [
    {
        "code": "medi_assist",
        "name": "Medi Assist Insurance TPA",
        "country": "IN",
    },
    {
        "code": "paramount_health",
        "name": "Paramount Health Services & Insurance TPA",
        "country": "IN",
    },
    {
        "code": "vidal_health",
        "name": "Vidal Health Insurance TPA",
        "country": "IN",
    },
    {
        "code": "md_india",
        "name": "MD India Healthcare Services TPA",
        "country": "IN",
    },
    {
        "code": "raksha_tpa",
        "name": "Raksha Health Insurance TPA",
        "country": "IN",
    },
    {
        "code": "good_health",
        "name": "Good Health TPA Services",
        "country": "IN",
    },
]
