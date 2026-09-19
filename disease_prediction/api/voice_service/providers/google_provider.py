"""
MEDLENS AI — Google Speech Recognition STT Provider
Uses Python `speech_recognition` library to transcribe audio files
via Google Speech Recognition public endpoint.

Supports all 23 Indian languages:
- hi-IN, te-IN, ta-IN, kn-IN, ml-IN, bn-IN, mr-IN, gu-IN, pa-IN, ur-IN, or-IN, as-IN, en-IN, etc.
Requires no paid API keys.
"""

import io
import logging
from typing import Optional

try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    sr = None
    SR_AVAILABLE = False

logger = logging.getLogger(__name__)

# Languages supported by Google Speech Recognition
GOOGLE_STT_LANGUAGES = {
    "en-IN", "hi-IN", "te-IN", "ta-IN", "kn-IN", "ml-IN", "bn-IN",
    "mr-IN", "gu-IN", "pa-IN", "ur-IN", "or-IN", "as-IN", "ne-IN",
    "kok-IN", "mai-IN", "mni-IN", "brx-IN", "doi-IN", "sat-IN", "sd-IN", "sa-IN"
}

# Mapping for languages with closest supported Google speech code
FALLBACK_MAP = {
    "kok-IN": "mr-IN",   # Konkani -> Marathi fallback
    "mai-IN": "hi-IN",   # Maithili -> Hindi fallback
    "mni-IN": "bn-IN",   # Manipuri -> Bengali fallback
    "brx-IN": "as-IN",   # Bodo -> Assamese fallback
    "doi-IN": "hi-IN",   # Dogri -> Hindi fallback
    "sat-IN": "bn-IN",   # Santali -> Bengali fallback
    "sd-IN": "ur-IN",    # Sindhi -> Urdu fallback
    "sa-IN": "hi-IN",    # Sanskrit -> Hindi fallback
    "ks-IN": "hi-IN",    # Kashmiri -> Hindi fallback
}


class GoogleSTTProvider:
    """
    Server-side Speech-to-Text using speech_recognition.
    Transcribes incoming WAV audio bytes.
    """

    PROVIDER_ID = "google_stt"
    PROVIDER_NAME = "Server-side Speech Recognition (Multilingual)"

    def __init__(self):
        if SR_AVAILABLE and sr is not None:
            try:
                self.recognizer = sr.Recognizer()
                self.recognizer.energy_threshold = 300
                self.recognizer.dynamic_energy_threshold = True
            except Exception as e:
                logger.warning(f"[GoogleSTT] Failed initializing speech_recognition: {e}")
                self.recognizer = None
        else:
            self.recognizer = None

    def is_available(self, language_code: str) -> bool:
        return bool(SR_AVAILABLE and (self.recognizer is not None))

    def transcribe(self, audio_bytes: bytes, language_code: str = "en-IN") -> str:
        """
        Transcribes WAV audio bytes into text in the specified language.
        """
        if not self.is_available(language_code) or not audio_bytes or len(audio_bytes) < 100:
            return ""

        target_lang = FALLBACK_MAP.get(language_code, language_code)

        try:
            audio_file = io.BytesIO(audio_bytes)
            with sr.AudioFile(audio_file) as source:
                audio_data = self.recognizer.record(source)

            # Transcribe with Google Speech Recognition
            try:
                transcript = self.recognizer.recognize_google(audio_data, language=target_lang)
                if transcript and transcript.strip():
                    logger.info(f"[GoogleSTT] Transcribed ({target_lang}): {transcript}")
                    res = transcript.strip()
                    if language_code in ("or-IN", "or"):
                        try:
                            from disease_prediction.api.voice_service.odia_service import convert_to_odia
                            res = convert_to_odia(res)
                        except Exception:
                            pass
                    return res
            except sr.UnknownValueError:
                # If target language had no match and wasn't en-IN, try Indian English fallback
                if target_lang not in ("en-IN", "en-US"):
                    try:
                        transcript = self.recognizer.recognize_google(audio_data, language="en-IN")
                        if transcript and transcript.strip():
                            logger.info(f"[GoogleSTT] Fallback transcribed (en-IN): {transcript}")
                            res = transcript.strip()
                            if language_code in ("or-IN", "or"):
                                try:
                                    from disease_prediction.api.voice_service.odia_service import convert_to_odia
                                    res = convert_to_odia(res)
                                except Exception:
                                    pass
                            return res
                    except Exception:
                        pass
                logger.info(f"[GoogleSTT] No recognizable speech in audio ({target_lang})")
                return ""
        except sr.RequestError as e:
            logger.error(f"[GoogleSTT] Recognition request failed: {e}")
            return ""
        except Exception as e:
            logger.exception(f"[GoogleSTT] Unexpected error during transcription: {e}")
            return ""

    def get_info(self, language_code: str) -> dict:
        return {
            "provider": self.PROVIDER_ID,
            "name": self.PROVIDER_NAME,
            "language": language_code,
            "server_side": True,
            "note": f"Server-side multilingual STT for {language_code}",
        }
