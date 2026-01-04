"""
OCR Service for Document Text Extraction.

Phase 10: Document Scanner & OCR

Uses EasyOCR for multi-language text extraction (Hindi + English).
"""

import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image

logger = logging.getLogger(__name__)


class OCRService:
    """
    OCR service for extracting text from scanned documents.

    Supports Hindi + English and attempts to extract structured data.
    """

    def __init__(self):
        """Initialize OCR service."""
        self.reader = None
        self._initialized = False

    def _initialize_reader(self, languages: list[str] | None = None) -> None:
        """
        Lazy initialization of EasyOCR reader.

        Args:
            languages: List of language codes (e.g., ['en', 'hi'])
        """
        if self._initialized:
            return

        try:
            import easyocr

            if languages is None:
                languages = ["en", "hi"]  # Default: English + Hindi

            logger.info(f"Initializing EasyOCR with languages: {languages}")
            self.reader = easyocr.Reader(languages, gpu=False)
            self._initialized = True
            logger.info("EasyOCR initialized successfully")

        except ImportError:
            logger.error(
                "EasyOCR not installed. Install with: pip install easyocr"
            )
            raise
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
            raise

    def extract_text(
        self,
        image_path: str | Path,
        languages: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Extract text from an image using OCR.

        Args:
            image_path: Path to the image file
            languages: Language codes for OCR (default: ['en', 'hi'])

        Returns:
            Dictionary with:
                - text: Extracted text
                - confidence: Average confidence score (0-100)
                - language: Detected language(s)
                - processing_time: Time taken in seconds
                - raw_results: Raw OCR results with bounding boxes
        """
        start_time = time.time()

        # Initialize reader if not already done
        self._initialize_reader(languages)

        if not self.reader:
            raise RuntimeError("OCR reader not initialized")

        try:
            # Read image
            image_path = Path(image_path)
            if not image_path.exists():
                raise FileNotFoundError(f"Image not found: {image_path}")

            # Verify image can be opened
            try:
                with Image.open(image_path) as img:
                    img.verify()
            except Exception as e:
                raise ValueError(f"Invalid image file: {e}")

            # Run OCR
            logger.info(f"Running OCR on: {image_path}")
            results = self.reader.readtext(str(image_path))

            # Extract text and confidence
            extracted_lines = []
            confidences = []

            for bbox, text, confidence in results:
                extracted_lines.append(text)
                confidences.append(confidence)

            # Combine into full text
            full_text = "\n".join(extracted_lines)

            # Calculate average confidence
            avg_confidence = (
                sum(confidences) / len(confidences) * 100
                if confidences
                else 0.0
            )

            # Detect language (simple heuristic)
            detected_language = self._detect_language(full_text)

            processing_time = time.time() - start_time

            result = {
                "text": full_text,
                "confidence": round(avg_confidence, 2),
                "language": detected_language,
                "processing_time": round(processing_time, 2),
                "raw_results": results,
            }

            logger.info(
                f"OCR completed in {processing_time:.2f}s "
                f"with {avg_confidence:.1f}% confidence"
            )

            return result

        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            raise

    def _detect_language(self, text: str) -> str:
        """
        Simple language detection based on character ranges.

        Args:
            text: Text to analyze

        Returns:
            Detected language(s) as comma-separated string
        """
        if not text:
            return "unknown"

        # Check for Devanagari script (Hindi)
        has_hindi = bool(re.search(r"[\u0900-\u097F]", text))

        # Check for English (ASCII letters)
        has_english = bool(re.search(r"[a-zA-Z]", text))

        if has_hindi and has_english:
            return "hi,en"
        elif has_hindi:
            return "hi"
        elif has_english:
            return "en"
        else:
            return "unknown"

    def extract_structured_data(self, text: str) -> dict[str, Any]:
        """
        Attempt to extract structured data from OCR text.

        This uses regex patterns to find common medical document fields.

        Args:
            text: Extracted text from OCR

        Returns:
            Dictionary with extracted structured data
        """
        if not text:
            return {}

        data: dict[str, Any] = {}

        # Patient name patterns
        name_patterns = [
            r"(?:Patient|Name|Patient Name)[\s:]*([A-Z][a-z]+(?: [A-Z][a-z]+)*)",
            r"(?:नाम|रोगी का नाम)[\s:]*([^\n]+)",
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["patient_name"] = match.group(1).strip()
                break

        # Date patterns (multiple formats)
        date_patterns = [
            r"(?:Date|Dated|Date of Test|Report Date)[\s:]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
            r"(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                data["date"] = match.group(1).strip()
                break

        # Age pattern
        age_match = re.search(r"(?:Age|Age:)[\s]*(\d+)", text, re.IGNORECASE)
        if age_match:
            data["age"] = int(age_match.group(1))

        # Gender pattern
        gender_match = re.search(
            r"(?:Gender|Sex)[\s:]*([MmFfOo]|Male|Female|Other)",
            text,
            re.IGNORECASE,
        )
        if gender_match:
            gender_value = gender_match.group(1).strip().upper()
            if gender_value.startswith("M"):
                data["gender"] = "M"
            elif gender_value.startswith("F"):
                data["gender"] = "F"
            else:
                data["gender"] = "O"

        # Phone number pattern (Indian)
        phone_match = re.search(
            r"(?:Phone|Mobile|Contact)[\s:]*([6-9]\d{9})",
            text,
            re.IGNORECASE,
        )
        if phone_match:
            data["phone"] = phone_match.group(1)

        # Lab test values (generic pattern)
        # Format: Test Name: Value Unit
        test_pattern = r"([A-Za-z\s]+)[\s:]+(\d+\.?\d*)\s*([a-zA-Z/%]+)?"
        test_matches = re.findall(test_pattern, text)
        if test_matches:
            tests = []
            for test_name, value, unit in test_matches:
                test_name = test_name.strip()
                # Filter out common false positives
                if len(test_name) > 3 and not test_name.lower().startswith(
                    ("date", "age", "phone", "page")
                ):
                    tests.append(
                        {
                            "name": test_name,
                            "value": value,
                            "unit": unit.strip() if unit else "",
                        }
                    )
            if tests:
                data["lab_tests"] = tests[:10]  # Limit to 10 tests

        # Doctor name pattern
        doctor_patterns = [
            r"(?:Dr\.|Doctor)[\s]*([A-Z][a-z]+(?: [A-Z][a-z]+)*)",
            r"डॉ\.?[\s]*([^\n]+)",
        ]
        for pattern in doctor_patterns:
            match = re.search(pattern, text)
            if match:
                data["doctor_name"] = match.group(1).strip()
                break

        # Diagnosis pattern
        diagnosis_match = re.search(
            r"(?:Diagnosis|Impression)[\s:]*([^\n]+)",
            text,
            re.IGNORECASE,
        )
        if diagnosis_match:
            data["diagnosis"] = diagnosis_match.group(1).strip()

        # Medications/Prescriptions
        med_pattern = r"(?:Rx|Medicine|Medication)[\s:]*([^\n]+)"
        med_matches = re.findall(med_pattern, text, re.IGNORECASE)
        if med_matches:
            data["medications"] = [m.strip() for m in med_matches]

        return data

    def process_document(
        self,
        image_path: str | Path,
        languages: list[str] | None = None,
        extract_structured: bool = True,
    ) -> dict[str, Any]:
        """
        Complete document processing: OCR + structured data extraction.

        Args:
            image_path: Path to the image file
            languages: Language codes for OCR
            extract_structured: Whether to extract structured data

        Returns:
            Dictionary with:
                - ocr_text: Extracted text
                - ocr_confidence: Confidence score
                - ocr_language: Detected language
                - extracted_data: Structured data (if enabled)
                - processing_time: Total time taken
        """
        # Run OCR
        ocr_result = self.extract_text(image_path, languages)

        result = {
            "ocr_text": ocr_result["text"],
            "ocr_confidence": ocr_result["confidence"],
            "ocr_language": ocr_result["language"],
            "processing_time": ocr_result["processing_time"],
        }

        # Extract structured data if requested
        if extract_structured and ocr_result["text"]:
            start_time = time.time()
            structured_data = self.extract_structured_data(ocr_result["text"])
            result["extracted_data"] = structured_data
            result["processing_time"] += time.time() - start_time

        return result


# Global OCR service instance
_ocr_service: OCRService | None = None


def get_ocr_service() -> OCRService:
    """
    Get the global OCR service instance (singleton pattern).

    Returns:
        OCR service instance
    """
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service
