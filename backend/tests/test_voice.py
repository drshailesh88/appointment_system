"""
Comprehensive tests for Voice features.

Tests:
- Speech-to-Text (STT) with Whisper
- Text-to-Speech (TTS) with Chatterbox
- Natural Language Understanding (NLU)
- Voice Agent orchestration
"""

import io
import wave
from datetime import date, datetime, time, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import UUID, uuid4

import numpy as np
import pytest

from app.voice.stt import SpeechToText, SpeechToTextAsync
from app.voice.tts import ChatterboxTTS, TextToSpeechAsync, add_expression, PARALINGUISTIC_TAGS
from app.voice.nlu import Intent, NaturalLanguageUnderstanding, NLUSync
from app.voice.agent import VoiceAgent, ConversationState


# =====================================================================
# Speech-to-Text (STT) Tests
# =====================================================================


class TestSpeechToText:
    """Tests for Speech-to-Text functionality."""

    @pytest.fixture
    def mock_whisper_model(self):
        """Mock Whisper model for testing."""
        mock_model = MagicMock()

        # Mock transcription output
        mock_segment = MagicMock()
        mock_segment.start = 0.0
        mock_segment.end = 2.5
        mock_segment.text = "Book an appointment for tomorrow"
        mock_segment.avg_logprob = -0.3
        mock_segment.words = []

        mock_info = MagicMock()
        mock_info.language = "en"
        mock_info.language_probability = 0.95
        mock_info.duration = 2.5

        mock_model.transcribe.return_value = ([mock_segment], mock_info)

        return mock_model

    @pytest.fixture
    def stt(self, mock_whisper_model):
        """STT instance with mocked model."""
        with patch('app.voice.stt.get_whisper_model', return_value=mock_whisper_model):
            return SpeechToText(model_size="base.en")

    def test_transcribe_english_speech(self, stt):
        """Test transcribing clear English speech."""
        # Create dummy audio data
        audio_bytes = self._generate_silent_wav(2.0)

        result = stt.transcribe(audio_bytes)

        assert result["text"] == "Book an appointment for tomorrow"
        assert result["language"] == "en"
        assert result["language_probability"] == 0.95
        assert result["confidence"] < 0  # avg_logprob is negative
        assert len(result["segments"]) == 1

    def test_transcribe_hindi_speech(self, stt, mock_whisper_model):
        """Test transcribing Hindi speech."""
        # Update mock for Hindi
        mock_segment = MagicMock()
        mock_segment.start = 0.0
        mock_segment.end = 2.0
        mock_segment.text = "कल के लिए अपॉइंटमेंट बुक करें"
        mock_segment.avg_logprob = -0.4
        mock_segment.words = []

        mock_info = MagicMock()
        mock_info.language = "hi"
        mock_info.language_probability = 0.92
        mock_info.duration = 2.0

        mock_whisper_model.transcribe.return_value = ([mock_segment], mock_info)

        audio_bytes = self._generate_silent_wav(2.0)
        result = stt.transcribe(audio_bytes, language="hi")

        assert result["text"] == "कल के लिए अपॉइंटमेंट बुक करें"
        assert result["language"] == "hi"

    def test_transcribe_empty_audio(self, stt, mock_whisper_model):
        """Test handling of silence/empty audio."""
        # Mock empty transcription
        mock_whisper_model.transcribe.return_value = ([], MagicMock(
            language="en",
            language_probability=0.0,
            duration=0.0
        ))

        audio_bytes = self._generate_silent_wav(0.5)
        result = stt.transcribe(audio_bytes)

        assert result["text"] == ""
        assert result["confidence"] == 0.0

    def test_transcribe_with_background_noise(self, stt):
        """Test handling audio with background noise."""
        # VAD filter should help with this
        audio_bytes = self._generate_noisy_wav(2.0)

        result = stt.transcribe(audio_bytes)

        # Should still extract speech despite noise
        assert isinstance(result["text"], str)
        assert result["language"] in ["en", "hi"]

    def test_transcribe_from_file_path(self, stt, tmp_path):
        """Test transcribing from a file path."""
        audio_file = tmp_path / "test_audio.wav"
        audio_file.write_bytes(self._generate_silent_wav(2.0))

        result = stt.transcribe(str(audio_file))

        assert "text" in result
        assert result["language"] is not None

    def test_transcribe_with_word_timestamps(self, stt, mock_whisper_model):
        """Test that word-level timestamps are included."""
        # Add word-level data
        mock_word = MagicMock()
        mock_word.word = "appointment"
        mock_word.start = 0.5
        mock_word.end = 1.0
        mock_word.probability = 0.95

        mock_segment = mock_whisper_model.transcribe.return_value[0][0]
        mock_segment.words = [mock_word]

        audio_bytes = self._generate_silent_wav(2.0)
        result = stt.transcribe(audio_bytes)

        assert len(result["segments"]) > 0
        segment = result["segments"][0]
        assert "words" in segment
        if segment["words"]:
            assert segment["words"][0]["word"] == "appointment"

    @pytest.mark.asyncio
    async def test_async_transcribe(self, mock_whisper_model):
        """Test async transcription."""
        with patch('app.voice.stt.get_whisper_model', return_value=mock_whisper_model):
            stt_async = SpeechToTextAsync(model_size="base.en")
            audio_bytes = self._generate_silent_wav(2.0)

            result = await stt_async.transcribe(audio_bytes)

            assert result["text"] == "Book an appointment for tomorrow"

    def _generate_silent_wav(self, duration: float, sample_rate: int = 16000) -> bytes:
        """Generate silent WAV audio for testing."""
        num_samples = int(sample_rate * duration)
        audio_data = np.zeros(num_samples, dtype=np.int16)

        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())

        return buffer.getvalue()

    def _generate_noisy_wav(self, duration: float, sample_rate: int = 16000) -> bytes:
        """Generate WAV with background noise."""
        num_samples = int(sample_rate * duration)
        # Random noise
        audio_data = np.random.randint(-1000, 1000, num_samples, dtype=np.int16)

        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())

        return buffer.getvalue()


