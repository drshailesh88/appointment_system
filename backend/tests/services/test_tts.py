"""
Tests for Chatterbox TTS service.
"""
import io
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import wave

from app.voice.tts import (
    ChatterboxTTS,
    TextToSpeech,
    TextToSpeechAsync,
    VOICE_RESPONSES,
    PARALINGUISTIC_TAGS,
    SUPPORTED_LANGUAGES,
    add_expression,
)


class TestChatterboxTTS:
    """Tests for ChatterboxTTS class."""

    def test_initialization_cpu(self):
        """Test TTS initialization with CPU."""
        with patch("torch.cuda.is_available", return_value=False):
            tts = ChatterboxTTS()
            assert tts.device == "cpu"
            assert tts._model is None
            assert tts._model_loaded is False

    def test_initialization_with_voice_sample(self, tmp_path):
        """Test TTS initialization with voice sample path."""
        voice_file = tmp_path / "voice.wav"
        voice_file.touch()

        tts = ChatterboxTTS(voice_sample_path=voice_file)
        assert tts.voice_sample_path == voice_file

    @patch("app.voice.tts.ChatterboxTTS._load_model")
    def test_synthesize_fallback_when_no_model(self, mock_load):
        """Test fallback when Chatterbox model not available."""
        tts = ChatterboxTTS()
        tts._model = None
        tts._model_loaded = True

        result = tts.synthesize("Hello")

        # Should return audio bytes (from fallback)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_generate_silent_audio(self):
        """Test silent audio generation."""
        tts = ChatterboxTTS()
        result = tts._generate_silent_audio(0.5)

        assert isinstance(result, bytes)
        assert len(result) > 0

        # Verify it's valid WAV
        buffer = io.BytesIO(result)
        with wave.open(buffer, "rb") as wav:
            assert wav.getnchannels() == 1
            assert wav.getsampwidth() == 2
            assert wav.getframerate() == 24000

    def test_set_voice_sample(self, tmp_path):
        """Test setting voice sample."""
        voice_file = tmp_path / "voice.wav"
        voice_file.touch()

        tts = ChatterboxTTS()
        tts.set_voice_sample(voice_file)
        assert tts.voice_sample_path == voice_file

    def test_set_voice_sample_not_found(self):
        """Test error when voice sample not found."""
        tts = ChatterboxTTS()
        with pytest.raises(FileNotFoundError):
            tts.set_voice_sample(Path("/nonexistent/voice.wav"))

    def test_clone_voice_from_bytes(self, tmp_path):
        """Test saving voice sample from bytes."""
        with patch.object(Path, "home", return_value=tmp_path):
            tts = ChatterboxTTS()

            # Create simple WAV bytes
            buffer = io.BytesIO()
            with wave.open(buffer, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(24000)
                wav.writeframes(b"\x00\x00" * 24000)

            voice_bytes = buffer.getvalue()
            result_path = tts.clone_voice_from_bytes(voice_bytes)

            assert result_path.exists()
            assert tts.voice_sample_path == result_path


class TestTextToSpeech:
    """Tests for backward-compatible TextToSpeech class."""

    def test_legacy_interface(self):
        """Test legacy interface compatibility."""
        tts = TextToSpeech(voice="en_IN")
        assert tts.voice == "en_IN"
        assert isinstance(tts, ChatterboxTTS)


class TestTextToSpeechAsync:
    """Tests for async TTS wrapper."""

    def test_initialization(self):
        """Test async TTS initialization."""
        tts = TextToSpeechAsync(voice="hi")
        assert tts.voice == "hi"
        assert isinstance(tts.tts, ChatterboxTTS)

    @pytest.mark.asyncio
    async def test_synthesize_async(self):
        """Test async synthesis."""
        tts = TextToSpeechAsync()

        with patch.object(tts.tts, "synthesize", return_value=b"audio_data"):
            result = await tts.synthesize("Hello")
            assert result == b"audio_data"


class TestVoiceResponses:
    """Tests for pre-defined voice responses."""

    def test_greeting_exists(self):
        """Test greeting responses exist."""
        assert "greeting" in VOICE_RESPONSES
        assert "en" in VOICE_RESPONSES["greeting"]
        assert "hi" in VOICE_RESPONSES["greeting"]

    def test_all_responses_have_en_hi(self):
        """Test all responses have English and Hindi."""
        for key, responses in VOICE_RESPONSES.items():
            assert "en" in responses, f"Missing English for {key}"
            assert "hi" in responses, f"Missing Hindi for {key}"

    def test_expressive_responses(self):
        """Test expressive responses with paralinguistic tags."""
        assert "booking_success" in VOICE_RESPONSES
        assert "[chuckle]" in VOICE_RESPONSES["booking_success"]["en"]

        assert "no_slots" in VOICE_RESPONSES
        assert "[sigh]" in VOICE_RESPONSES["no_slots"]["en"]


class TestParalinguisticTags:
    """Tests for paralinguistic tag support."""

    def test_supported_tags(self):
        """Test all expected tags are supported."""
        expected_tags = ["[laugh]", "[cough]", "[sigh]", "[gasp]", "[chuckle]"]
        for tag in expected_tags:
            assert tag in PARALINGUISTIC_TAGS

    def test_add_expression(self):
        """Test adding expression to text."""
        result = add_expression("Hello", "[laugh]")
        assert result == "[laugh] Hello"

    def test_add_unknown_expression(self):
        """Test adding unknown expression (should return original)."""
        result = add_expression("Hello", "[unknown]")
        assert result == "Hello"


class TestSupportedLanguages:
    """Tests for language support."""

    def test_indian_languages(self):
        """Test Indian language support."""
        indian_languages = ["hi", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa"]
        for lang in indian_languages:
            assert lang in SUPPORTED_LANGUAGES

    def test_english_supported(self):
        """Test English is supported."""
        assert "en" in SUPPORTED_LANGUAGES
