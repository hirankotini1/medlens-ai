"""
MEDLENS AI — BHASHINI Provider Stub
Integration point for India's BHASHINI multilingual AI platform.
https://bhashini.gov.in/

This provider is DISABLED by default.
Enable with BHASHINI_ENABLED=true in .env and provide API credentials.

When enabled, BHASHINI provides:
- ASR (Automatic Speech Recognition) for major Indian languages
- TTS (Text-to-Speech) for major Indian languages
- Translation services

IMPORTANT: No paid API is required for SIH prototype.
The browser Web Speech API fallback is always available.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

BHASHINI_ENABLED = os.environ.get("BHASHINI_ENABLED", "false").lower() == "true"
BHASHINI_API_KEY = os.environ.get("BHASHINI_API_KEY", "")
BHASHINI_USER_ID = os.environ.get("BHASHINI_USER_ID", "")
BHASHINI_BASE_URL = os.environ.get("BHASHINI_BASE_URL", "https://dhruva-api.bhashini.gov.in")

# Languages with known BHASHINI support
BHASHINI_STT_LANGUAGES = {
    "hi-IN", "te-IN", "ta-IN", "kn-IN", "ml-IN", "bn-IN",
    "mr-IN", "gu-IN", "pa-IN", "or-IN", "as-IN", "ur-IN",
}
BHASHINI_TTS_LANGUAGES = {
    "hi-IN", "te-IN", "ta-IN", "kn-IN", "ml-IN", "bn-IN",
    "mr-IN", "gu-IN", "pa-IN",
}


class BhashiniTTSProvider:
    """
    BHASHINI TTS provider stub.
    Implements the standard TTSProvider interface.
    Returns None when disabled or credentials missing.
    """

    PROVIDER_ID = "bhashini"
    PROVIDER_NAME = "BHASHINI (Govt. of India Multilingual Platform)"

    def is_available(self, language_code: str) -> bool:
        if not BHASHINI_ENABLED:
            return False
        if not BHASHINI_API_KEY:
            logger.warning("[BHASHINI] BHASHINI_API_KEY not set in environment.")
            return False
        return language_code in BHASHINI_TTS_LANGUAGES

    def synthesize(self, text: str, language_code: str) -> Optional[bytes]:
        if not self.is_available(language_code):
            return None
        # TODO: Implement BHASHINI TTS API call when credentials are available
        # Endpoint: POST {BHASHINI_BASE_URL}/services/inference/pipeline
        # Headers: { "Authorization": BHASHINI_API_KEY, "userID": BHASHINI_USER_ID }
        # Refer: https://bhashini.gitbook.io/bhashini-apis/
        logger.info(f"[BHASHINI] TTS requested for {language_code} — implementation pending credentials.")
        return None

    def get_info(self, language_code: str) -> dict:
        return {
            "provider": self.PROVIDER_ID,
            "name": self.PROVIDER_NAME,
            "language": language_code,
            "server_side": True,
            "available": self.is_available(language_code),
            "note": "BHASHINI TTS — configure BHASHINI_API_KEY + BHASHINI_ENABLED=true",
        }


class BhashiniSTTProvider:
    """
    BHASHINI STT/ASR provider stub.
    """

    PROVIDER_ID = "bhashini"
    PROVIDER_NAME = "BHASHINI ASR (Govt. of India)"

    def is_available(self, language_code: str) -> bool:
        if not BHASHINI_ENABLED:
            return False
        if not BHASHINI_API_KEY:
            return False
        return language_code in BHASHINI_STT_LANGUAGES

    def transcribe(self, audio: bytes, language_code: str) -> str:
        if not self.is_available(language_code):
            return ""
        # TODO: Implement BHASHINI ASR API call when credentials are available
        # Endpoint: POST {BHASHINI_BASE_URL}/services/inference/pipeline
        logger.info(f"[BHASHINI] STT requested for {language_code} — implementation pending credentials.")
        return ""

    def get_info(self, language_code: str) -> dict:
        return {
            "provider": self.PROVIDER_ID,
            "name": self.PROVIDER_NAME,
            "language": language_code,
            "server_side": True,
            "available": self.is_available(language_code),
            "note": "BHASHINI ASR — configure BHASHINI_API_KEY + BHASHINI_ENABLED=true",
        }