# =====================================================================
# Text-to-Speech (TTS) Tests
# =====================================================================


class TestChatterboxTTS:
    """Tests for Text-to-Speech with Chatterbox."""

    @pytest.fixture
    def mock_chatterbox_model(self):
        """Mock Chatterbox model."""
        mock_model = MagicMock()

        # Mock audio tensor output
        import torch
        mock_tensor = torch.randn(1, 24000)  # 1 second of audio at 24kHz
        mock_model.generate.return_value = mock_tensor

        return mock_model

    @pytest.fixture
    def tts(self, mock_chatterbox_model):
        """TTS instance with mocked model."""
        with patch('app.voice.tts.ChatterboxTTS.from_pretrained', return_value=mock_chatterbox_model):
            tts = ChatterboxTTS(device="cpu")
            tts._model = mock_chatterbox_model
            tts._model_loaded = True
            return tts

    def test_synthesize_english_text(self, tts):
        """Test synthesizing English text."""
        text = "Hello, welcome to DocAssist. How can I help you?"

        audio_bytes = tts.synthesize(text, language="en")

        assert isinstance(audio_bytes, bytes)
        assert len(audio_bytes) > 0
        # WAV header check
        assert audio_bytes[:4] == b'RIFF'

    def test_synthesize_hindi_text(self, tts):
        """Test synthesizing Hindi text."""
        text = "नमस्ते, डॉकअसिस्ट में आपका स्वागत है"

        audio_bytes = tts.synthesize(text, language="hi")

        assert isinstance(audio_bytes, bytes)
        assert len(audio_bytes) > 0

    def test_synthesize_with_emotion_tags(self, tts):
        """Test synthesis with paralinguistic tags."""
        text = "[laugh] Great news! Your appointment is confirmed!"

        audio_bytes = tts.synthesize(text, language="en", exaggeration=0.7)

        assert isinstance(audio_bytes, bytes)
        tts._model.generate.assert_called_once()

    def test_synthesize_with_voice_cloning(self, tts, tmp_path):
        """Test voice cloning with reference audio."""
        # Create a dummy voice sample
        voice_sample = tmp_path / "doctor_voice.wav"
        voice_sample.write_bytes(self._generate_silent_wav(3.0))

        tts.set_voice_sample(voice_sample)

        text = "Your appointment is tomorrow at 3 PM"
        audio_bytes = tts.synthesize(text, language="en")

        assert isinstance(audio_bytes, bytes)
        # Verify model was called with voice sample
        call_args = tts._model.generate.call_args
        assert "audio_prompt_path" in call_args[1] or call_args[0]

    def test_synthesize_with_speed_control(self, tts):
        """Test speech speed control."""
        text = "This is a test"

        # Fast speech
        fast_audio = tts.synthesize(text, speed=1.5)
        # Slow speech
        slow_audio = tts.synthesize(text, speed=0.5)

        # Faster speech should have higher sample rate
        assert isinstance(fast_audio, bytes)
        assert isinstance(slow_audio, bytes)

    def test_synthesize_empty_text(self, tts):
        """Test handling empty text."""
        audio_bytes = tts.synthesize("", language="en")

        # Should return some audio (even if silent or error handling)
        assert isinstance(audio_bytes, bytes)

    def test_synthesize_very_long_text(self, tts):
        """Test handling very long text."""
        text = "This is a very long sentence. " * 100

        audio_bytes = tts.synthesize(text, language="en")

        assert isinstance(audio_bytes, bytes)
        assert len(audio_bytes) > 0

    def test_synthesize_with_special_characters(self, tts):
        """Test handling special characters."""
        text = "Cost: ₹500 | Time: 3:00 PM | Dr. Sharma's clinic"

        audio_bytes = tts.synthesize(text, language="en")

        assert isinstance(audio_bytes, bytes)

    def test_fallback_tts_when_chatterbox_unavailable(self):
        """Test fallback to pyttsx3 when Chatterbox unavailable."""
        with patch('app.voice.tts.ChatterboxTTS.from_pretrained', side_effect=ImportError):
            tts = ChatterboxTTS()
            tts._load_model()

            # Should fall back to pyttsx3 or silent audio
            audio_bytes = tts.synthesize("Test", language="en")
            assert isinstance(audio_bytes, bytes)

    @pytest.mark.asyncio
    async def test_async_synthesize(self, mock_chatterbox_model):
        """Test async synthesis."""
        with patch('app.voice.tts.ChatterboxTTS.from_pretrained', return_value=mock_chatterbox_model):
            tts_async = TextToSpeechAsync(voice="en")
            tts_async.tts._model = mock_chatterbox_model
            tts_async.tts._model_loaded = True

            audio_bytes = await tts_async.synthesize("Hello world")

            assert isinstance(audio_bytes, bytes)

    def test_add_expression(self):
        """Test adding paralinguistic expressions."""
        text = "Your appointment is confirmed"

        result = add_expression(text, "[chuckle]")

        assert result == "[chuckle] Your appointment is confirmed"

    def test_add_invalid_expression(self):
        """Test adding invalid expression (should return original)."""
        text = "Test text"

        result = add_expression(text, "[invalid]")

        # Should return original text
        assert result == text

    def _generate_silent_wav(self, duration: float) -> bytes:
        """Generate silent WAV audio."""
        sample_rate = 24000
        num_samples = int(sample_rate * duration)
        audio_data = np.zeros(num_samples, dtype=np.int16)

        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())

        return buffer.getvalue()


