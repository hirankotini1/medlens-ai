"""
MEDLENS AI — Voice API Router
Provider-independent voice endpoints for multilingual patient case-taking.

Endpoints:
  GET  /api/voice/health        - Voice engine health status (admin only)
  GET  /api/voice/languages     - All supported languages + provider availability
  POST /api/voice/transcribe    - Server-side STT (audio → text)
  POST /api/voice/speak         - Server-side TTS (text → audio)

IMPORTANT:
- These endpoints are OPTIONAL. The frontend uses browser Web Speech API by default.
- If server-side providers are unavailable, 200 is still returned with fallback=true.
- The frontend handles browser STT/TTS when server returns fallback=true.
- Never expose raw patient audio unless explicitly needed for transcription.
"""

import os
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status, Depends, Header, Query
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

try:
    from disease_prediction.api.voice_service.voice_manager import get_voice_manager
    from disease_prediction.api.voice_service.language_config import SUPPORTED_LANGUAGES, get_language
    from disease_prediction.api import database as db
except ImportError:
    try:
        from voice_service.voice_manager import get_voice_manager
        from voice_service.language_config import SUPPORTED_LANGUAGES, get_language
        import database as db
    except ImportError:
        from api.voice_service.voice_manager import get_voice_manager
        from api.voice_service.language_config import SUPPORTED_LANGUAGES, get_language
        from api import database as db

router = APIRouter(prefix="/api/voice", tags=["Multilingual Voice Engine"])

VOICE_ENABLED = os.environ.get("VOICE_ENABLED", "true").lower() == "true"


# ==============================================================================
# PYDANTIC SCHEMAS
# ==============================================================================
class SpeakRequest(BaseModel):
    text: str
    language_code: str = "en-IN"
    speed: float = 1.0  # 0.5 to 2.0


class TranscriptSaveRequest(BaseModel):
    case_id: str
    session_id: Optional[str] = None
    question_key: str
    question_text: str
    answer_original: str
    language_code: str = "en-IN"
    normalized_answer: Optional[str] = None
    confidence: Optional[float] = None
    source: str = "browser"  # 'browser', 'bhashini', 'ai4bharat'


# ==============================================================================
# ENDPOINTS
# ==============================================================================

@router.get("/health")
def voice_health():
    """
    Returns voice engine health status.
    Shows which providers are active and which use browser fallback.
    Intended for admin/developer visibility.
    """
    if not VOICE_ENABLED:
        return {"voice_enabled": False, "message": "Voice engine disabled via VOICE_ENABLED=false"}

    try:
        vm = get_voice_manager()
        health = vm.get_health_status()
        return {
            "status": "ok",
            "voice_enabled": True,
            **health,
            "demo_mode": True,
            "demo_note": (
                "SIH Demo Mode: Browser Web Speech API is the active fallback. "
                "Enable BHASHINI_ENABLED or AI4BHARAT_ENABLED for server-side multilingual STT/TTS."
            ),
        }
    except Exception as e:
        logger.exception("[VoiceHealth] Error generating voice health status")
        return {
            "status": "degraded",
            "voice_enabled": True,
            "error": str(e),
            "fallback": "browser",
        }


@router.get("/languages")
def get_supported_languages():
    """
    Returns all 23 supported languages with:
    - BCP-47 codes
    - Native script names
    - Provider availability (server vs browser fallback)

    Used by frontend to populate language selector and show availability badges.
    """
    try:
        vm = get_voice_manager()
        languages = vm.get_languages_info()
        return {
            "total": len(languages),
            "languages": languages,
            "note": (
                "Languages marked 'browser_fallback' use the browser Web Speech API. "
                "Quality varies by browser and device. Chrome/Edge recommended for Indian languages."
            ),
        }
    except Exception as e:
        logger.warning(f"[VoiceLanguages] Error: {e}. Returning static language list.")
        # Fallback: return static list without provider info
        return {
            "total": len(SUPPORTED_LANGUAGES),
            "languages": [
                {**lang, "availability": "browser_fallback", "tts_provider": "browser", "stt_provider": "browser"}
                for lang in SUPPORTED_LANGUAGES
            ],
        }


