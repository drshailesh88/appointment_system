"""
Text-to-Speech using Chatterbox.

Chatterbox is a state-of-the-art zero-shot voice cloning TTS system that:
- Works entirely offline
- Supports 23+ languages including Hindi
- Enables voice cloning from short audio samples
- Supports paralinguistic tags: [laugh], [cough], [sigh], [gasp], [chuckle]
- Provides emotion control via exaggeration parameter

Reference: https://github.com/resemble-ai/chatterbox
"""

from __future__ import annotations

import io
import logging
import tempfile
import wave
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import torch

# Optional PyTorch import - not required for tests
try:
    import torch
    import torchaudio
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None
    torchaudio = None

logger = logging.getLogger(__name__)

# Supported languages (subset - Chatterbox supports 23+)
SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "bn": "Bengali",
    "mr": "Marathi",
    "gu": "Gujarati",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
}

# Paralinguistic tags supported by Chatterbox
PARALINGUISTIC_TAGS = ["[laugh]", "[cough]", "[sigh]", "[gasp]", "[chuckle]", "[clear_throat]"]

DEFAULT_VOICE = "en"
DEFAULT_SAMPLE_RATE = 24000


class ChatterboxTTS:
    """
    Text-to-Speech synthesis using Chatterbox.

    Features:
    - Zero-shot voice cloning from 3-10 second audio sample
    - 23+ language support including Indian languages
    - Paralinguistic expressions ([laugh], [cough], etc.)
    - Emotion/exaggeration control (0.0-1.0)
    - Fully offline operation
    """

    def __init__(
        self,
        device: Optional[str] = None,
        voice_sample_path: Optional[Path] = None,
    ):
        """
        Initialize Chatterbox TTS engine.

        Args:
            device: "cuda" or "cpu" (auto-detected if None)
            voice_sample_path: Path to reference voice audio for cloning
        """
        if TORCH_AVAILABLE and torch is not None:
            self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = device or "cpu"
        self.voice_sample_path = voice_sample_path
        self._model = None
        self._model_loaded = False

    def _load_model(self):
        """Lazy load the Chatterbox model."""
        if self._model_loaded:
            return

        if not TORCH_AVAILABLE:
            logger.warning(
                "PyTorch is not installed. TTS will use fallback mode. "
                "For full TTS features, install with: pip install torch torchaudio"
            )
            self._model = None
            self._model_loaded = True
            return

        try:
            from chatterbox.tts import ChatterboxTTS as CBModel

            logger.info(f"Loading Chatterbox TTS model on {self.device}...")
            self._model = CBModel.from_pretrained(device=self.device)
            self._model_loaded = True
            logger.info("Chatterbox TTS model loaded successfully")

        except ImportError:
            logger.warning("Chatterbox not installed. Using fallback TTS.")
            self._model = None
            self._model_loaded = True

        except Exception as e:
            logger.error(f"Error loading Chatterbox: {e}")
            self._model = None
            self._model_loaded = True

    def synthesize(
        self,
        text: str,
        language: str = "en",
        voice_sample: Optional[bytes] = None,
        voice_sample_path: Optional[Path] = None,
        exaggeration: float = 0.5,
        speed: float = 1.0,
    ) -> bytes:
        """
        Synthesize speech from text.

        Args:
            text: Text to speak (can include paralinguistic tags like [laugh])
            language: Language code (e.g., "en", "hi", "ta")
            voice_sample: Audio bytes for voice cloning
            voice_sample_path: Path to voice sample audio file
            exaggeration: Emotion intensity (0.0 = neutral, 1.0 = very expressive)
            speed: Speech speed multiplier (0.5 = slow, 2.0 = fast)

        Returns:
            Audio data as WAV bytes
        """
        self._load_model()

        if self._model is None:
            return self._synthesize_fallback(text, speed)

        try:
            # Determine voice sample to use
            audio_prompt = voice_sample_path or self.voice_sample_path

            # If bytes provided, save to temp file
            temp_voice_file = None
            if voice_sample:
                temp_voice_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                temp_voice_file.write(voice_sample)
                temp_voice_file.close()
                audio_prompt = Path(temp_voice_file.name)

            # Generate speech
            if audio_prompt and Path(audio_prompt).exists():
                # Voice cloning mode
                wav_tensor = self._model.generate(
                    text,
                    audio_prompt_path=str(audio_prompt),
                    exaggeration=exaggeration,
                )
            else:
                # Default voice mode
                wav_tensor = self._model.generate(
                    text,
                    exaggeration=exaggeration,
                )

            # Cleanup temp file
            if temp_voice_file:
                Path(temp_voice_file.name).unlink(missing_ok=True)

            # Convert tensor to WAV bytes
            return self._tensor_to_wav(wav_tensor, speed)

        except Exception as e:
            logger.error(f"Chatterbox synthesis error: {e}")
            return self._synthesize_fallback(text, speed)

    def _tensor_to_wav(self, wav_tensor, speed: float = 1.0) -> bytes:
        """Convert PyTorch tensor to WAV bytes."""
        if not TORCH_AVAILABLE or torchaudio is None:
            raise ImportError(
                "PyTorch and torchaudio are required for TTS tensor conversion. "
                "Install with: pip install torch torchaudio"
            )

        # Adjust sample rate for speed
        sample_rate = int(DEFAULT_SAMPLE_RATE * speed)

        buffer = io.BytesIO()
        torchaudio.save(
            buffer,
            wav_tensor.cpu(),
            sample_rate,
            format="wav",
        )
        buffer.seek(0)
        return buffer.read()

    def _synthesize_fallback(self, text: str, speed: float) -> bytes:
        """Fallback TTS using pyttsx3."""
        try:
            import pyttsx3

            engine = pyttsx3.init()
            engine.setProperty("rate", int(150 * speed))

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                output_file = f.name

            engine.save_to_file(text, output_file)
            engine.runAndWait()

            with open(output_file, "rb") as f:
                audio_data = f.read()

            Path(output_file).unlink(missing_ok=True)
            return audio_data

        except ImportError:
            logger.warning("pyttsx3 not available, using silent audio")
            return self._generate_silent_audio(len(text) * 0.1)

    def _generate_silent_audio(self, duration: float) -> bytes:
        """Generate silent WAV audio as last resort."""
        sample_rate = DEFAULT_SAMPLE_RATE
        num_samples = int(sample_rate * duration)

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(b"\x00\x00" * num_samples)

        return buffer.getvalue()

    def set_voice_sample(self, voice_sample_path: Path):
        """
        Set the reference voice for cloning.

        Args:
            voice_sample_path: Path to 3-10 second audio sample
        """
        if not voice_sample_path.exists():
            raise FileNotFoundError(f"Voice sample not found: {voice_sample_path}")
        self.voice_sample_path = voice_sample_path
        logger.info(f"Voice sample set: {voice_sample_path}")

    def clone_voice_from_bytes(self, audio_bytes: bytes) -> Path:
        """
        Save voice sample from bytes for cloning.

        Args:
            audio_bytes: WAV audio bytes (3-10 seconds recommended)

        Returns:
            Path to saved voice sample
        """
        voice_dir = Path.home() / ".docassist" / "voices"
        voice_dir.mkdir(parents=True, exist_ok=True)

        import hashlib
        voice_hash = hashlib.md5(audio_bytes).hexdigest()[:8]
        voice_path = voice_dir / f"voice_{voice_hash}.wav"

        voice_path.write_bytes(audio_bytes)
        self.voice_sample_path = voice_path
        logger.info(f"Voice sample saved: {voice_path}")
        return voice_path


