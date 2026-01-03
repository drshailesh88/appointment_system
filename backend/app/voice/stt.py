"""
Speech-to-Text using faster-whisper.

faster-whisper is a reimplementation of OpenAI's Whisper model using CTranslate2,
which makes it 4x faster with less memory usage.
"""

import io
import logging
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Lazy import to avoid loading if not used
_whisper_model = None


def get_whisper_model(model_size: str = "base.en"):
    """Get or create the Whisper model (lazy loading)."""
    global _whisper_model

    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel

            # Use CPU by default, GPU if available
            device = "cpu"
            compute_type = "int8"

            try:
                import torch
                if torch.cuda.is_available():
                    device = "cuda"
                    compute_type = "float16"
                    logger.info("Using GPU for Whisper")
            except ImportError:
                pass

            logger.info(f"Loading Whisper model: {model_size} on {device}")
            _whisper_model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
            )
            logger.info("Whisper model loaded successfully")
        except ImportError:
            logger.warning("faster-whisper not installed. Install with: pip install faster-whisper")
            raise

    return _whisper_model


class SpeechToText:
    """
    Speech-to-Text transcription using faster-whisper.

    Supports:
    - Multiple Indian languages (Hindi, Tamil, Telugu, etc.)
    - English with Indian accent
    - Real-time streaming (chunked)
    """

    def __init__(self, model_size: str = "base.en"):
        """
        Initialize STT engine.

        Args:
            model_size: Whisper model size. Options:
                - "tiny.en", "base.en", "small.en" (English only, faster)
                - "tiny", "base", "small", "medium", "large-v2" (Multilingual)
        """
        self.model_size = model_size
        self._model = None

    @property
    def model(self):
        """Lazy load the model."""
        if self._model is None:
            self._model = get_whisper_model(self.model_size)
        return self._model

    def transcribe(
        self,
        audio_data: bytes | np.ndarray | str | Path,
        language: Optional[str] = None,
    ) -> dict:
        """
        Transcribe audio to text.

        Args:
            audio_data: Audio data as bytes, numpy array, or file path
            language: Language code (e.g., "en", "hi", "ta"). Auto-detect if None.

        Returns:
            Dictionary with:
                - text: Full transcribed text
                - segments: List of segments with timestamps
                - language: Detected language
                - confidence: Average confidence score
        """
        # Handle different input types
        if isinstance(audio_data, (str, Path)):
            audio_input = str(audio_data)
        elif isinstance(audio_data, bytes):
            # Convert bytes to file-like object
            audio_input = io.BytesIO(audio_data)
        else:
            audio_input = audio_data

        # Transcribe
        segments, info = self.model.transcribe(
            audio_input,
            language=language,
            beam_size=5,
            word_timestamps=True,
            vad_filter=True,  # Voice activity detection
            vad_parameters=dict(
                min_silence_duration_ms=500,
                speech_pad_ms=400,
            ),
        )

        # Collect results
        result_segments = []
        full_text = []
        total_confidence = 0.0
        segment_count = 0

        for segment in segments:
            result_segments.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
                "confidence": segment.avg_logprob,
                "words": [
                    {
                        "word": word.word,
                        "start": word.start,
                        "end": word.end,
                        "probability": word.probability,
                    }
                    for word in (segment.words or [])
                ],
            })
            full_text.append(segment.text.strip())
            total_confidence += segment.avg_logprob
            segment_count += 1

        avg_confidence = total_confidence / segment_count if segment_count > 0 else 0.0

        return {
            "text": " ".join(full_text),
            "segments": result_segments,
            "language": info.language,
            "language_probability": info.language_probability,
            "confidence": avg_confidence,
            "duration": info.duration,
        }

    def transcribe_stream(
        self,
        audio_chunks: list[bytes],
        language: Optional[str] = None,
    ):
        """
        Transcribe audio in streaming mode (chunk by chunk).

        Args:
            audio_chunks: List of audio chunks
            language: Language code

        Yields:
            Partial transcription results
        """
        # Combine chunks for now (true streaming would need more complex handling)
        combined = b"".join(audio_chunks)
        result = self.transcribe(combined, language)
        yield result


class SpeechToTextAsync:
    """Async wrapper for Speech-to-Text."""

    def __init__(self, model_size: str = "base.en"):
        self.stt = SpeechToText(model_size)

    async def transcribe(
        self,
        audio_data: bytes | np.ndarray | str | Path,
        language: Optional[str] = None,
    ) -> dict:
        """Async transcribe (runs in thread pool)."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.stt.transcribe(audio_data, language),
        )
