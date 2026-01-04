"""
Voice Agent module for DocAssist Practice Manager.

Provides voice-based appointment booking using:
- faster-whisper for Speech-to-Text (STT)
- Chatterbox for Text-to-Speech (TTS) with voice cloning
- Ollama/Qwen for Natural Language Understanding (NLU)
"""

from app.voice.agent import VoiceAgent
from app.voice.stt import SpeechToText
from app.voice.tts import TextToSpeech, ChatterboxTTS, TextToSpeechAsync
from app.voice.nlu import NaturalLanguageUnderstanding

__all__ = [
    "VoiceAgent",
    "SpeechToText",
    "TextToSpeech",
    "ChatterboxTTS",
    "TextToSpeechAsync",
    "NaturalLanguageUnderstanding",
]