class TextToSpeech(ChatterboxTTS):
    """
    Legacy alias for backward compatibility.
    Use ChatterboxTTS for new code.
    """

    def __init__(
        self,
        voice: str = DEFAULT_VOICE,
        model_path: Optional[Path] = None,
    ):
        """
        Initialize TTS with legacy interface.

        Args:
            voice: Language/voice identifier
            model_path: Ignored (for Piper compatibility)
        """
        super().__init__()
        self.voice = voice


class TextToSpeechAsync:
    """Async wrapper for Text-to-Speech."""

    def __init__(
        self,
        voice: str = DEFAULT_VOICE,
        voice_sample_path: Optional[Path] = None,
    ):
        """
        Initialize async TTS.

        Args:
            voice: Language/voice identifier
            voice_sample_path: Optional path to voice sample for cloning
        """
        self.tts = ChatterboxTTS(voice_sample_path=voice_sample_path)
        self.voice = voice

    async def synthesize(
        self,
        text: str,
        language: Optional[str] = None,
        voice_sample: Optional[bytes] = None,
        exaggeration: float = 0.5,
        speed: float = 1.0,
    ) -> bytes:
        """
        Async synthesize (runs in thread pool).

        Args:
            text: Text to speak
            language: Language code (defaults to instance voice)
            voice_sample: Optional audio bytes for voice cloning
            exaggeration: Emotion intensity (0.0-1.0)
            speed: Speech speed multiplier

        Returns:
            Audio data as WAV bytes
        """
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.tts.synthesize(
                text,
                language=language or self.voice,
                voice_sample=voice_sample,
                exaggeration=exaggeration,
                speed=speed,
            ),
        )

    def set_voice_sample(self, voice_sample_path: Path):
        """Set voice sample for cloning."""
        self.tts.set_voice_sample(voice_sample_path)


