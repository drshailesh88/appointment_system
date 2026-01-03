"""
Text-to-Speech using Piper.

Piper is a fast, local neural text-to-speech system that works entirely offline.
It supports multiple languages and voices with natural-sounding output.
"""

import io
import logging
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Voice models for Indian languages
VOICE_MODELS = {
    "en_IN": "en_IN-cmu_indic_hin_ab-medium",  # Indian English
    "en_US": "en_US-lessac-medium",  # American English
    "en_GB": "en_GB-cori-medium",  # British English
    "hi_IN": "hi_IN-swara-medium",  # Hindi
}

DEFAULT_VOICE = "en_IN"


class TextToSpeech:
    """
    Text-to-Speech synthesis using Piper.

    Supports:
    - Indian English accent
    - Hindi
    - Multiple voices per language
    - Adjustable speed and pitch
    """

    def __init__(
        self,
        voice: str = DEFAULT_VOICE,
        model_path: Optional[Path] = None,
    ):
        """
        Initialize TTS engine.

        Args:
            voice: Voice identifier (e.g., "en_IN", "hi_IN")
            model_path: Path to Piper models directory
        """
        self.voice = voice
        self.model_path = model_path or Path.home() / ".local" / "share" / "piper"
        self._piper_path = None

    def _get_piper_path(self) -> Optional[str]:
        """Find Piper executable."""
        if self._piper_path:
            return self._piper_path

        # Check common locations
        locations = [
            "/usr/bin/piper",
            "/usr/local/bin/piper",
            str(Path.home() / ".local" / "bin" / "piper"),
        ]

        for loc in locations:
            if Path(loc).exists():
                self._piper_path = loc
                return loc

        # Try to find in PATH
        try:
            result = subprocess.run(
                ["which", "piper"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                self._piper_path = result.stdout.strip()
                return self._piper_path
        except Exception:
            pass

        return None

    def _get_model_file(self, voice: str) -> Optional[Path]:
        """Get the model file for a voice."""
        model_name = VOICE_MODELS.get(voice, VOICE_MODELS[DEFAULT_VOICE])
        model_file = self.model_path / f"{model_name}.onnx"

        if model_file.exists():
            return model_file

        # Try to download model
        logger.warning(f"Voice model not found: {model_file}")
        return None

    def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
        output_format: str = "wav",
    ) -> bytes:
        """
        Synthesize speech from text.

        Args:
            text: Text to speak
            voice: Voice to use (defaults to instance voice)
            speed: Speech speed multiplier (0.5 = half speed, 2.0 = double speed)
            output_format: Output audio format ("wav" or "raw")

        Returns:
            Audio data as bytes
        """
        voice = voice or self.voice

        # Try Piper first
        piper_path = self._get_piper_path()
        model_file = self._get_model_file(voice)

        if piper_path and model_file:
            return self._synthesize_piper(text, model_file, speed)

        # Fallback to pyttsx3 (offline) or gTTS (online)
        return self._synthesize_fallback(text, speed)

    def _synthesize_piper(
        self,
        text: str,
        model_file: Path,
        speed: float,
    ) -> bytes:
        """Synthesize using Piper."""
        piper_path = self._get_piper_path()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            output_file = f.name

        try:
            # Run Piper
            cmd = [
                piper_path,
                "--model", str(model_file),
                "--output_file", output_file,
                "--length_scale", str(1.0 / speed),  # Inverse for speed
            ]

            process = subprocess.run(
                cmd,
                input=text,
                capture_output=True,
                text=True,
            )

            if process.returncode != 0:
                logger.error(f"Piper error: {process.stderr}")
                raise RuntimeError(f"Piper synthesis failed: {process.stderr}")

            # Read output file
            with open(output_file, "rb") as f:
                return f.read()

        finally:
            # Cleanup
            Path(output_file).unlink(missing_ok=True)

    def _synthesize_fallback(self, text: str, speed: float) -> bytes:
        """Fallback TTS using pyttsx3 or simple tone."""
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
        """Generate silent WAV audio."""
        sample_rate = 22050
        num_samples = int(sample_rate * duration)

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(b"\x00\x00" * num_samples)

        return buffer.getvalue()

    def synthesize_ssml(self, ssml: str, voice: Optional[str] = None) -> bytes:
        """
        Synthesize from SSML (Speech Synthesis Markup Language).

        Note: Piper has limited SSML support. Complex SSML is converted to plain text.
        """
        # Strip SSML tags for basic support
        import re
        text = re.sub(r"<[^>]+>", "", ssml)
        return self.synthesize(text, voice)


class TextToSpeechAsync:
    """Async wrapper for Text-to-Speech."""

    def __init__(self, voice: str = DEFAULT_VOICE):
        self.tts = TextToSpeech(voice)

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> bytes:
        """Async synthesize (runs in thread pool)."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.tts.synthesize(text, voice, speed),
        )


# Pre-defined responses for common scenarios
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
}
