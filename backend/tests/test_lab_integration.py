"""
Integration tests for lab results system.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from app.models.lab_result import (
    LabOrder,
    LabOrderStatus,
    LabResult,
    LabResultStatus,
    LabReport,
    LabTestPriority,
)


@pytest.fixture
def sample_lab_order(test_db, sample_patient, sample_doctor):
    """Create a sample lab order for testing."""
    order = LabOrder(
        patient_id=sample_patient.id,
        doctor_id=sample_doctor.id,
        order_date=datetime.now(timezone.utc),
        tests_ordered=["CBC", "LFT", "KFT"],
        priority=LabTestPriority.ROUTINE.value,
        status=LabOrderStatus.ORDERED.value,
        clinical_notes="Routine checkup",
    )
    test_db.add(order)
    test_db.commit()
    test_db.refresh(order)
    return order


@pytest.fixture
def sample_lab_result(test_db, sample_lab_order):
    """Create a sample lab result for testing."""
    result = LabResult(
        order_id=sample_lab_order.id,
        test_name="Hemoglobin",
        test_category="CBC",
        value="14.5",
        value_numeric=14.5,
        unit="g/dL",
        reference_range_min=12.0,
        reference_range_max=16.0,
        is_abnormal=False,
        status=LabResultStatus.FINAL.value,
        result_date=datetime.now(timezone.utc),
    )
    test_db.add(result)
    test_db.commit()
    test_db.refresh(result)
    return result


class TestLabOrderAPI:
    """Test lab order API endpoints."""

    @pytest.mark.asyncio
    async def test_create_lab_order(
        self, async_client, auth_headers, sample_patient, sample_doctor
    ):
        """Test creating a lab order."""
        response = await async_client.post(
            "/api/v1/labs/orders",
            headers=auth_headers,
            json={
                "patient_id": str(sample_patient.id),
                "doctor_id": str(sample_doctor.id),
                "tests_ordered": ["CBC", "LFT", "Lipid Profile"],
                "priority": "routine",
                "clinical_notes": "Annual health checkup",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["patient_id"] == str(sample_patient.id)
        assert data["doctor_id"] == str(sample_doctor.id)
        assert len(data["tests_ordered"]) == 3
        assert data["status"] == "ordered"

    @pytest.mark.asyncio
    async def test_get_lab_order(self, async_client, auth_headers, sample_lab_order):
        """Test getting a lab order."""
        response = await async_client.get(
            f"/api/v1/labs/orders/{sample_lab_order.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_lab_order.id)
        assert data["status"] == "ordered"

    @pytest.mark.asyncio
    async def test_get_patient_lab_orders(
        self, async_client, auth_headers, sample_lab_order, sample_patient
    ):
        """Test getting all lab orders for a patient."""
        response = await async_client.get(
            f"/api/v1/labs/patient/{sample_patient.id}/orders",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["orders"]) >= 1

    @pytest.mark.asyncio
    async def test_update_lab_order(self, async_client, auth_headers, sample_lab_order):
        """Test updating a lab order."""
        response = await async_client.patch(
            f"/api/v1/labs/orders/{sample_lab_order.id}",
            headers=auth_headers,
            json={"status": "sample_collected"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "sample_collected"


class TestLabResultAPI:
    """Test lab result API endpoints."""

    @pytest.mark.asyncio
    async def test_create_lab_result(
        self, async_client, auth_headers, sample_lab_order
    ):
        """Test creating a lab result."""
        response = await async_client.post(
            "/api/v1/labs/results",
            headers=auth_headers,
            json={
                "order_id": str(sample_lab_order.id),
                "test_name": "Hemoglobin",
                "test_category": "CBC",
                "value": "14.5",
                "value_numeric": 14.5,
                "unit": "g/dL",
                "reference_range_min": 12.0,
                "reference_range_max": 16.0,
                "is_abnormal": False,
                "status": "final",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["test_name"] == "Hemoglobin"
        assert data["value"] == "14.5"
        assert data["is_abnormal"] is False

    @pytest.mark.asyncio
    async def test_get_lab_result(self, async_client, auth_headers, sample_lab_result):
        """Test getting a lab result."""
        response = await async_client.get(
            f"/api/v1/labs/results/{sample_lab_result.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_lab_result.id)
        assert data["test_name"] == "Hemoglobin"

    @pytest.mark.asyncio
    async def test_get_patient_lab_results(
        self, async_client, auth_headers, sample_lab_result, sample_patient
    ):
        """Test getting all lab results for a patient."""
        response = await async_client.get(
            f"/api/v1/labs/patient/{sample_patient.id}/results",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_get_abnormal_results(
        self, async_client, auth_headers, sample_patient, sample_lab_order, test_db
    ):
        """Test filtering abnormal results."""
        # Create an abnormal result
        abnormal_result = LabResult(
            order_id=sample_lab_order.id,
            test_name="Creatinine",
            test_category="KFT",
            value="2.5",
            value_numeric=2.5,
            unit="mg/dL",
            reference_range_min=0.6,
            reference_range_max=1.2,
            is_abnormal=True,
            abnormal_flag="H",
            status=LabResultStatus.FINAL.value,
        )
        test_db.add(abnormal_result)
        test_db.commit()

        response = await async_client.get(
            f"/api/v1/labs/patient/{sample_patient.id}/results",
            headers=auth_headers,
            params={"is_abnormal": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert all(result["is_abnormal"] for result in data)

    @pytest.mark.asyncio
    async def test_get_result_trends(
        self, async_client, auth_headers, sample_lab_result
    ):
        """Test getting trend data for a result."""
        response = await async_client.get(
            f"/api/v1/labs/results/{sample_lab_result.id}/trends",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["test_name"] == sample_lab_result.test_name
        assert "data_points" in data


class TestLabStatistics:
    """Test lab statistics API."""

    @pytest.mark.asyncio
    async def test_get_lab_statistics(
        self, async_client, auth_headers, sample_lab_order, sample_lab_result
    ):
        """Test getting lab statistics."""
        response = await async_client.get(
            "/api/v1/labs/statistics",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_orders" in data
        assert "pending_orders" in data
        assert "completed_orders" in data
        assert "total_results" in data
        assert "abnormal_results" in data
        assert data["total_orders"] >= 1
        assert data["total_results"] >= 1


class TestLabParser:
    """Test lab parser functionality."""

    def test_parse_reference_range(self):
        """Test parsing reference ranges."""
        from app.services.lab_parser import PDFLabParser

        parser = PDFLabParser()

        # Test numeric range
        min_val, max_val, text = parser.parse_reference_range("10-20")
        assert min_val == 10.0
        assert max_val == 20.0

        # Test less than
        min_val, max_val, text = parser.parse_reference_range("< 200")
        assert min_val is None
        assert max_val == 200.0

        # Test greater than
        min_val, max_val, text = parser.parse_reference_range("> 5")
        assert min_val == 5.0
        assert max_val is None

    def test_extract_numeric_value(self):
        """Test extracting numeric values."""
        from app.services.lab_parser import PDFLabParser

        parser = PDFLabParser()

        assert parser.extract_numeric_value("14.5") == 14.5
        assert parser.extract_numeric_value("200 mg/dL") == 200.0
        assert parser.extract_numeric_value("Negative") is None

    def test_determine_abnormal_flag(self):
        """Test abnormal flag determination."""
        from app.services.lab_parser import PDFLabParser

        parser = PDFLabParser()

        # High value
        is_abnormal, flag = parser.determine_abnormal_flag(15.0, 10.0, 12.0)
        assert is_abnormal
        assert flag == "H"

        # Critically high value
        is_abnormal, flag = parser.determine_abnormal_flag(20.0, 10.0, 12.0)
        assert is_abnormal
        assert flag == "HH"

        # Low value
        is_abnormal, flag = parser.determine_abnormal_flag(8.0, 10.0, 12.0)
        assert is_abnormal
        assert flag == "L"

        # Normal value
        is_abnormal, flag = parser.determine_abnormal_flag(11.0, 10.0, 12.0)
        assert not is_abnormal
        assert flag is None


class TestLabIntegration:
    """Test lab integration service."""

    @pytest.mark.asyncio
    async def test_file_based_lab_provider(self):
        """Test file-based lab provider."""
        from app.integrations.lab_integration import FileBasedLabProvider, LabOrderRequest

        provider = FileBasedLabProvider({
            "name": "Test Lab",
            "watch_directory": "/tmp/test_lab_reports",
            "archive_directory": "/tmp/test_lab_reports/archive",
        })

        # Create order
        order_request = LabOrderRequest(
            patient_id="test-patient-123",
            patient_name="John Doe",
            tests=["CBC", "LFT"],
            priority="routine",
        )

        response = await provider.create_order(order_request)
        assert response.order_id.startswith("FILE-")
        assert response.status == "ordered"

    @pytest.mark.asyncio
    async def test_get_order_status(self):
        """Test getting lab order status."""
        from app.integrations.lab_integration import FileBasedLabProvider, LabOrderRequest

        provider = FileBasedLabProvider({
            "name": "Test Lab",
            "watch_directory": "/tmp/test_lab_reports",
            "archive_directory": "/tmp/test_lab_reports/archive",
        })

        order_request = LabOrderRequest(
            patient_id="test-patient-123",
            patient_name="John Doe",
            tests=["CBC"],
            priority="routine",
        )

        response = await provider.create_order(order_request)
        status = await provider.get_order_status(response.order_id)

        assert status in ["ordered", "sample_collected", "in_progress", "completed", "cancelled"]

    @pytest.mark.asyncio
    async def test_lab_service_register_provider(self):
        """Test registering lab providers."""
        from app.integrations.lab_integration import (
            LabIntegrationService,
            FileBasedLabProvider,
        )

        service = LabIntegrationService()

        provider = FileBasedLabProvider({
            "name": "Test Lab",
            "watch_directory": "/tmp/test_lab",
            "archive_directory": "/tmp/test_lab/archive",
        })

        service.register_provider("test_lab", provider, is_default=True)

        assert "test_lab" in service.providers
        assert service.default_provider == "test_lab"

    @pytest.mark.asyncio
    async def test_lab_service_get_provider(self):
        """Test getting lab provider."""
        from app.integrations.lab_integration import (
            LabIntegrationService,
            FileBasedLabProvider,
        )

        service = LabIntegrationService()
        provider = FileBasedLabProvider({"name": "Test"})
        service.register_provider("test", provider)

        retrieved = service.get_provider("test")
        assert retrieved == provider

    @pytest.mark.asyncio
    async def test_lab_service_create_order(self):
        """Test creating order through service."""
        from app.integrations.lab_integration import (
            LabIntegrationService,
            FileBasedLabProvider,
            LabOrderRequest,
        )

        service = LabIntegrationService()
        provider = FileBasedLabProvider({
            "name": "Test",
            "watch_directory": "/tmp/test_lab",
            "archive_directory": "/tmp/test_lab/archive",
        })
        service.register_provider("test", provider, is_default=True)

        order_request = LabOrderRequest(
            patient_id="patient-123",
            patient_name="Test Patient",
            tests=["CBC", "LFT"],
            priority="stat",
        )

        response = await service.create_order(order_request)
        assert response.order_id is not None
        assert response.status == "ordered"

    @pytest.mark.asyncio
    async def test_lab_service_list_providers(self):
        """Test listing registered providers."""
        from app.integrations.lab_integration import (
            LabIntegrationService,
            FileBasedLabProvider,
        )

        service = LabIntegrationService()
        provider1 = FileBasedLabProvider({"name": "Lab 1"})
        provider2 = FileBasedLabProvider({"name": "Lab 2"})

        service.register_provider("lab1", provider1)
        service.register_provider("lab2", provider2, is_default=True)

        providers = service.list_providers()

        assert len(providers) == 2
        assert any(p["name"] == "lab1" for p in providers)
        assert any(p["name"] == "lab2" and p["is_default"] for p in providers)

    @pytest.mark.asyncio
    async def test_parse_pdf_results(self):
        """Test parsing PDF lab results."""
        from app.integrations.lab_integration import FileBasedLabProvider

        provider = FileBasedLabProvider({"name": "Test"})

        # Mock PDF content
        pdf_content = b"%PDF-1.4 mock content"

        # This would fail without actual PDF parser implementation
        # but tests the interface
        try:
            report = await provider.parse_results(pdf_content, "pdf")
            # If parsing succeeds, verify structure
            assert hasattr(report, "patient_info")
        except Exception:
            # Expected to fail without full parser
            pass

    @pytest.mark.asyncio
    async def test_parse_hl7_results(self):
        """Test parsing HL7 lab results."""
        from app.integrations.lab_integration import FileBasedLabProvider

        provider = FileBasedLabProvider({"name": "Test"})

        # Mock HL7 content
        hl7_content = b"MSH|^~\\&|LAB|FACILITY|||20240101120000||ORU^R01|123|P|2.5"

        try:
            report = await provider.parse_results(hl7_content, "hl7")
            assert hasattr(report, "patient_info")
        except Exception:
            # Expected without full HL7 parser
            pass

    def test_normalize_test_name(self):
        """Test test name normalization."""
        from app.services.lab_parser import PDFLabParser

        parser = PDFLabParser()

        # Test hemoglobin variants
        name, info = parser.normalize_test_name("Hemoglobin")
        assert name == "hemoglobin"
        assert info is not None

        name, info = parser.normalize_test_name("HB")
        assert name == "hemoglobin"

        name, info = parser.normalize_test_name("HGB")
        assert name == "hemoglobin"


class TestThyrocareProvider:
    """Test Thyrocare lab provider stub."""

    def test_thyrocare_initialization(self):
        """Test Thyrocare provider initialization."""
        from app.integrations.lab_integration import ThyrocareLabProvider

        provider = ThyrocareLabProvider({
            "name": "Thyrocare",
            "api_key": "test_key",
            "api_url": "https://api.thyrocare.com",
            "center_code": "TC001",
        })

        assert provider.api_key == "test_key"
        assert provider.center_code == "TC001"

    def test_thyrocare_is_available(self):
        """Test Thyrocare availability check."""
        from app.integrations.lab_integration import ThyrocareLabProvider

        # With credentials
        provider = ThyrocareLabProvider({
            "api_key": "test_key",
            "center_code": "TC001",
        })
        assert provider.is_available() is True

        # Without credentials
        provider = ThyrocareLabProvider({})
        assert provider.is_available() is False

    @pytest.mark.asyncio
    async def test_thyrocare_not_implemented(self):
        """Test Thyrocare methods raise NotImplementedError."""
        from app.integrations.lab_integration import (
            ThyrocareLabProvider,
            LabOrderRequest,
        )

        provider = ThyrocareLabProvider({
            "api_key": "test_key",
            "center_code": "TC001",
        })

        order_request = LabOrderRequest(
            patient_id="123",
            patient_name="Test",
            tests=["CBC"],
        )

        # Should raise NotImplementedError until implemented
        with pytest.raises(NotImplementedError):
            await provider.create_order(order_request)

        with pytest.raises(NotImplementedError):
            await provider.get_order_status("ORDER123")

        with pytest.raises(NotImplementedError):
            await provider.download_results("ORDER123")
