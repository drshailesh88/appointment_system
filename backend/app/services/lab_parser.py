"""
Lab result parser for PDF and HL7 formats.

Supports common Indian lab formats and FHIR standards.
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ParsedLabResult:
    """Parsed lab result data."""

    test_name: str
    value: str
    value_numeric: float | None
    unit: str | None
    reference_range_min: float | None
    reference_range_max: float | None
    reference_range_text: str | None
    is_abnormal: bool
    abnormal_flag: str | None  # H, L, HH, LL, A
    test_code: str | None = None
    test_category: str | None = None
    notes: str | None = None


@dataclass
class ParsedLabReport:
    """Parsed lab report document."""

    patient_name: str | None
    patient_id: str | None
    lab_order_id: str | None
    report_date: datetime | None
    lab_provider: str | None
    results: list[ParsedLabResult]
    raw_text: str
    metadata: dict[str, Any]


# Common Indian lab test patterns
INDIAN_LAB_TESTS = {
    # CBC (Complete Blood Count)
    "hemoglobin": {"names": ["hemoglobin", "hb", "hgb"], "unit": "g/dL", "range": (12.0, 16.0)},
    "rbc": {"names": ["rbc", "red blood cell"], "unit": "million/cumm", "range": (4.5, 5.5)},
    "wbc": {"names": ["wbc", "white blood cell", "tlc"], "unit": "/cumm", "range": (4000, 11000)},
    "platelet": {"names": ["platelet", "plt"], "unit": "/cumm", "range": (150000, 450000)},
    "hematocrit": {"names": ["hematocrit", "hct", "pcv"], "unit": "%", "range": (36.0, 46.0)},
    "mcv": {"names": ["mcv", "mean corpuscular volume"], "unit": "fL", "range": (80.0, 100.0)},
    "mch": {"names": ["mch", "mean corpuscular hemoglobin"], "unit": "pg", "range": (27.0, 32.0)},
    "mchc": {"names": ["mchc"], "unit": "g/dL", "range": (32.0, 36.0)},

    # LFT (Liver Function Test)
    "sgot": {"names": ["sgot", "ast", "aspartate"], "unit": "U/L", "range": (0, 40)},
    "sgpt": {"names": ["sgpt", "alt", "alanine"], "unit": "U/L", "range": (0, 41)},
    "bilirubin_total": {"names": ["bilirubin total", "total bilirubin"], "unit": "mg/dL", "range": (0.3, 1.2)},
    "bilirubin_direct": {"names": ["bilirubin direct", "direct bilirubin"], "unit": "mg/dL", "range": (0.0, 0.3)},
    "alkaline_phosphatase": {"names": ["alkaline phosphatase", "alp"], "unit": "U/L", "range": (44, 147)},
    "total_protein": {"names": ["total protein", "protein total"], "unit": "g/dL", "range": (6.0, 8.3)},
    "albumin": {"names": ["albumin"], "unit": "g/dL", "range": (3.5, 5.5)},
    "globulin": {"names": ["globulin"], "unit": "g/dL", "range": (2.0, 3.5)},

    # KFT (Kidney Function Test)
    "creatinine": {"names": ["creatinine", "serum creatinine"], "unit": "mg/dL", "range": (0.6, 1.2)},
    "urea": {"names": ["urea", "blood urea"], "unit": "mg/dL", "range": (15, 40)},
    "bun": {"names": ["bun", "blood urea nitrogen"], "unit": "mg/dL", "range": (7, 20)},
    "uric_acid": {"names": ["uric acid"], "unit": "mg/dL", "range": (3.5, 7.2)},

    # Lipid Profile
    "cholesterol": {"names": ["cholesterol", "total cholesterol"], "unit": "mg/dL", "range": (0, 200)},
    "triglycerides": {"names": ["triglycerides", "tg"], "unit": "mg/dL", "range": (0, 150)},
    "hdl": {"names": ["hdl", "hdl cholesterol"], "unit": "mg/dL", "range": (40, 60)},
    "ldl": {"names": ["ldl", "ldl cholesterol"], "unit": "mg/dL", "range": (0, 100)},
    "vldl": {"names": ["vldl"], "unit": "mg/dL", "range": (2, 30)},

    # Thyroid
    "tsh": {"names": ["tsh", "thyroid stimulating hormone"], "unit": "uIU/mL", "range": (0.4, 4.0)},
    "t3": {"names": ["t3", "triiodothyronine"], "unit": "ng/dL", "range": (80, 200)},
    "t4": {"names": ["t4", "thyroxine"], "unit": "ug/dL", "range": (4.5, 12.0)},

    # Diabetes
    "glucose_fasting": {"names": ["glucose fasting", "fbs", "fasting blood sugar"], "unit": "mg/dL", "range": (70, 100)},
    "glucose_pp": {"names": ["glucose pp", "ppbs", "post prandial"], "unit": "mg/dL", "range": (70, 140)},
    "hba1c": {"names": ["hba1c", "glycated hemoglobin"], "unit": "%", "range": (4.0, 5.6)},
}


class LabParser(ABC):
    """Abstract base class for lab report parsers."""

    @abstractmethod
    def parse(self, content: bytes | str) -> ParsedLabReport:
        """Parse lab report content."""
        pass

    def normalize_test_name(self, raw_name: str) -> tuple[str, dict | None]:
        """
        Normalize test name to standard form.

        Returns:
            Tuple of (normalized_name, test_info)
        """
        raw_lower = raw_name.lower().strip()

        # Try to match against known tests
        for test_key, test_info in INDIAN_LAB_TESTS.items():
            for name_variant in test_info["names"]:
                if name_variant in raw_lower:
                    return test_key, test_info

        # Return as-is if no match
        return raw_name, None

    def extract_numeric_value(self, value_str: str) -> float | None:
        """Extract numeric value from string."""
        try:
            # Remove common non-numeric characters
            cleaned = re.sub(r'[^0-9.\-]', '', value_str)
            if cleaned:
                return float(cleaned)
        except (ValueError, AttributeError):
            pass
        return None

    def parse_reference_range(
        self, range_str: str
    ) -> tuple[float | None, float | None, str]:
        """
        Parse reference range string.

        Returns:
            Tuple of (min, max, original_text)
        """
        # Pattern: "10-20", "10 - 20", "< 200", "> 5", "Negative", etc.
        range_str = range_str.strip()

        # Numeric range: 10-20, 10 - 20
        match = re.match(r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)', range_str)
        if match:
            return float(match.group(1)), float(match.group(2)), range_str

        # Less than: < 200
        match = re.match(r'<\s*(\d+\.?\d*)', range_str)
        if match:
            return None, float(match.group(1)), range_str

        # Greater than: > 5
        match = re.match(r'>\s*(\d+\.?\d*)', range_str)
        if match:
            return float(match.group(1)), None, range_str

        # Upto: Upto 200
        match = re.match(r'(?:upto|up to)\s*(\d+\.?\d*)', range_str, re.IGNORECASE)
        if match:
            return None, float(match.group(1)), range_str

        # Return as text reference
        return None, None, range_str

    def determine_abnormal_flag(
        self,
        value_numeric: float | None,
        ref_min: float | None,
        ref_max: float | None,
    ) -> tuple[bool, str | None]:
        """
        Determine if value is abnormal and flag type.

        Returns:
            Tuple of (is_abnormal, flag)
            Flags: H (high), L (low), HH (critically high), LL (critically low)
        """
        if value_numeric is None:
            return False, None

        is_abnormal = False
        flag = None

        if ref_max is not None and value_numeric > ref_max:
            is_abnormal = True
            # Critically high if > 150% of max
            if value_numeric > ref_max * 1.5:
                flag = "HH"
            else:
                flag = "H"

        if ref_min is not None and value_numeric < ref_min:
            is_abnormal = True
            # Critically low if < 50% of min
            if ref_min > 0 and value_numeric < ref_min * 0.5:
                flag = "LL"
            else:
                flag = "L"

        return is_abnormal, flag


class PDFLabParser(LabParser):
    """Parse lab results from PDF files."""

    def parse(self, content: bytes | str) -> ParsedLabReport:
        """Parse PDF lab report."""
        try:
            from pypdf import PdfReader
            from io import BytesIO
        except ImportError:
            logger.error("pypdf not installed. Install with: pip install pypdf")
            raise ImportError("pypdf required for PDF parsing")

        # Read PDF
        if isinstance(content, bytes):
            pdf_file = BytesIO(content)
        else:
            pdf_file = content

        reader = PdfReader(pdf_file)

        # Extract all text
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"

        return self.parse_text(text)

    def parse_text(self, text: str) -> ParsedLabReport:
        """Parse text extracted from PDF."""
        results = []
        metadata = {}

        # Extract header info (patterns vary by lab)
        patient_name = self._extract_patient_name(text)
        patient_id = self._extract_patient_id(text)
        lab_order_id = self._extract_order_id(text)
        report_date = self._extract_report_date(text)
        lab_provider = self._extract_lab_name(text)

        # Parse test results
        # Common pattern: TEST_NAME    VALUE    UNIT    REFERENCE_RANGE
        lines = text.split('\n')

        for i, line in enumerate(lines):
            result = self._parse_result_line(line, lines[i:i+3])
            if result:
                results.append(result)

        return ParsedLabReport(
            patient_name=patient_name,
            patient_id=patient_id,
            lab_order_id=lab_order_id,
            report_date=report_date,
            lab_provider=lab_provider,
            results=results,
            raw_text=text,
            metadata=metadata,
        )

    def _parse_result_line(
        self, line: str, context_lines: list[str]
    ) -> ParsedLabResult | None:
        """Parse a single result line."""
        # Pattern 1: TEST_NAME  VALUE  UNIT  REF_RANGE
        # Example: "Hemoglobin    14.5    g/dL    12.0-16.0"
        parts = re.split(r'\s{2,}|\t', line.strip())

        if len(parts) < 2:
            return None

        test_name = parts[0].strip()

        # Skip header/footer lines
        if any(skip in test_name.lower() for skip in ['test', 'parameter', 'name', 'page', 'lab', 'report']):
            if test_name.lower() in ['test', 'parameter', 'test name']:
                return None

        # Must have a value
        if len(parts) < 2:
            return None

        value_str = parts[1].strip()
        if not value_str:
            return None

        # Extract components
        unit = parts[2].strip() if len(parts) > 2 else None
        ref_range_str = parts[3].strip() if len(parts) > 3 else ""

        # Parse reference range
        ref_min, ref_max, ref_text = self.parse_reference_range(ref_range_str)

        # Extract numeric value
        value_numeric = self.extract_numeric_value(value_str)

        # Normalize test name
        normalized_name, test_info = self.normalize_test_name(test_name)

        # Use default ranges if available
        if test_info and not (ref_min and ref_max):
            ref_min, ref_max = test_info["range"]

        # Determine abnormality
        is_abnormal, abnormal_flag = self.determine_abnormal_flag(
            value_numeric, ref_min, ref_max
        )

        return ParsedLabResult(
            test_name=test_name,
            value=value_str,
            value_numeric=value_numeric,
            unit=unit,
            reference_range_min=ref_min,
            reference_range_max=ref_max,
            reference_range_text=ref_text or ref_range_str,
            is_abnormal=is_abnormal,
            abnormal_flag=abnormal_flag,
            test_code=None,
            test_category=self._categorize_test(normalized_name),
            notes=None,
        )

    def _extract_patient_name(self, text: str) -> str | None:
        """Extract patient name from text."""
        patterns = [
            r'Patient Name\s*:?\s*([A-Z][a-zA-Z\s]+)',
            r'Name\s*:?\s*([A-Z][a-zA-Z\s]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_patient_id(self, text: str) -> str | None:
        """Extract patient ID from text."""
        patterns = [
            r'Patient ID\s*:?\s*([A-Z0-9]+)',
            r'MR No\s*:?\s*([A-Z0-9]+)',
            r'UHID\s*:?\s*([A-Z0-9]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_order_id(self, text: str) -> str | None:
        """Extract lab order ID from text."""
        patterns = [
            r'Order No\s*:?\s*([A-Z0-9]+)',
            r'Lab No\s*:?\s*([A-Z0-9]+)',
            r'Sample ID\s*:?\s*([A-Z0-9]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_report_date(self, text: str) -> datetime | None:
        """Extract report date from text."""
        patterns = [
            r'Report Date\s*:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'Date\s*:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                try:
                    # Try different date formats
                    for fmt in ['%d-%m-%Y', '%d/%m/%Y', '%d-%m-%y', '%d/%m/%y']:
                        try:
                            return datetime.strptime(date_str, fmt)
                        except ValueError:
                            continue
                except Exception:
                    pass

        return None

    def _extract_lab_name(self, text: str) -> str | None:
        """Extract lab provider name from text."""
        # Usually in header, first few lines
        lines = text.split('\n')[:5]

        # Look for common lab names
        common_labs = [
            'pathology', 'diagnostics', 'laboratory', 'lab',
            'thyrocare', 'dr lal', 'metropolis', 'srl'
        ]

        for line in lines:
            for lab in common_labs:
                if lab in line.lower():
                    return line.strip()

        return None

    def _categorize_test(self, test_name: str) -> str | None:
        """Categorize test into groups (CBC, LFT, etc.)."""
        test_lower = test_name.lower()

        # CBC tests
        if any(x in test_lower for x in ['hemoglobin', 'rbc', 'wbc', 'platelet', 'hematocrit', 'mcv', 'mch']):
            return "CBC"

        # LFT tests
        if any(x in test_lower for x in ['sgot', 'sgpt', 'bilirubin', 'alkaline', 'protein', 'albumin']):
            return "LFT"

        # KFT tests
        if any(x in test_lower for x in ['creatinine', 'urea', 'bun', 'uric']):
            return "KFT"

        # Lipid Profile
        if any(x in test_lower for x in ['cholesterol', 'triglyceride', 'hdl', 'ldl', 'vldl']):
            return "Lipid Profile"

        # Thyroid
        if any(x in test_lower for x in ['tsh', 't3', 't4', 'thyroid']):
            return "Thyroid"

        # Diabetes
        if any(x in test_lower for x in ['glucose', 'fbs', 'ppbs', 'hba1c', 'sugar']):
            return "Diabetes"

        return None


class HL7LabParser(LabParser):
    """Parse lab results from HL7 messages."""

    def parse(self, content: bytes | str) -> ParsedLabReport:
        """Parse HL7 lab report."""
        if isinstance(content, bytes):
            content = content.decode('utf-8')

        # HL7 segments are separated by newlines or \r
        segments = content.split('\n')

        results = []
        metadata = {}

        patient_name = None
        patient_id = None
        lab_order_id = None
        report_date = None
        lab_provider = None

        # Parse segments
        for segment in segments:
            fields = segment.split('|')

            if not fields:
                continue

            segment_type = fields[0]

            # PID segment - Patient Identification
            if segment_type == 'PID':
                patient_id = fields[2] if len(fields) > 2 else None
                patient_name = fields[5] if len(fields) > 5 else None

            # OBR segment - Observation Request
            elif segment_type == 'OBR':
                lab_order_id = fields[2] if len(fields) > 2 else None
                if len(fields) > 7:
                    try:
                        report_date = datetime.fromisoformat(fields[7])
                    except Exception:
                        pass

            # OBX segment - Observation Result
            elif segment_type == 'OBX':
                result = self._parse_obx_segment(fields)
                if result:
                    results.append(result)

        return ParsedLabReport(
            patient_name=patient_name,
            patient_id=patient_id,
            lab_order_id=lab_order_id,
            report_date=report_date,
            lab_provider=lab_provider,
            results=results,
            raw_text=content,
            metadata=metadata,
        )

    def _parse_obx_segment(self, fields: list[str]) -> ParsedLabResult | None:
        """Parse OBX (observation) segment."""
        if len(fields) < 6:
            return None

        # OBX segment format:
        # OBX|1|NM|TEST_CODE^TEST_NAME|1|VALUE|UNIT|REF_RANGE|ABNORMAL_FLAG

        test_info = fields[3].split('^')
        test_code = test_info[0] if len(test_info) > 0 else None
        test_name = test_info[1] if len(test_info) > 1 else test_code

        value_str = fields[5] if len(fields) > 5 else ""
        unit = fields[6] if len(fields) > 6 else None
        ref_range_str = fields[7] if len(fields) > 7 else ""
        abnormal_flag = fields[8] if len(fields) > 8 else None

        # Parse reference range
        ref_min, ref_max, ref_text = self.parse_reference_range(ref_range_str)

        # Extract numeric value
        value_numeric = self.extract_numeric_value(value_str)

        # Normalize test name
        normalized_name, test_info_dict = self.normalize_test_name(test_name)

        # Determine abnormality
        is_abnormal = abnormal_flag in ['H', 'L', 'HH', 'LL', 'A'] if abnormal_flag else False

        if not is_abnormal and value_numeric:
            is_abnormal, calc_flag = self.determine_abnormal_flag(
                value_numeric, ref_min, ref_max
            )
            if not abnormal_flag:
                abnormal_flag = calc_flag

        return ParsedLabResult(
            test_name=test_name,
            value=value_str,
            value_numeric=value_numeric,
            unit=unit,
            reference_range_min=ref_min,
            reference_range_max=ref_max,
            reference_range_text=ref_text,
            is_abnormal=is_abnormal,
            abnormal_flag=abnormal_flag,
            test_code=test_code,
            test_category=None,
            notes=None,
        )


class LabParserFactory:
    """Factory for creating appropriate lab parsers."""

    @staticmethod
    def create_parser(file_type: str) -> LabParser:
        """
        Create appropriate parser based on file type.

        Args:
            file_type: 'pdf', 'hl7', or 'text'

        Returns:
            LabParser instance
        """
        if file_type.lower() == 'pdf':
            return PDFLabParser()
        elif file_type.lower() in ['hl7', 'fhir']:
            return HL7LabParser()
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    @staticmethod
    def detect_file_type(content: bytes) -> str:
        """Detect file type from content."""
        # Check for PDF magic bytes
        if content.startswith(b'%PDF'):
            return 'pdf'

        # Check for HL7 segments
        try:
            text = content.decode('utf-8')
            if 'MSH|' in text or 'PID|' in text or 'OBX|' in text:
                return 'hl7'
        except UnicodeDecodeError:
            pass

        return 'text'
