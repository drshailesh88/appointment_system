"""
Voice Agent module for DocAssist Practice Manager.

Provides voice-based appointment booking using:
- faster-whisper for Speech-to-Text (STT)
- Piper for Text-to-Speech (TTS)
- Ollama/Qwen for Natural Language Understanding (NLU)
"""

from app.voice.agent import VoiceAgent
from app.voice.stt import SpeechToText
from app.voice.tts import TextToSpeech
from app.voice.nlu import NaturalLanguageUnderstanding

__all__ = [
    "VoiceAgent",
    "SpeechToText",
    "TextToSpeech",
    "NaturalLanguageUnderstanding",
]
