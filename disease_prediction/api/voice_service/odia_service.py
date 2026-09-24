"""
MEDLENS AI — Dedicated Odia (ଓଡ଼ିଆ) Speech & Clinical Language Converter
Converts speech recognition output (which may be transcribed as English words,
Romanized Odia phrases, or mixed medical terms) into authentic, native Odia Unicode script (ଓଡ଼ିଆ ଲିପି).

Multi-Tier Processing Architecture:
  Tier 1: Pre-parsed Odia Script Validator (preserves existing Odia characters)
  Tier 2: Clinical Lexicon & Romanized Transliteration Engine
  Tier 3: Google Translate (GTX) Free Neural Endpoint (Odia 'or' locale)
  Tier 4: OpenRouter LLM Medical Converter (with clinical contextual prompt)
"""

import os
import re
import json
import logging
import urllib.request
import urllib.parse
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# Common colloquial & clinical Romanized Odia to native Odia script dictionary
ODIA_CLINICAL_LEXICON: Dict[str, str] = {
    # Symptoms & Sensations
    "munda bindhuchi": "ମୁଣ୍ଡ ବିନ୍ଧୁଛି",
    "munda betha": "ମୁଣ୍ଡ ବିନ୍ଧା",
    "munda bulauchi": "ମୁଣ୍ଡ ବୁଲାଇବା",
    "mora munda bindhuchi": "ମୋର ମୁଣ୍ଡ ବିନ୍ଧୁଛି",
    "jwara": "ଜ୍ୱର",
    "jwar": "ଜ୍ୱର",
    "jwara heuchi": "ଜ୍ୱର ହେଉଛି",
    "mora jwara achi": "ମୋର ଜ୍ୱର ଅଛି",
    "high fever": "ପ୍ରବଳ ଜ୍ୱର",
    "fever": "ଜ୍ୱର",
    "fever and headache": "ଜ୍ୱର ଏବଂ ମୁଣ୍ଡବିନ୍ଧା",
    "headache": "ମୁଣ୍ଡବିନ୍ଧା",
    "severe headache": "ଅସହ୍ୟ ମୁଣ୍ଡବିନ୍ଧା",
    "chest pain": "ଛାତିରେ ଯନ୍ତ୍ରଣା",
    "chhati betha": "ଛାତି ଯନ୍ତ୍ରଣା",
    "chhati re jantrana": "ଛାତିରେ ଯନ୍ତ୍ରଣା",
    "petare betha": "ପେଟରେ ଯନ୍ତ୍ରଣା",
    "petare betha heuchi": "ପେଟରେ ବେଥା / ଯନ୍ତ୍ରଣା ହେଉଛି",
    "peta betha": "ପେଟ ଯନ୍ତ୍ରଣା",
    "stomach pain": "ପେଟ ଯନ୍ତ୍ରଣା",
    "abdominal pain": "ପେଟ ଯନ୍ତ୍ରଣା",
    "banti": "ବାନ୍ତି",
    "banti heuchi": "ବାନ୍ତି ହେଉଛି",
    "vomiting": "ବାନ୍ତି",
    "nausea": "ଅଇଁଷିଆ ଲାଗିବା",
    "chakkara": "ଚକ୍କର ଆସିବା",
    "dizziness": "ମୁଣ୍ଡ ବୁଲାଇବା / ଚକ୍କର",
    "swasakasta": "ଶ୍ୱାସକଷ୍ଟ",
    "breathless": "ଶ୍ୱାସକଷ୍ଟ",
    "shortness of breath": "ନିଶ୍ୱାସ ନେବାରେ କଷ୍ଟ",
    "cough": "କାଶ",
    "cold": "ଥଣ୍ଡା",
    "cough and cold": "ଥଣ୍ଡା ଏବଂ କାଶ",
    "kasa": "କାଶ",
    "thanda": "ଥଣ୍ଡା",
    "jhala": "ଝାଳ ବାହାରିବା",
    "sweating": "ଝାଳ ବାହାରିବା",
    "durbala laguchi": "ଦୁର୍ବଳ ଲାଗୁଛି",
    "weakness": "ଅତ୍ୟଧିକ ଦୁର୍ବଳତା",
    "pain": "ଯନ୍ତ୍ରଣା",
    "severe pain": "ତୀବ୍ର ଯନ୍ତ୍ରଣା",
    "asodhya": "ଅସହ୍ୟ",
    "unbearable": "ଅସହ୍ୟ ଯନ୍ତ୍ରଣା",
    "loose motion": "ତରଳ ଝାଡ଼ା",
    "diarrhea": "ତରଳ ଝାଡ଼ା",
    "jhada": "ଝାଡ଼ା",
    "raktapata": "ରକ୍ତସ୍ରାବ",
    "bleeding": "ରକ୍ତସ୍ରାବ",
    "blood in stool": "ଝାଡ଼ାରେ ରକ୍ତ",
    "blood in vomit": "ବାନ୍ତିରେ ରକ୍ତ",

    # Durations & Frequencies
    "aaji": "ଆଜି",
    "today": "ଆଜିଠାରୁ",
    "kali": "ଗତକାଲି",
    "yesterday": "ଗତକାଲିଠାରୁ",
    "1 day": "୧ ଦିନ ହେବ",
    "2 days": "୨ ଦିନ ହେବ",
    "3 days": "୩ ଦିନ ହେବ",
    "4 days": "୪ ଦିନ ହେବ",
    "5 days": "୫ ଦିନ ହେବ",
    "duita dina": "୨ ଦିନ ହେବ",
    "tinta dina": "୩ ଦିନ ହେବ",
    "1 week": "୧ ସପ୍ତାହ ହେବ",
    "2 weeks": "୨ ସପ୍ତାହ ହେବ",
    "1 month": "୧ ମାସ ହେବ",
    "several days": "କିଛି ଦିନ ହେବ",
    "since morning": "ସକାଳୁ",
    "since yesterday": "ଗତକାଲିଠାରୁ",

    # Chronic Conditions & History
    "madhumeha": "ମଧୁମେହ",
    "diabetes": "ମଧୁମେହ (ଡାଇବେଟିସ୍)",
    "sugar": "ସୁଗାର (ମଧୁମେହ)",
    "bp": "ରକ୍ତଚାପ (ବିପି)",
    "high bp": "ଉଚ୍ଚ ରକ୍ତଚାପ (ହାଇ ବିପି)",
    "hypertension": "ଉଚ୍ଚ ରକ୍ତଚାପ",
    "heart disease": "ହୃଦରୋଗ",
    "asthma": "ଶ୍ୱାସ (ଆଜମା)",
    "thyroid": "ଥାଇରଏଡ୍",
    "no prior illness": "କୌଣସି ପୁରୁଣା ରୋଗ ନାହିଁ",
    "none": "ନାହିଁ",
    "no medicine": "କୌଣସି ଔଷଧ ନାହିଁ",
    "no medicines": "କୌଣସି ଔଷଧ ନାହିଁ",
    "allergic": "ଆଲର୍ଜି ଅଛି",
    "no allergy": "କୌଣସି ଆଲର୍ଜି ନାହିଁ",
}


