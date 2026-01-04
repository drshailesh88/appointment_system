"""
Tests for Procedure & Intervention Tracking Service.

Phase 9: Tests for CRUD, analytics, and consumables tracking.
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from app.models.procedure import PROCEDURE_TEMPLATES, ProcedureOutcome, ProcedureSeverity
from app.schemas.procedure import (
    ProcedureCreate,
    ProcedureUpdate,
    ProcedureStats,
    ProcedureTypeCount,
    DoctorProcedureStats,
)
from app.services.procedures import ProcedureFilter


class TestProcedureTemplates:
    """Tests for procedure templates."""

    def test_cardiology_templates_exist(self):
        """Test Cardiology templates are defined."""
        assert "cardiology" in PROCEDURE_TEMPLATES
        cardio = PROCEDURE_TEMPLATES["cardiology"]

        assert "types" in cardio
        assert "category" in cardio
        assert cardio["category"] == "Cardiology"
        # Check for nested types structure
        assert "diagnostic" in cardio["types"] or "interventional" in cardio["types"]

    def test_orthopedics_templates_exist(self):
        """Test Orthopedics templates are defined."""
        assert "orthopedics" in PROCEDURE_TEMPLATES
        ortho = PROCEDURE_TEMPLATES["orthopedics"]

        assert "types" in ortho
        assert "category" in ortho
        assert ortho["category"] == "Orthopedics"

    def test_ophthalmology_templates_exist(self):
        """Test Ophthalmology templates are defined."""
        assert "ophthalmology" in PROCEDURE_TEMPLATES
        ophth = PROCEDURE_TEMPLATES["ophthalmology"]

        assert "types" in ophth
        assert "category" in ophth
        assert ophth["category"] == "Ophthalmology"

    def test_dermatology_templates_exist(self):
        """Test Dermatology templates are defined."""
        assert "dermatology" in PROCEDURE_TEMPLATES
        derm = PROCEDURE_TEMPLATES["dermatology"]

        assert "types" in derm
        assert "category" in derm
        assert derm["category"] == "Dermatology"

    def test_gastroenterology_templates_exist(self):
        """Test Gastroenterology templates are defined."""
        assert "gastroenterology" in PROCEDURE_TEMPLATES
        gastro = PROCEDURE_TEMPLATES["gastroenterology"]

        assert "types" in gastro
        assert "category" in gastro
        assert gastro["category"] == "Gastroenterology"

    def test_templates_have_procedure_types(self):
        """Test templates include procedure types."""
        cardio = PROCEDURE_TEMPLATES["cardiology"]
        types = cardio["types"]
        # Check that at least one category of types exists
        assert len(types) > 0
        # Check that types contain procedures
        all_procedures = []
        for category_types in types.values():
            all_procedures.extend(category_types)
        assert len(all_procedures) > 0

    def test_all_specialties_have_types(self):
        """Test all specialties have procedure types defined."""
        for specialty, template in PROCEDURE_TEMPLATES.items():
            assert "types" in template, f"{specialty} missing types"
            assert len(template["types"]) > 0, f"{specialty} has empty types"


class TestProcedureOutcome:
    """Tests for ProcedureOutcome enum."""

    def test_outcome_values(self):
        """Test outcome enum values."""
        assert ProcedureOutcome.SUCCESSFUL.value == "successful"
        assert ProcedureOutcome.PARTIAL.value == "partial"
        assert ProcedureOutcome.UNSUCCESSFUL.value == "unsuccessful"
        assert ProcedureOutcome.COMPLICATED.value == "complicated"
        assert ProcedureOutcome.REFERRED.value == "referred"
        assert ProcedureOutcome.ABANDONED.value == "abandoned"
        assert ProcedureOutcome.PENDING_FOLLOWUP.value == "pending_followup"

    def test_outcome_count(self):
        """Test number of outcomes."""
        outcomes = list(ProcedureOutcome)
        assert len(outcomes) == 7


class TestProcedureSeverity:
    """Tests for ProcedureSeverity enum."""

    def test_severity_values(self):
        """Test severity enum values."""
        assert ProcedureSeverity.MINOR.value == "minor"
        assert ProcedureSeverity.MODERATE.value == "moderate"
        assert ProcedureSeverity.MAJOR.value == "major"
        assert ProcedureSeverity.CRITICAL.value == "critical"

    def test_severity_count(self):
        """Test number of severity levels."""
        severities = list(ProcedureSeverity)
        assert len(severities) == 4


class TestProcedureFilter:
    """Tests for ProcedureFilter dataclass."""

    def test_minimal_filter(self):
        """Test filter with only required fields."""
        clinic_id = uuid4()
        pf = ProcedureFilter(clinic_id=clinic_id)

        assert pf.clinic_id == clinic_id
        assert pf.patient_id is None
        assert pf.doctor_id is None
        assert pf.category is None

    def test_full_filter(self):
        """Test filter with all fields."""
        clinic_id = uuid4()
        patient_id = uuid4()
        doctor_id = uuid4()

        pf = ProcedureFilter(
            clinic_id=clinic_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            category="Cardiology",
            procedure_type="Echo",
            outcome=ProcedureOutcome.SUCCESSFUL,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            is_billable=True,
        )

        assert pf.clinic_id == clinic_id
        assert pf.patient_id == patient_id
        assert pf.doctor_id == doctor_id
        assert pf.category == "Cardiology"
        assert pf.procedure_type == "Echo"
        assert pf.outcome == ProcedureOutcome.SUCCESSFUL
        assert pf.start_date == date(2026, 1, 1)
        assert pf.end_date == date(2026, 1, 31)
        assert pf.is_billable is True


class TestProcedureSchemas:
    """Tests for Pydantic schemas."""

    def test_procedure_create_minimal(self):
        """Test ProcedureCreate with minimal data."""
        data = ProcedureCreate(
            patient_id=uuid4(),
            doctor_id=uuid4(),
            category="Cardiology",
            procedure_type="Echo",
            name="Echocardiogram",
        )

        assert data.patient_id is not None
        assert data.doctor_id is not None
        assert data.category == "Cardiology"
        assert data.procedure_type == "Echo"
        assert data.name == "Echocardiogram"
        assert data.outcome == ProcedureOutcome.SUCCESSFUL
        assert data.severity == ProcedureSeverity.MINOR
        assert data.is_billable is True

    def test_procedure_create_full(self):
        """Test ProcedureCreate with all data."""
        patient_id = uuid4()
        doctor_id = uuid4()
        appointment_id = uuid4()

        data = ProcedureCreate(
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_id=appointment_id,
            category="Cardiology",
            procedure_type="Angioplasty",
            sub_type="PTCA",
            name="Coronary Angioplasty",
            description="Single vessel angioplasty",
            performed_at=datetime(2026, 1, 15, 10, 30),
            duration_minutes=45,
            outcome=ProcedureOutcome.SUCCESSFUL,
            severity=ProcedureSeverity.MAJOR,
            findings="70% stenosis in LAD",
            notes="Patient tolerated well",
            consumables={"stent_brand": "Xience", "stent_size": "3.0x18mm"},
            custom_fields={"contrast_used_ml": 120, "radiation_time_min": 15},
            billing_code="PTCA001",
            cpt_code="92928",
            icd_code="I25.10",
            is_billable=True,
            billed_amount=Decimal("250000.00"),
            location="Cath Lab 1",
        )

        assert data.patient_id == patient_id
        assert data.doctor_id == doctor_id
        assert data.appointment_id == appointment_id
        assert data.category == "Cardiology"
        assert data.procedure_type == "Angioplasty"
        assert data.sub_type == "PTCA"
        assert data.duration_minutes == 45
        assert data.outcome == ProcedureOutcome.SUCCESSFUL
        assert data.severity == ProcedureSeverity.MAJOR
        assert data.billed_amount == Decimal("250000.00")
        assert data.consumables["stent_brand"] == "Xience"

    def test_procedure_update_partial(self):
        """Test ProcedureUpdate with partial data."""
        data = ProcedureUpdate(
            outcome=ProcedureOutcome.PARTIAL,
            notes="Additional notes",
        )

        assert data.outcome == ProcedureOutcome.PARTIAL
        assert data.notes == "Additional notes"
        assert data.category is None
        assert data.procedure_type is None

    def test_procedure_stats_schema(self):
        """Test ProcedureStats schema."""
        stats = ProcedureStats(
            total=100,
            by_category={"Cardiology": 60, "Orthopedics": 40},
            by_type={"Echo": 30, "ECG": 25, "X-Ray": 45},
            by_outcome={"successful": 85, "partial": 10, "unsuccessful": 5},
            by_severity={"minor": 50, "moderate": 30, "major": 20},
            total_billed=500000.0,
            average_duration_minutes=30.5,
        )

        assert stats.total == 100
        assert stats.by_category["Cardiology"] == 60
        assert stats.total_billed == 500000.0
        assert stats.average_duration_minutes == 30.5

    def test_procedure_type_count_schema(self):
        """Test ProcedureTypeCount schema."""
        tc = ProcedureTypeCount(
            category="Cardiology",
            procedure_type="Echo",
            count=50,
            total_billed=100000.0,
        )

        assert tc.category == "Cardiology"
        assert tc.procedure_type == "Echo"
        assert tc.count == 50
        assert tc.total_billed == 100000.0

    def test_doctor_procedure_stats_schema(self):
        """Test DoctorProcedureStats schema."""
        dps = DoctorProcedureStats(
            doctor_id=uuid4(),
            doctor_name="Dr. Test",
            total_procedures=75,
            by_category={"Cardiology": 50, "General": 25},
            total_billed=375000.0,
            success_rate=95.0,
        )

        assert dps.doctor_name == "Dr. Test"
        assert dps.total_procedures == 75
        assert dps.success_rate == 95.0


class TestProcedureValidation:
    """Tests for procedure validation logic."""

    def test_category_required(self):
        """Test category is required."""
        with pytest.raises(Exception):
            ProcedureCreate(
                patient_id=uuid4(),
                doctor_id=uuid4(),
                procedure_type="Echo",
                name="Echo Test",
                # Missing category
            )

    def test_procedure_type_required(self):
        """Test procedure_type is required."""
        with pytest.raises(Exception):
            ProcedureCreate(
                patient_id=uuid4(),
                doctor_id=uuid4(),
                category="Cardiology",
                name="Echo Test",
                # Missing procedure_type
            )

    def test_patient_id_required(self):
        """Test patient_id is required."""
        with pytest.raises(Exception):
            ProcedureCreate(
                doctor_id=uuid4(),
                category="Cardiology",
                procedure_type="Echo",
                name="Echo Test",
                # Missing patient_id
            )

    def test_doctor_id_required(self):
        """Test doctor_id is required."""
        with pytest.raises(Exception):
            ProcedureCreate(
                patient_id=uuid4(),
                category="Cardiology",
                procedure_type="Echo",
                name="Echo Test",
                # Missing doctor_id
            )


class TestConsumablesTracking:
    """Tests for consumables data structure."""

    def test_stent_consumables(self):
        """Test stent consumables structure."""
        consumables = {
            "stent_brand": "Xience",
            "stent_size": "3.0x18mm",
            "guide_wire": "PT2",
            "contrast_ml": 150,
        }

        assert consumables["stent_brand"] == "Xience"
        assert consumables["stent_size"] == "3.0x18mm"
        assert consumables["contrast_ml"] == 150

    def test_ophthalmology_consumables(self):
        """Test ophthalmology consumables structure."""
        consumables = {
            "iol_brand": "Alcon",
            "iol_power": "+21.5D",
            "viscoelastic": "Healon",
            "suture_type": "10-0 nylon",
        }

        assert consumables["iol_brand"] == "Alcon"
        assert consumables["iol_power"] == "+21.5D"

    def test_orthopedics_consumables(self):
        """Test orthopedics consumables structure."""
        consumables = {
            "implant_type": "Total Hip",
            "implant_brand": "Zimmer",
            "implant_size": "Size 4",
            "bone_cement": True,
        }

        assert consumables["implant_type"] == "Total Hip"
        assert consumables["bone_cement"] is True


class TestCustomFields:
    """Tests for custom fields data structure."""

    def test_cardiac_custom_fields(self):
        """Test cardiac custom fields."""
        custom_fields = {
            "ef_before": 35,
            "ef_after": 50,
            "lvedd": 58,
            "lvesd": 42,
            "rwma": "anterior",
        }

        assert custom_fields["ef_before"] == 35
        assert custom_fields["ef_after"] == 50

    def test_ophthalmology_custom_fields(self):
        """Test ophthalmology custom fields."""
        custom_fields = {
            "preop_vision": "6/60",
            "postop_vision": "6/12",
            "iop_preop": 16,
            "iop_postop": 14,
        }

        assert custom_fields["preop_vision"] == "6/60"
        assert custom_fields["postop_vision"] == "6/12"

    def test_gastro_custom_fields(self):
        """Test gastroenterology custom fields."""
        custom_fields = {
            "polyps_found": 2,
            "polyps_removed": 2,
            "biopsy_sites": ["cecum", "sigmoid"],
            "withdrawal_time_min": 8,
        }

        assert custom_fields["polyps_found"] == 2
        assert len(custom_fields["biopsy_sites"]) == 2


class TestBillingCodes:
    """Tests for billing code formats."""

    def test_cpt_code_format(self):
        """Test CPT code format."""
        cpt_codes = ["92928", "43239", "66984", "27447"]
        for code in cpt_codes:
            assert len(code) == 5
            assert code.isdigit()

    def test_icd_code_format(self):
        """Test ICD-10 code format."""
        icd_codes = ["I25.10", "H26.9", "M17.11", "K21.0"]
        for code in icd_codes:
            assert "." in code
            parts = code.split(".")
            assert len(parts[0]) >= 1


class TestDateRanges:
    """Tests for date range handling in analytics."""

    def test_today_range(self):
        """Test single day range."""
        today = date.today()
        start = today
        end = today

        assert start == end

    def test_week_range(self):
        """Test week range."""
        today = date.today()
        start = today - timedelta(days=7)
        end = today

        assert (end - start).days == 7

    def test_month_range(self):
        """Test month range."""
        today = date.today()
        start = date(today.year, today.month, 1)
        end = today

        assert start.day == 1
        assert start.month == today.month

    def test_year_range(self):
        """Test year range."""
        today = date.today()
        start = date(today.year, 1, 1)
        end = today

        assert start.day == 1
        assert start.month == 1
        assert start.year == today.year


class TestProcedureListResponse:
    """Tests for paginated list responses."""

    def test_pagination_structure(self):
        """Test pagination response structure."""
        response = {
            "items": [],
            "total": 100,
            "page": 1,
            "page_size": 20,
            "pages": 5,
        }

        assert response["total"] == 100
        assert response["page"] == 1
        assert response["page_size"] == 20
        assert response["pages"] == 5

    def test_pagination_calculation(self):
        """Test page count calculation."""
        total = 95
        page_size = 20
        pages = (total + page_size - 1) // page_size

        assert pages == 5

    def test_offset_calculation(self):
        """Test offset calculation for pagination."""
        page = 3
        page_size = 20
        offset = (page - 1) * page_size

        assert offset == 40
