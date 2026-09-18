"""
MEDLENS AI — TinyTTS Provider (English Only)
Optional English TTS provider using TinyTTS.
Repository: https://github.com/tronghieuit/tiny-tts

IMPORTANT:
- TinyTTS is for ENGLISH only.
- DO NOT use TinyTTS for Indian languages.
- This is an OPTIONAL feature. App works without it.
- Enable with TINY_TTS_ENABLED=true in .env

Install TinyTTS (optional):
  pip install tiny-tts   (if published on PyPI)
  OR clone from: https://github.com/tronghieuit/tiny-tts
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

TINY_TTS_ENABLED = os.environ.get("TINY_TTS_ENABLED", "false").lower() == "true"

# Attempt lazy import of TinyTTS
_tiny_tts_module = None

def _load_tiny_tts():
    global _tiny_tts_module
    if _tiny_tts_module is not None:
        return _tiny_tts_module
    try:
        import tiny_tts  # noqa: F401
        _tiny_tts_module = tiny_tts
        logger.info("[TinyTTS] TinyTTS loaded successfully.")
        return _tiny_tts_module
    except ImportError:
        logger.info("[TinyTTS] TinyTTS not installed. English TTS will use browser fallback.")
        return None


class TinyTTSProvider:
    """
    Optional English-only TTS using TinyTTS.
    Gracefully degrades to None when not installed.
    NEVER used for Indian language TTS.
    """

    PROVIDER_ID = "tinytts"
    PROVIDER_NAME = "TinyTTS (English)"
    SUPPORTED_LANGUAGES = {"en-IN", "en-US", "en-GB"}

    def is_available(self, language_code: str) -> bool:
        """
        TinyTTS is only available for English and only when enabled and installed.
        For ALL Indian languages — returns False.
        """
        if not TINY_TTS_ENABLED:
            return False
        if language_code not in self.SUPPORTED_LANGUAGES:
            return False
        module = _load_tiny_tts()
        return module is not None

    def synthesize(self, text: str, language_code: str) -> Optional[bytes]:
        """
        Synthesize English text using TinyTTS.
        Returns audio bytes if successful, None otherwise.
        """
        if not self.is_available(language_code):
            return None

        module = _load_tiny_tts()
        if not module:
            return None

        try:
            # TinyTTS API — adapt if API differs in the actual library
            audio_data = module.synthesize(text)
            if isinstance(audio_data, bytes):
                return audio_data
            logger.warning("[TinyTTS] Unexpected output type from TinyTTS.synthesize()")
            return None
        except Exception as e:
            logger.warning(f"[TinyTTS] Synthesis failed: {e}")
            return None

    def get_info(self, language_code: str) -> dict:
        available = self.is_available(language_code)
        return {
            "provider": self.PROVIDER_ID,
            "name": self.PROVIDER_NAME,
            "language": language_code,
            "server_side": True,
            "available": available,
            "note": (
                "TinyTTS English TTS active."
                if available
                else "TinyTTS unavailable — using browser fallback."
            ),
        }