def is_odia_text(text: str) -> bool:
    """Checks if the string already contains significant Odia Unicode characters (U+0B00 to U+0B7F)."""
    if not text:
        return False
    odia_chars = [c for c in text if '\u0b00' <= c <= '\u0b7f']
    return len(odia_chars) >= max(2, len(text.strip()) * 0.3)


def _translate_with_google_gtx(text: str) -> Optional[str]:
    """Free Google Translate single endpoint for fast English/Roman to Odia translation."""
    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=or&dt=t&q=" + urllib.parse.quote(text.strip())
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            }
        )
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                translated = "".join([part[0] for part in data[0] if part and len(part) > 0 and part[0]])
                if translated and is_odia_text(translated):
                    return translated.strip()
    except Exception as e:
        logger.debug(f"[OdiaService] Google GTX translate error: {e}")
    return None


def _translate_with_openrouter(text: str) -> Optional[str]:
    """Translates and transliterates Romanized/English medical text into Odia using OpenRouter free model."""
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        return None

    try:
        import requests
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "Avenqra Multilingual Voice Engine",
        }
        payload = {
            "model": "openrouter/free",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a medical speech-to-text transcriber and translator for the Odia language (ଓଡ଼ିଆ).\n"
                        "Task: Convert the patient's spoken symptom text (which might be in English words, "
                        "Romanized Odia phonetics like 'munda bindhuchi', or mixed clinical terms) directly into "
                        "authentic Odia script (ଓଡ଼ିଆ ଲିପି).\n"
                        "CRITICAL: Output ONLY the translated/transliterated Odia script. Do NOT include explanations, "
                        "transliterations, brackets, or English words."
                    )
                },
                {
                    "role": "user",
                    "content": f"Convert to Odia script: {text.strip()}"
                }
            ],
            "max_tokens": 150,
            "temperature": 0.1,
        }
        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=5.0
        )
        if res.status_code == 200:
            result_data = res.json()
            out = result_data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            # Clean markdown fences or quotes if model added any
            out = re.sub(r"^[\"']|[\"']$", "", out).strip()
            if is_odia_text(out):
                return out
    except Exception as e:
        logger.warning(f"[OdiaService] OpenRouter Odia conversion error: {e}")
    return None