# Pre-defined responses for common scenarios (multilingual)
VOICE_RESPONSES = {
    "greeting": {
        "en": "Hello! Welcome to DocAssist. How can I help you today?",
        "hi": "नमस्ते! डॉकअसिस्ट में आपका स्वागत है। मैं आपकी कैसे मदद कर सकता हूं?",
    },
    "ask_doctor": {
        "en": "Which doctor would you like to book an appointment with?",
        "hi": "आप किस डॉक्टर के साथ अपॉइंटमेंट बुक करना चाहते हैं?",
    },
    "ask_date": {
        "en": "What date would you prefer for your appointment?",
        "hi": "आप अपनी अपॉइंटमेंट के लिए कौन सी तारीख पसंद करेंगे?",
    },
    "ask_time": {
        "en": "What time works best for you?",
        "hi": "आपके लिए कौन सा समय सबसे अच्छा रहेगा?",
    },
    "confirm": {
        "en": "I have booked your appointment with {doctor} on {date} at {time}. Would you like me to send a confirmation?",
        "hi": "{doctor} के साथ {date} को {time} पर आपकी अपॉइंटमेंट बुक कर दी गई है। क्या आप चाहते हैं कि मैं कन्फर्मेशन भेजूं?",
    },
    "goodbye": {
        "en": "Thank you for using DocAssist. Take care and stay healthy!",
        "hi": "डॉकअसिस्ट का उपयोग करने के लिए धन्यवाद। अपना ख्याल रखें और स्वस्थ रहें!",
    },
    # Expressive responses using paralinguistic tags
    "booking_success": {
        "en": "[chuckle] Great news! Your appointment has been booked successfully!",
        "hi": "[chuckle] बहुत अच्छा! आपकी अपॉइंटमेंट सफलतापूर्वक बुक हो गई है!",
    },
    "no_slots": {
        "en": "[sigh] I'm sorry, there are no available slots on that date. Would you like to try another day?",
        "hi": "[sigh] मुझे खेद है, उस तारीख पर कोई स्लॉट उपलब्ध नहीं है। क्या आप कोई और दिन आज़माना चाहेंगे?",
    },
}


def add_expression(text: str, expression: str = "[chuckle]") -> str:
    """
    Add paralinguistic expression to text.

    Args:
        text: Original text
        expression: Paralinguistic tag to add

    Returns:
        Text with expression prepended
    """
    if expression not in PARALINGUISTIC_TAGS:
        logger.warning(f"Unknown expression: {expression}")
        return text
    return f"{expression} {text}"