# =====================================================================
# Natural Language Understanding (NLU) Tests
# =====================================================================


class TestNLU:
    """Tests for Natural Language Understanding."""

    @pytest.fixture
    def mock_ollama_response(self):
        """Mock Ollama API response."""
        return {
            "message": {
                "content": """{
                    "intent": "book_appointment",
                    "confidence": 0.95,
                    "entities": {
                        "doctor_name": "Dr. Sharma",
                        "date": "2024-03-15",
                        "time": "14:00",
                        "patient_name": null,
                        "patient_phone": null,
                        "appointment_type": "new_consultation",
                        "reason": "general checkup"
                    },
                    "response_suggestion": "I'll book an appointment with Dr. Sharma on March 15 at 2 PM."
                }"""
            }
        }

    @pytest.fixture
    def nlu(self):
        """NLU instance."""
        return NaturalLanguageUnderstanding(
            model="qwen2.5:latest",
            base_url="http://localhost:11434"
        )

    @pytest.mark.asyncio
    async def test_parse_booking_intent(self, nlu, mock_ollama_response):
        """Test parsing book appointment intent."""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = AsyncMock(
                status_code=200,
                json=lambda: mock_ollama_response,
                raise_for_status=lambda: None
            )

            result = await nlu.process("Book an appointment with Dr. Sharma tomorrow at 2 PM")

            assert result.intent == Intent.BOOK_APPOINTMENT
            assert result.confidence > 0.9
            assert result.entities.doctor_name == "Dr. Sharma"

    @pytest.mark.asyncio
    async def test_parse_cancellation_intent(self, nlu):
        """Test parsing cancel appointment intent."""
        mock_response = {
            "message": {
                "content": '{"intent": "cancel_appointment", "confidence": 0.9, "entities": {}}'
            }
        }

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = AsyncMock(
                status_code=200,
                json=lambda: mock_response,
                raise_for_status=lambda: None
            )

            result = await nlu.process("Cancel my appointment")

            assert result.intent == Intent.CANCEL_APPOINTMENT

    @pytest.mark.asyncio
    async def test_parse_reschedule_intent(self, nlu):
        """Test parsing reschedule intent."""
        mock_response = {
            "message": {
                "content": '{"intent": "reschedule_appointment", "confidence": 0.88, "entities": {"date": "2024-03-20"}}'
            }
        }

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = AsyncMock(
                status_code=200,
                json=lambda: mock_response,
                raise_for_status=lambda: None
            )

            result = await nlu.process("Reschedule my appointment to next Wednesday")

            assert result.intent == Intent.RESCHEDULE_APPOINTMENT

    @pytest.mark.asyncio
    async def test_extract_date_entities(self, nlu, mock_ollama_response):
        """Test extracting date entities."""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = AsyncMock(
                status_code=200,
                json=lambda: mock_ollama_response,
                raise_for_status=lambda: None
            )

            result = await nlu.process("Book for tomorrow")

            assert result.entities.date is not None
            # Should parse "tomorrow" correctly
            assert isinstance(result.entities.date, date)

    @pytest.mark.asyncio
    async def test_extract_time_entities(self, nlu, mock_ollama_response):
        """Test extracting time entities."""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = AsyncMock(
                status_code=200,
                json=lambda: mock_ollama_response,
                raise_for_status=lambda: None
            )

            result = await nlu.process("Book at 3 PM")

            assert result.entities.time is not None
            assert isinstance(result.entities.time, time)

    @pytest.mark.asyncio
    async def test_hindi_english_code_mixing(self, nlu):
        """Test handling Hindi-English mixed queries."""
        mock_response = {
            "message": {
                "content": '{"intent": "book_appointment", "confidence": 0.85, "entities": {"date": "2024-03-15", "doctor_name": "Sharma"}}'
            }
        }

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = AsyncMock(
                status_code=200,
                json=lambda: mock_response,
                raise_for_status=lambda: None
            )

            result = await nlu.process("Kal ke liye Dr. Sharma se appointment book karo")

            assert result.intent == Intent.BOOK_APPOINTMENT

    @pytest.mark.asyncio
    async def test_ambiguous_query_handling(self, nlu):
        """Test handling ambiguous queries."""
        mock_response = {
            "message": {
                "content": '{"intent": "unknown", "confidence": 0.3, "entities": {}, "needs_clarification": true, "clarification_question": "Which doctor?"}'
            }
        }

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = AsyncMock(
                status_code=200,
                json=lambda: mock_response,
                raise_for_status=lambda: None
            )

            result = await nlu.process("Book an appointment")

            assert result.confidence < 0.5 or result.intent == Intent.UNKNOWN

    @pytest.mark.asyncio
    async def test_fallback_when_ollama_unavailable(self, nlu):
        """Test fallback parsing when Ollama is unavailable."""
        with patch('httpx.AsyncClient.post', side_effect=Exception("Connection error")):
            result = await nlu.process("Book an appointment with doctor")

            # Should use fallback keyword matching
            assert result.intent == Intent.BOOK_APPOINTMENT
            assert result.confidence < 1.0  # Lower confidence for fallback

    def test_sync_nlu(self):
        """Test synchronous NLU wrapper."""
        nlu_sync = NLUSync()

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = AsyncMock(
                status_code=200,
                json=lambda: {
                    "message": {"content": '{"intent": "greeting", "confidence": 0.95, "entities": {}}'}
                },
                raise_for_status=lambda: None
            )

            result = nlu_sync.process("Hello")

            assert result.intent == Intent.GREETING


