"""
MEDLENS AI — Voice Manager
Provider registry and selection logic for TTS and STT.

Priority chain:
  TTS: AI4Bharat → BHASHINI → TinyTTS (en only) → Browser (metadata)
  STT: AI4Bharat → BHASHINI → Browser (metadata)

The system gracefully falls back at each level.
If all server-side providers are unavailable, the frontend uses
browser Web Speech API directly.
"""
import os
import logging
from typing import Optional, Dict, Any

try:
    from disease_prediction.api.voice_service.providers.browser_provider import BrowserTTSProvider, BrowserSTTProvider
    from disease_prediction.api.voice_service.providers.tinytts_provider import TinyTTSProvider
    from disease_prediction.api.voice_service.providers.bhashini_provider import BhashiniTTSProvider, BhashiniSTTProvider
    from disease_prediction.api.voice_service.providers.ai4bharat_provider import AI4BharatTTSProvider, AI4BharatSTTProvider
    from disease_prediction.api.voice_service.providers.google_provider import GoogleSTTProvider
    from disease_prediction.api.voice_service.language_config import SUPPORTED_LANGUAGES, get_language
except ImportError:
    try:
        from voice_service.providers.browser_provider import BrowserTTSProvider, BrowserSTTProvider
        from voice_service.providers.tinytts_provider import TinyTTSProvider
        from voice_service.providers.bhashini_provider import BhashiniTTSProvider, BhashiniSTTProvider
        from voice_service.providers.ai4bharat_provider import AI4BharatTTSProvider, AI4BharatSTTProvider
        from voice_service.providers.google_provider import GoogleSTTProvider
        from voice_service.language_config import SUPPORTED_LANGUAGES, get_language
    except ImportError:
        from api.voice_service.providers.browser_provider import BrowserTTSProvider, BrowserSTTProvider
        from api.voice_service.providers.tinytts_provider import TinyTTSProvider
        from api.voice_service.providers.bhashini_provider import BhashiniTTSProvider, BhashiniSTTProvider
        from api.voice_service.providers.ai4bharat_provider import AI4BharatTTSProvider, AI4BharatSTTProvider
        from api.voice_service.providers.google_provider import GoogleSTTProvider
        from api.voice_service.language_config import SUPPORTED_LANGUAGES, get_language

logger = logging.getLogger(__name__)

VOICE_ENABLED = os.environ.get("VOICE_ENABLED", "true").lower() == "true"


class VoiceManager:
    """
    Central registry for TTS and STT providers.
    Provider selection is automatic based on language and availability.
    """

    def __init__(self):
        # TTS providers in priority order
        self._tts_providers = [
            AI4BharatTTSProvider(),
            BhashiniTTSProvider(),
            TinyTTSProvider(),
            BrowserTTSProvider(),   # Always last — browser-side fallback
        ]
        # STT providers in priority order
        self._stt_providers = [
            AI4BharatSTTProvider(),
            BhashiniSTTProvider(),
            GoogleSTTProvider(),    # Robust server-side multilingual recognition
            BrowserSTTProvider(),   # Always last — browser-side fallback
        ]

    def get_tts_provider(self, language_code: str):
        """Returns the highest-priority TTS provider available for the language."""
        for provider in self._tts_providers:
            if provider.is_available(language_code):
                return provider
        return BrowserTTSProvider()

    def get_stt_provider(self, language_code: str):
        """Returns the highest-priority STT provider available for the language."""
        for provider in self._stt_providers:
            if provider.is_available(language_code):
                return provider
        return BrowserSTTProvider()

    def synthesize(self, text: str, language_code: str) -> Optional[bytes]:
        """
        Attempt TTS synthesis using the best available provider.
        Returns audio bytes or None (frontend uses browser TTS as fallback).
        """
        if not VOICE_ENABLED:
            return None
        provider = self.get_tts_provider(language_code)
        audio = provider.synthesize(text, language_code)
        if audio:
            logger.info(f"[VoiceManager] TTS synthesis via {provider.PROVIDER_ID} for {language_code}")
        return audio

    def transcribe(self, audio: bytes, language_code: str) -> str:
        """
        Attempt STT transcription using the best available provider.
        Returns transcript string or empty (frontend uses browser STT).
        """
        if not VOICE_ENABLED:
            return ""
        provider = self.get_stt_provider(language_code)
        transcript = provider.transcribe(audio, language_code)
        if transcript:
            logger.info(f"[VoiceManager] STT transcribed via {provider.PROVIDER_ID} for {language_code}")
        return transcript

    def get_health_status(self) -> Dict[str, Any]:
        """
        Returns detailed health status of all voice providers.
        Visible only to admin/developer.
        """
        # Test with a few common languages
        test_langs = ["en-IN", "hi-IN", "te-IN", "ta-IN"]
        tts_status = {}
        stt_status = {}

        for lang in test_langs:
            tts_provider = self.get_tts_provider(lang)
            stt_provider = self.get_stt_provider(lang)
            tts_status[lang] = {
                "provider": tts_provider.PROVIDER_ID,
                "name": tts_provider.PROVIDER_NAME,
                "server_side": tts_provider.PROVIDER_ID != "browser",
            }
            stt_status[lang] = {
                "provider": stt_provider.PROVIDER_ID,
                "name": stt_provider.PROVIDER_NAME,
                "server_side": stt_provider.PROVIDER_ID != "browser",
            }

        from disease_prediction.api.voice_service.providers.tinytts_provider import TINY_TTS_ENABLED
        from disease_prediction.api.voice_service.providers.bhashini_provider import BHASHINI_ENABLED
        from disease_prediction.api.voice_service.providers.ai4bharat_provider import AI4BHARAT_ENABLED

        return {
            "voice_enabled": VOICE_ENABLED,
            "providers": {
                "tiny_tts": {
                    "enabled": TINY_TTS_ENABLED,
                    "role": "Optional English TTS",
                    "languages": ["en-IN", "en-US"],
                },
                "bhashini": {
                    "enabled": BHASHINI_ENABLED,
                    "role": "Indian languages STT + TTS",
                    "languages": "Major 12+ Indian languages",
                },
                "ai4bharat": {
                    "enabled": AI4BHARAT_ENABLED,
                    "role": "Open-source Indian language ASR + TTS",
                    "languages": "22 Indian languages",
                },
                "browser": {
                    "enabled": True,
                    "role": "Client-side browser Web Speech API fallback",
                    "languages": "All (quality varies)",
                },
            },
            "tts_status_by_language": tts_status,
            "stt_status_by_language": stt_status,
        }

    def get_languages_info(self):
        """Returns all supported languages with provider availability metadata."""
        result = []
        for lang in SUPPORTED_LANGUAGES:
            code = lang["code"]
            tts_p = self.get_tts_provider(code)
            stt_p = self.get_stt_provider(code)
            result.append({
                **lang,
                "tts_provider": tts_p.PROVIDER_ID,
                "tts_server_side": tts_p.PROVIDER_ID != "browser",
                "stt_provider": stt_p.PROVIDER_ID,
                "stt_server_side": stt_p.PROVIDER_ID != "browser",
                "availability": (
                    "server" if tts_p.PROVIDER_ID != "browser" or stt_p.PROVIDER_ID != "browser"
                    else "browser_fallback"
                ),
            })
        return result


# Singleton instance
_voice_manager = None

def get_voice_manager() -> VoiceManager:
    global _voice_manager
    if _voice_manager is None:
        _voice_manager = VoiceManager()
    return _voice_manager