@router.post("/speak")
async def synthesize_speech(payload: SpeakRequest):
    """
    Server-side TTS synthesis.
    Returns audio/wav bytes if a server-side TTS provider is available.
    Returns JSON fallback=true if browser TTS should be used instead.

    Client should always have browser TTS as fallback.
    """
    if not VOICE_ENABLED:
        return JSONResponse({"fallback": True, "reason": "Voice engine disabled"})

    if not payload.text or not payload.text.strip():
        raise HTTPException(status_code=400, detail="Text to speak cannot be empty.")

    # Sanitize — do not speak raw stack traces or PII
    text = payload.text.strip()[:500]  # Limit to 500 chars for TTS

    try:
        vm = get_voice_manager()
        audio_bytes = vm.synthesize(text, payload.language_code)

        if audio_bytes:
            return Response(
                content=audio_bytes,
                media_type="audio/wav",
                headers={
                    "Content-Disposition": "inline",
                    "X-Voice-Provider": vm.get_tts_provider(payload.language_code).PROVIDER_ID,
                    "X-Language": payload.language_code,
                }
            )
        else:
            # No server-side audio — instruct client to use browser TTS
            return JSONResponse({
                "fallback": True,
                "text": text,
                "language_code": payload.language_code,
                "browser_lang": get_language(payload.language_code).get("browser_tts_lang", "en-IN"),
                "reason": "No server-side TTS available for this language. Use browser SpeechSynthesis.",
            })
    except Exception as e:
        logger.exception(f"[VoiceSpeak] TTS error for {payload.language_code}")
        return JSONResponse({
            "fallback": True,
            "text": text,
            "language_code": payload.language_code,
            "reason": f"TTS service temporarily unavailable: {type(e).__name__}",
        })


@router.post("/transcribe")
async def transcribe_speech(
    audio: UploadFile = File(...),
    language_code: str = Form("en-IN"),
):
    """
    Server-side STT transcription.
    Accepts audio file (webm/wav/ogg) and returns transcript text.
    Returns fallback=true if browser STT should be used instead.

    Audio is processed in-memory and NOT stored permanently.
    """
    if not VOICE_ENABLED:
        return JSONResponse({"fallback": True, "reason": "Voice engine disabled"})

    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Audio file is empty.")

    # Max 10MB audio
    if len(audio_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio file too large (max 10MB).")

    try:
        vm = get_voice_manager()
        provider = vm.get_stt_provider(language_code)
        transcript = vm.transcribe(audio_bytes, language_code)

        if transcript:
            return {
                "transcript": transcript,
                "language_code": language_code,
                "provider": provider.PROVIDER_ID,
                "fallback": False,
            }
        else:
            return {
                "transcript": "",
                "language_code": language_code,
                "provider": provider.PROVIDER_ID,
                "fallback": False,
                "no_speech": True,
                "message": "No clear speech detected in audio. Please speak louder or closer to the microphone."
            }
    except Exception as e:
        logger.exception(f"[VoiceTranscribe] STT error for {language_code}")
        return JSONResponse({
            "fallback": True,
            "language_code": language_code,
            "reason": f"STT service unavailable: {type(e).__name__}",
        })


@router.post("/save-transcript")
def save_voice_transcript(payload: TranscriptSaveRequest):
    """
    Saves a voice session transcript entry to the database.
    Called after patient confirms their spoken answer.
    Raw audio is NOT stored — only text transcript is persisted.
    """
    try:
        result = db.save_voice_transcript(
            case_id=payload.case_id,
            session_id=payload.session_id,
            question_key=payload.question_key,
            question_text=payload.question_text,
            answer_original=payload.answer_original,
            language_code=payload.language_code,
            normalized_answer=payload.normalized_answer or payload.answer_original,
            confidence=payload.confidence,
            source=payload.source,
        )
        return {"status": "saved", "transcript_id": result.get("transcript_id"), "case_id": payload.case_id}
    except Exception as e:
        logger.exception("[VoiceTranscript] Error saving transcript")
        raise HTTPException(status_code=500, detail=f"Failed to save transcript: {str(e)}")


@router.get("/transcripts/{case_id}")
def get_case_transcripts(case_id: str):
    """
    Returns all voice transcripts for a clinical case.
    Used by the Doctor Console to view original patient voice responses.
    """
    try:
        transcripts = db.get_voice_transcripts(case_id)
        return {
            "case_id": case_id,
            "total": len(transcripts),
            "transcripts": transcripts,
        }
    except Exception as e:
        logger.exception(f"[VoiceTranscript] Error fetching transcripts for {case_id}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch transcripts: {str(e)}")