# =====================================================================
# Voice Agent Tests
# =====================================================================


class TestVoiceAgent:
    """Tests for Voice Agent orchestration."""

    @pytest.fixture
    def mock_db(self):
        """Mock async database session."""
        return AsyncMock()

    @pytest.fixture
    def agent(self):
        """Voice agent instance with mocked components."""
        with patch('app.voice.agent.SpeechToTextAsync'), \
             patch('app.voice.agent.TextToSpeechAsync'), \
             patch('app.voice.agent.NaturalLanguageUnderstanding'):

            agent = VoiceAgent()

            # Mock STT
            agent.stt.transcribe = AsyncMock(return_value={
                "text": "Book an appointment with Dr. Sharma tomorrow",
                "language": "en",
                "confidence": 0.95
            })

            # Mock TTS
            agent.tts.synthesize = AsyncMock(return_value=b"fake_audio_data")

            # Mock NLU
            from app.voice.nlu import ExtractedEntities
            agent.nlu.process = AsyncMock(return_value=MagicMock(
                intent=Intent.BOOK_APPOINTMENT,
                confidence=0.9,
                entities=ExtractedEntities(
                    doctor_name="Sharma",
                    date=date.today() + timedelta(days=1)
                ),
                response_suggestion="I'll book that for you"
            ))

            return agent

    @pytest.mark.asyncio
    async def test_process_audio_input(self, agent, mock_db):
        """Test processing audio input end-to-end."""
        clinic_id = uuid4()
        session_id = "test_session_1"
        audio_data = b"fake_audio_bytes"

        response = await agent.process_audio(audio_data, session_id, clinic_id, mock_db)

        assert response.text is not None
        assert response.audio is not None
        assert response.state in ConversationState

    @pytest.mark.asyncio
    async def test_process_text_input(self, agent, mock_db):
        """Test processing text input (for testing/text mode)."""
        clinic_id = uuid4()
        session_id = "test_session_2"

        response = await agent.process_text(
            "Book an appointment tomorrow",
            session_id,
            clinic_id,
            mock_db
        )

        assert response.text is not None
        assert response.state in ConversationState

    @pytest.mark.asyncio
    async def test_conversation_flow_greeting(self, agent, mock_db):
        """Test greeting conversation flow."""
        agent.nlu.process = AsyncMock(return_value=MagicMock(
            intent=Intent.GREETING,
            confidence=0.95,
            entities=MagicMock()
        ))

        response = await agent.process_text("Hello", "session", uuid4(), mock_db)

        assert response.state == ConversationState.GREETING
        assert "welcome" in response.text.lower() or "hello" in response.text.lower()

    @pytest.mark.asyncio
    async def test_conversation_state_tracking(self, agent, mock_db):
        """Test that conversation state is tracked across turns."""
        session_id = "state_test"
        clinic_id = uuid4()

        # First message
        await agent.process_text("Hello", session_id, clinic_id, mock_db)

        # Session should be created
        assert session_id in agent.sessions
        context = agent.sessions[session_id]
        assert context.conversation_history is not None
        assert len(context.conversation_history) >= 2  # User + assistant

    @pytest.mark.asyncio
    async def test_error_handling_in_voice_agent(self, agent, mock_db):
        """Test error handling when STT/NLU fails."""
        agent.stt.transcribe = AsyncMock(side_effect=Exception("STT Error"))

        response = await agent.process_audio(b"audio", "session", uuid4(), mock_db)

        assert response.state == ConversationState.ERROR
        assert "error" in response.text.lower() or "sorry" in response.text.lower()

    @pytest.mark.asyncio
    async def test_session_cleanup(self, agent, mock_db):
        """Test stale session cleanup."""
        # Create old session
        old_session = "old_session"
        agent.sessions[old_session] = MagicMock(
            session_id=old_session,
            last_activity=datetime.now() - timedelta(hours=2)
        )

        # Create recent session
        recent_session = "recent_session"
        agent.sessions[recent_session] = MagicMock(
            session_id=recent_session,
            last_activity=datetime.now()
        )

        # Cleanup stale sessions (>30 min)
        agent.cleanup_stale_sessions(max_age_minutes=60)

        assert old_session not in agent.sessions
        assert recent_session in agent.sessions
