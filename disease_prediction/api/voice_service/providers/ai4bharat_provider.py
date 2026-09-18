"""
MEDLENS AI — AI4Bharat Provider Stub
Integration point for AI4Bharat open-source Indian language models.
https://ai4bharat.iitm.ac.in/

This provider is DISABLED by default.
Enable with AI4BHARAT_ENABLED=true in .env and provide API credentials.

AI4Bharat provides:
- IndicASR: Automatic Speech Recognition for 22 Indian languages
- IndicTTS: Text-to-Speech for Indian languages
- IndicTrans: Translation between Indian languages

These are open-source models that can also run locally.
For SIH demo: browser Web Speech API fallback is used by default.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

AI4BHARAT_ENABLED = os.environ.get("AI4BHARAT_ENABLED", "false").lower() == "true"
AI4BHARAT_API_KEY = os.environ.get("AI4BHARAT_API_KEY", "")
AI4BHARAT_BASE_URL = os.environ.get("AI4BHARAT_BASE_URL", "https://api.ai4bharat.org")

# Languages with known AI4Bharat IndicASR support
AI4BHARAT_STT_LANGUAGES = {
    "hi-IN", "te-IN", "ta-IN", "kn-IN", "ml-IN", "bn-IN",
    "mr-IN", "gu-IN", "pa-IN", "or-IN", "as-IN", "ur-IN",
    "mai-IN", "mni-IN", "brx-IN", "doi-IN", "sat-IN", "sd-IN",
    "ks-IN",
}
AI4BHARAT_TTS_LANGUAGES = {
    "hi-IN", "te-IN", "ta-IN", "kn-IN", "ml-IN", "bn-IN",
    "mr-IN", "gu-IN", "pa-IN", "or-IN", "as-IN",
}


class AI4BharatTTSProvider:
    """
    AI4Bharat IndicTTS provider stub.
    """

    PROVIDER_ID = "ai4bharat"
    PROVIDER_NAME = "AI4Bharat IndicTTS (Open-Source)"

    def is_available(self, language_code: str) -> bool:
        if not AI4BHARAT_ENABLED:
            return False
        return language_code in AI4BHARAT_TTS_LANGUAGES

    def synthesize(self, text: str, language_code: str) -> Optional[bytes]:
        if not self.is_available(language_code):
            return None
        # TODO: Implement AI4Bharat IndicTTS API call
        # Endpoint: POST {AI4BHARAT_BASE_URL}/inference/tts
        # Refer: https://ai4bharat.github.io/IndicTTS/
        logger.info(f"[AI4BHARAT] TTS requested for {language_code} — implementation pending.")
        return None

    def get_info(self, language_code: str) -> dict:
        return {
            "provider": self.PROVIDER_ID,
            "name": self.PROVIDER_NAME,
            "language": language_code,
            "server_side": True,
            "available": self.is_available(language_code),
            "note": "AI4Bharat IndicTTS — configure AI4BHARAT_API_KEY + AI4BHARAT_ENABLED=true",
        }


class AI4BharatSTTProvider:
    """
    AI4Bharat IndicASR provider stub.
    """

    PROVIDER_ID = "ai4bharat"
    PROVIDER_NAME = "AI4Bharat IndicASR (Open-Source)"

    def is_available(self, language_code: str) -> bool:
        if not AI4BHARAT_ENABLED:
            return False
        return language_code in AI4BHARAT_STT_LANGUAGES

    def transcribe(self, audio: bytes, language_code: str) -> str:
        if not self.is_available(language_code):
            return ""
        # TODO: Implement AI4Bharat IndicASR API call
        # Endpoint: POST {AI4BHARAT_BASE_URL}/inference/asr
        logger.info(f"[AI4BHARAT] STT requested for {language_code} — implementation pending.")
        return ""

    def get_info(self, language_code: str) -> dict:
        return {
            "provider": self.PROVIDER_ID,
            "name": self.PROVIDER_NAME,
            "language": language_code,
            "server_side": True,
            "available": self.is_available(language_code),
            "note": "AI4Bharat IndicASR — configure AI4BHARAT_API_KEY + AI4BHARAT_ENABLED=true",
        }
