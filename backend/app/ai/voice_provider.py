"""Phase 8 — voice provider abstraction (plan v3, config-swappable via VOICE_PROVIDER).

The MVP path is "webspeech": speech-to-text and text-to-speech run entirely in the browser via the
Web Speech API — zero cost, no server key, and no candidate audio ever leaves the device. This module
just reports the active capability so the frontend knows whether to show the mic / speaker controls;
a hosted STT/TTS provider can later be added here behind the same shape without touching the UI.
"""
from app.config import get_settings


def capability() -> dict:
    s = get_settings()
    provider = (s.voice_provider or "webspeech").lower()
    if provider == "webspeech":
        return {"provider": "webspeech", "stt": "client", "tts": "client", "configured": True}
    # A hosted provider would need a key; report accordingly (no server implementation in the MVP).
    return {"provider": provider, "stt": "server", "tts": "server", "configured": bool(s.voice_api_key)}
