"""
MEDLENS AI — Browser Provider
Represents the browser-side Web Speech API (STT) and SpeechSynthesis (TTS).
The actual execution happens in the frontend JS; this backend class
reports availability and provides configuration metadata to the frontend.

NOTE: Browser STT/TTS cannot be executed server-side.
This class informs the frontend which browser locale to use.
"""
from typing import Optional


class BrowserTTSProvider:
    """
    Browser SpeechSynthesis TTS.
    Executed entirely on the client — backend only provides metadata.
    """

    PROVIDER_ID = "browser"
    PROVIDER_NAME = "Browser SpeechSynthesis (Web Speech API)"

    def is_available(self, language_code: str) -> bool:
        """
        Browser TTS is available as a fallback for all languages
        (quality varies). Returns True — actual voice availability
        is checked at runtime in the browser.
        """
        return True

    def synthesize(self, text: str, language_code: str) -> Optional[bytes]:
        """
        Browser provider cannot synthesize server-side.
        Returns None — the frontend handles synthesis directly.
        """
        return None

    def get_info(self, language_code: str) -> dict:
        return {
            "provider": self.PROVIDER_ID,
            "name": self.PROVIDER_NAME,
            "language": language_code,
            "server_side": False,
            "note": "Executed in browser via SpeechSynthesis API",
        }


class BrowserSTTProvider:
    """
    Browser Web Speech API STT.
    Executed entirely on the client — backend only provides locale config.
    """

    PROVIDER_ID = "browser"
    PROVIDER_NAME = "Browser Web Speech API"

    def is_available(self, language_code: str) -> bool:
        """
        Browser STT is available as fallback for supported locales.
        Chrome/Edge: broad Indian language support.
        Firefox/Safari: limited support.
        """
        return True

    def transcribe(self, audio: bytes, language_code: str) -> str:
        """
        Browser provider cannot transcribe server-side.
        Returns empty — frontend handles recognition directly.
        """
        return ""

    def get_info(self, language_code: str) -> dict:
        return {
            "provider": self.PROVIDER_ID,
            "name": self.PROVIDER_NAME,
            "language": language_code,
            "server_side": False,
            "note": "Executed in browser via Web Speech API (Chrome/Edge recommended)",
        }
