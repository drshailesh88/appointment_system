"""
Lab Integration Service.

Provides abstract base class for lab providers and implements
common functionality for lab result integration.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from app.services.lab_parser import (
    LabParserFactory,
    ParsedLabReport,
    ParsedLabResult,
)

logger = logging.getLogger(__name__)


@dataclass
class LabOrderRequest:
    """Lab order request."""

    patient_id: str
    patient_name: str
    tests: list[str]
    priority: str = "routine"
    clinical_notes: str | None = None
    diagnosis_codes: list[str] | None = None


@dataclass
class LabOrderResponse:
    """Lab order response from provider."""

    order_id: str
    status: str
    expected_completion: datetime | None
    tracking_url: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class LabResultNotification:
    """Notification of available lab results."""

    order_id: str
    status: str
    results_available: bool
    report_url: str | None = None
    report_format: str | None = None  # pdf, hl7, fhir


class LabProvider(ABC):
    """
    Abstract base class for lab providers.

    Implement this for different lab integrations:
    - Thyrocare API
    - Dr. Lal PathLabs API
    - Metropolis Healthcare API
    - SRL Diagnostics API
    - Local lab file-based integration
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize lab provider.

        Args:
            config: Provider-specific configuration
        """
        self.config = config
        self.provider_name = config.get("name", "Unknown Lab")

    @abstractmethod
    async def create_order(self, order: LabOrderRequest) -> LabOrderResponse:
        """
        Create a lab order.

        Args:
            order: Order request details

        Returns:
            Order response with tracking info
        """
        pass

    @abstractmethod
    async def get_order_status(self, order_id: str) -> str:
        """
        Get order status.

        Returns:
            Status: ordered, sample_collected, in_progress, completed, cancelled
        """
        pass

    @abstractmethod
    async def download_results(
        self, order_id: str
    ) -> tuple[bytes, str]:
        """
        Download lab results.

        Returns:
            Tuple of (content, format) where format is 'pdf', 'hl7', etc.
        """
        pass

    @abstractmethod
    async def parse_results(
        self, content: bytes, format: str
    ) -> ParsedLabReport:
        """
        Parse lab results.

        Args:
            content: Raw report content
            format: Report format (pdf, hl7, fhir)

        Returns:
            Parsed lab report
        """
        pass

    def is_available(self) -> bool:
        """Check if provider is available/configured."""
        return True


class FileBasedLabProvider(LabProvider):
    """
    File-based lab provider.

    Monitors a directory for lab reports (PDFs, HL7 files)
    and processes them as they arrive.
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize file-based provider.

        Config:
            watch_directory: Path to monitor for lab reports
            archive_directory: Path to move processed files
        """
        super().__init__(config)
        self.watch_dir = Path(config.get("watch_directory", "/var/lab_reports"))
        self.archive_dir = Path(config.get("archive_directory", "/var/lab_reports/archive"))

        # Create directories if they don't exist
        self.watch_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    async def create_order(self, order: LabOrderRequest) -> LabOrderResponse:
        """Create a lab order (saves order info to file)."""
        # For file-based, we just track the order locally
        order_id = f"FILE-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        # Save order details to file
        order_file = self.watch_dir / f"order_{order_id}.json"

        import json
        order_data = {
            "order_id": order_id,
            "patient_id": order.patient_id,
            "patient_name": order.patient_name,
            "tests": order.tests,
            "priority": order.priority,
            "clinical_notes": order.clinical_notes,
            "diagnosis_codes": order.diagnosis_codes,
            "created_at": datetime.now().isoformat(),
        }

        with open(order_file, 'w') as f:
            json.dump(order_data, f, indent=2)

        logger.info(f"Created file-based lab order: {order_id}")

        return LabOrderResponse(
            order_id=order_id,
            status="ordered",
            expected_completion=None,
            tracking_url=None,
            metadata={"order_file": str(order_file)},
        )

    async def get_order_status(self, order_id: str) -> str:
        """Get order status by checking for result files."""
        # Check if result file exists
        result_files = list(self.watch_dir.glob(f"*{order_id}*.pdf")) + \
                       list(self.watch_dir.glob(f"*{order_id}*.hl7"))

        if result_files:
            return "completed"

        # Check if archived
        archived_files = list(self.archive_dir.glob(f"*{order_id}*"))
        if archived_files:
            return "completed"

        return "ordered"

    async def download_results(self, order_id: str) -> tuple[bytes, str]:
        """Download results from file."""
        # Find result file
        result_files = (
            list(self.watch_dir.glob(f"*{order_id}*.pdf")) +
            list(self.watch_dir.glob(f"*{order_id}*.hl7")) +
            list(self.watch_dir.glob(f"*{order_id}*.txt"))
        )

        if not result_files:
            raise FileNotFoundError(f"No results found for order {order_id}")

        result_file = result_files[0]

        # Detect format
        if result_file.suffix == '.pdf':
            format = 'pdf'
        elif result_file.suffix == '.hl7':
            format = 'hl7'
        else:
            format = 'text'

        # Read content
        with open(result_file, 'rb') as f:
            content = f.read()

        logger.info(f"Downloaded results for {order_id} from {result_file}")

        return content, format

    async def parse_results(
        self, content: bytes, format: str
    ) -> ParsedLabReport:
        """Parse lab results using appropriate parser."""
        parser = LabParserFactory.create_parser(format)
        return parser.parse(content)

    def archive_report(self, filename: str):
        """Move processed report to archive."""
        source = self.watch_dir / filename
        dest = self.archive_dir / filename

        if source.exists():
            source.rename(dest)
            logger.info(f"Archived lab report: {filename}")


class ThyrocareLabProvider(LabProvider):
    """
    Thyrocare API integration.

    Note: This is a stub implementation. Actual Thyrocare API
    requires authentication and specific endpoint documentation.
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize Thyrocare provider.

        Config:
            api_key: Thyrocare API key
            api_url: API endpoint URL
            center_code: Thyrocare center code
        """
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.api_url = config.get("api_url", "https://api.thyrocare.com")
        self.center_code = config.get("center_code")

    async def create_order(self, order: LabOrderRequest) -> LabOrderResponse:
        """Create order via Thyrocare API."""
        # TODO: Implement actual API call
        logger.warning("Thyrocare API integration not yet implemented")
        raise NotImplementedError("Thyrocare API integration pending")

    async def get_order_status(self, order_id: str) -> str:
        """Get order status from Thyrocare."""
        # TODO: Implement actual API call
        raise NotImplementedError("Thyrocare API integration pending")

    async def download_results(self, order_id: str) -> tuple[bytes, str]:
        """Download results from Thyrocare."""
        # TODO: Implement actual API call
        raise NotImplementedError("Thyrocare API integration pending")

    async def parse_results(
        self, content: bytes, format: str
    ) -> ParsedLabReport:
        """Parse Thyrocare results."""
        parser = LabParserFactory.create_parser(format)
        return parser.parse(content)

    def is_available(self) -> bool:
        """Check if Thyrocare credentials are configured."""
        return bool(self.api_key and self.center_code)


class LabIntegrationService:
    """
    Main lab integration service.

    Manages multiple lab providers and routes requests.
    """

    def __init__(self):
        """Initialize lab integration service."""
        self.providers: dict[str, LabProvider] = {}
        self.default_provider: str | None = None

    def register_provider(
        self, name: str, provider: LabProvider, is_default: bool = False
    ):
        """
        Register a lab provider.

        Args:
            name: Provider identifier (e.g., 'thyrocare', 'file_based')
            provider: Provider instance
            is_default: Set as default provider
        """
        self.providers[name] = provider
        logger.info(f"Registered lab provider: {name}")

        if is_default or self.default_provider is None:
            self.default_provider = name
            logger.info(f"Set default lab provider: {name}")

    def get_provider(self, name: str | None = None) -> LabProvider:
        """
        Get a lab provider by name.

        Args:
            name: Provider name, or None for default

        Returns:
            LabProvider instance

        Raises:
            ValueError: If provider not found
        """
        provider_name = name or self.default_provider

        if provider_name not in self.providers:
            raise ValueError(f"Lab provider not found: {provider_name}")

        return self.providers[provider_name]

    async def create_order(
        self,
        order: LabOrderRequest,
        provider_name: str | None = None,
    ) -> LabOrderResponse:
        """Create a lab order."""
        provider = self.get_provider(provider_name)
        return await provider.create_order(order)

    async def get_order_status(
        self,
        order_id: str,
        provider_name: str | None = None,
    ) -> str:
        """Get order status."""
        provider = self.get_provider(provider_name)
        return await provider.get_order_status(order_id)

    async def fetch_and_parse_results(
        self,
        order_id: str,
        provider_name: str | None = None,
    ) -> ParsedLabReport:
        """
        Fetch and parse lab results.

        Args:
            order_id: Lab order ID
            provider_name: Provider to use (optional)

        Returns:
            Parsed lab report
        """
        provider = self.get_provider(provider_name)

        # Download results
        content, format = await provider.download_results(order_id)

        # Parse results
        report = await provider.parse_results(content, format)

        return report

    def list_providers(self) -> list[dict[str, Any]]:
        """List all registered providers."""
        return [
            {
                "name": name,
                "provider_name": provider.provider_name,
                "is_default": name == self.default_provider,
                "is_available": provider.is_available(),
            }
            for name, provider in self.providers.items()
        ]


# Global service instance
_lab_service: LabIntegrationService | None = None


def get_lab_integration_service() -> LabIntegrationService:
    """Get global lab integration service instance."""
    global _lab_service

    if _lab_service is None:
        _lab_service = LabIntegrationService()

        # Register default file-based provider
        file_provider = FileBasedLabProvider({
            "name": "File-Based Lab",
            "watch_directory": "/var/lab_reports",
            "archive_directory": "/var/lab_reports/archive",
        })
        _lab_service.register_provider("file_based", file_provider, is_default=True)

        logger.info("Lab integration service initialized")

    return _lab_service
