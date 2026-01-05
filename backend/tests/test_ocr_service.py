"""
Tests for OCR service.

Phase 10: Document Scanner & OCR
"""

import os
import tempfile
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from app.services.ocr import OCRService, get_ocr_service


@pytest.fixture
def ocr_service():
    """Get OCR service instance."""
    return OCRService()


@pytest.fixture
def sample_image():
    """Create a sample image with text for testing."""
    # Create a temporary image file with text
    img = Image.new("RGB", (800, 600), color="white")
    draw = ImageDraw.Draw(img)

    # Add some text
    text = "Patient Name: John Doe\nDate: 2026-01-02\nHemoglobin: 14.5 g/dL"

    # Try to use a font, fall back to default if not available
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except (OSError, IOError):
        font = ImageFont.load_default()

    draw.text((50, 50), text, fill="black", font=font)

    # Save to temporary file
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        img.save(tmp.name)
        yield tmp.name

    # Cleanup
    try:
        os.unlink(tmp.name)
    except OSError:
        pass


@pytest.mark.asyncio



async def test_ocr_service_initialization(ocr_service):
    """Test OCR service can be initialized."""
    assert ocr_service is not None
    assert ocr_service._initialized is False


@pytest.mark.asyncio



async def test_get_ocr_service_singleton():
    """Test that get_ocr_service returns singleton instance."""
    service1 = get_ocr_service()
    service2 = get_ocr_service()
    assert service1 is service2


@pytest.mark.asyncio



async def test_detect_language_english(ocr_service):
    """Test language detection for English text."""
    text = "This is a test in English"
    language = ocr_service._detect_language(text)
    assert "en" in language


@pytest.mark.asyncio



async def test_detect_language_hindi(ocr_service):
    """Test language detection for Hindi text."""
    text = "यह हिंदी में एक परीक्षण है"
    language = ocr_service._detect_language(text)
    assert "hi" in language


@pytest.mark.asyncio



async def test_detect_language_mixed(ocr_service):
    """Test language detection for mixed Hindi + English text."""
    text = "Patient Name: जॉन डो"
    language = ocr_service._detect_language(text)
    assert "hi" in language and "en" in language


@pytest.mark.asyncio



async def test_detect_language_empty(ocr_service):
    """Test language detection for empty text."""
    language = ocr_service._detect_language("")
    assert language == "unknown"


@pytest.mark.asyncio



async def test_extract_structured_data_patient_name(ocr_service):
    """Test extraction of patient name."""
    text = "Patient Name: John Doe\nAge: 45\nGender: M"
    data = ocr_service.extract_structured_data(text)

    assert "patient_name" in data
    assert "John Doe" in data["patient_name"]


@pytest.mark.asyncio



async def test_extract_structured_data_age(ocr_service):
    """Test extraction of age."""
    text = "Patient: John Doe\nAge: 45"
    data = ocr_service.extract_structured_data(text)

    assert "age" in data
    assert data["age"] == 45


@pytest.mark.asyncio



async def test_extract_structured_data_gender(ocr_service):
    """Test extraction of gender."""
    text = "Gender: Male"
    data = ocr_service.extract_structured_data(text)

    assert "gender" in data
    assert data["gender"] == "M"


@pytest.mark.asyncio



async def test_extract_structured_data_date(ocr_service):
    """Test extraction of date."""
    text = "Date: 02/01/2026\nPatient: John"
    data = ocr_service.extract_structured_data(text)

    assert "date" in data
    assert "2026" in data["date"]


@pytest.mark.asyncio



async def test_extract_structured_data_phone(ocr_service):
    """Test extraction of Indian phone number."""
    text = "Contact: 9876543210"
    data = ocr_service.extract_structured_data(text)

    assert "phone" in data
    assert data["phone"] == "9876543210"


@pytest.mark.asyncio



async def test_extract_structured_data_lab_tests(ocr_service):
    """Test extraction of lab test values."""
    text = """
    Lab Report
    Hemoglobin: 14.5 g/dL
    WBC Count: 8000 cells/uL
    Blood Sugar: 95 mg/dL
    """
    data = ocr_service.extract_structured_data(text)

    assert "lab_tests" in data
    assert len(data["lab_tests"]) > 0

    # Check if we extracted some test values
    test_names = [test["name"].lower() for test in data["lab_tests"]]
    assert any("hemoglobin" in name for name in test_names)


@pytest.mark.asyncio



async def test_extract_structured_data_doctor(ocr_service):
    """Test extraction of doctor name."""
    text = "Dr. Sharma\nPatient: John Doe"
    data = ocr_service.extract_structured_data(text)

    assert "doctor_name" in data
    assert "Sharma" in data["doctor_name"]


@pytest.mark.asyncio



async def test_extract_structured_data_empty(ocr_service):
    """Test extraction from empty text."""
    data = ocr_service.extract_structured_data("")
    assert data == {}


@pytest.mark.asyncio



async def test_extract_structured_data_hindi(ocr_service):
    """Test extraction from Hindi text."""
    text = "नाम: जॉन डो\nडॉ. शर्मा"
    data = ocr_service.extract_structured_data(text)

    # Should extract some data even from Hindi
    assert isinstance(data, dict)


@pytest.mark.skipif(
    os.getenv("SKIP_OCR_TESTS") == "1",
    reason="OCR tests skipped (EasyOCR not installed or too slow)",
)
@pytest.mark.asyncio

async def test_extract_text_from_image(ocr_service, sample_image):
    """Test OCR text extraction from an image."""
    result = ocr_service.extract_text(sample_image)

    assert "text" in result
    assert "confidence" in result
    assert "language" in result
    assert "processing_time" in result

    # Text should contain something (may not be perfect)
    assert len(result["text"]) > 0

    # Confidence should be between 0 and 100
    assert 0 <= result["confidence"] <= 100


@pytest.mark.skipif(
    os.getenv("SKIP_OCR_TESTS") == "1",
    reason="OCR tests skipped (EasyOCR not installed or too slow)",
)
@pytest.mark.asyncio

async def test_process_document(ocr_service, sample_image):
    """Test complete document processing."""
    result = ocr_service.process_document(
        sample_image,
        languages=["en"],
        extract_structured=True,
    )

    assert "ocr_text" in result
    assert "ocr_confidence" in result
    assert "ocr_language" in result
    assert "extracted_data" in result
    assert "processing_time" in result


@pytest.mark.asyncio



async def test_extract_text_invalid_file(ocr_service):
    """Test OCR with invalid file path."""
    with pytest.raises(FileNotFoundError):
        ocr_service.extract_text("/nonexistent/file.jpg")


@pytest.mark.asyncio



async def test_extract_text_invalid_image(ocr_service):
    """Test OCR with invalid image file."""
    # Create a text file pretending to be an image
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(b"This is not an image")
        tmp_path = tmp.name

    try:
        with pytest.raises(ValueError):
            ocr_service.extract_text(tmp_path)
    finally:
        os.unlink(tmp_path)