def _lookup_lexicon(text: str) -> Optional[str]:
    """Exact or normalized dictionary match for common Odia symptom phrases."""
    clean = text.lower().strip().rstrip(".!?")
    if clean in ODIA_CLINICAL_LEXICON:
        return ODIA_CLINICAL_LEXICON[clean]
    
    # Try partial multi-word replacements
    res = clean
    matched = False
    for k, v in sorted(ODIA_CLINICAL_LEXICON.items(), key=lambda x: -len(x[0])):
        if k in res:
            res = res.replace(k, v)
            matched = True
    if matched and is_odia_text(res):
        return res
    return None


def convert_to_odia(text: str) -> str:
    """
    Primary entry point: Converts any input text (English, Romanized Odia, or mixed)
    into authentic Odia Unicode script.
    """
    if not text or not text.strip():
        return ""

    raw = text.strip()

    # 1. If already predominantly Odia script, return directly
    if is_odia_text(raw):
        return raw

    # 2. Exact match in clinical lexicon
    clean_lower = raw.lower().strip().rstrip(".!?")
    if clean_lower in ODIA_CLINICAL_LEXICON:
        lex = ODIA_CLINICAL_LEXICON[clean_lower]
        logger.info(f"[OdiaService] Exact Lexicon match: '{raw}' -> '{lex}'")
        return lex

    # 3. Google GTX Neural translation (high accuracy for full natural sentences)
    gtx_match = _translate_with_google_gtx(raw)
    if gtx_match and is_odia_text(gtx_match):
        logger.info(f"[OdiaService] GTX match: '{raw}' -> '{gtx_match}'")
        return gtx_match

    # 4. OpenRouter AI translation & transliteration (handles romanized slang and mixed input)
    llm_match = _translate_with_openrouter(raw)
    if llm_match and is_odia_text(llm_match):
        logger.info(f"[OdiaService] OpenRouter match: '{raw}' -> '{llm_match}'")
        return llm_match

    # 5. Partial multi-word lexicon replacement as fallback
    lex_match = _lookup_lexicon(raw)
    if lex_match and is_odia_text(lex_match):
        logger.info(f"[OdiaService] Partial Lexicon match: '{raw}' -> '{lex_match}'")
        return lex_match

    # 6. Fallback: Return original text if conversion could not be verified
    return raw
