"""
MedLens Clinical Interview Engine — Confidence & Ambiguity Handler
Evaluates answer extraction confidence, generates non-intrusive clarifications,
and logs uncertainties for physician review.
"""

from typing import Dict, Any, List, Optional

CONFIDENCE_HIGH_THRESHOLD = 0.70
CONFIDENCE_MEDIUM_THRESHOLD = 0.45


class ConfidenceManager:
    """Manages answer confidence scoring, clarification generation, and uncertainty logging."""

    @classmethod
    def evaluate_extraction(
        cls,
        param_name: str,
        extracted_data: Dict[str, Any],
        raw_text: str,
        language: str = "en-IN"
    ) -> Dict[str, Any]:
        """
        Assesses confidence score and determines if clarification is needed.
        """
        confidence = float(extracted_data.get("confidence", 0.5))
        value = extracted_data.get("value")

        needs_clarification = False
        clarification_prompt = None

        if confidence < CONFIDENCE_MEDIUM_THRESHOLD or value is None:
            needs_clarification = True
            clarification_prompt = cls.get_clarification_prompt(param_name, raw_text, language)
            action = "CLARIFY"
        elif confidence < CONFIDENCE_HIGH_THRESHOLD:
            # Medium confidence: accept but flag for doctor review
            action = "ACCEPT_WITH_NOTE"
        else:
            action = "ACCEPT"

        return {
            "param_name": param_name,
            "value": value,
            "confidence": confidence,
            "action": action,
            "needs_clarification": needs_clarification,
            "clarification_prompt": clarification_prompt
        }

    @classmethod
    def get_clarification_prompt(cls, param_name: str, raw_text: str, language: str = "en-IN") -> str:
        """Generates friendly, gentle clarification prompts in the user's language."""
        prompts = {
            "duration": {
                "en-IN": f"Just to make sure I noted it correctly, about how long have you had this issue? (e.g., 2 days, 1 week)",
                "hi-IN": f"यह सुनिश्चित करने के लिए कि मैंने सही समझा, यह समस्या आपको लगभग कितने समय से है? (जैसे: २ दिन, १ हफ्ता)",
                "te-IN": f"సరైన వివరాలు నమోదు చేయడానికి, ఈ సమస్య మీకు సుమారు ఎన్ని రోజుల నుండి ఉంది? (ఉదా: 2 రోజులు, 1 వారం)",
                "or-IN": f"ଠିକ୍ ଭାବରେ ଲିପିବଦ୍ଧ କରିବା ପାଇଁ, ଏହି ସମସ୍ୟା କେତେ ଦିନରୁ ହେଉଛି କହିପାରିବେ କି? (ଯେପରିକି: ୨ ଦିନ, ୧ ସପ୍ତାହ)",
                "ta-IN": f"சரியாக பதிவு செய்ய, இந்த பிரச்சனை எத்தனை நாட்களாக உள்ளது?"
            },
            "severity": {
                "en-IN": "On a scale from 1 (very mild) to 10 (unbearable), how would you rate the discomfort?",
                "hi-IN": "१ (बहुत हल्का) से १० (असहनीय) के पैमाने पर, आप इस परेशानी को कितना अंक देंगे?",
                "te-IN": "1 (చాలా తక్కువ) నుండి 10 (భరించలేనిది) స్కేల్‌లో, మీ బాధ ఎంతవరకు ఉంది?",
                "or-IN": "୧ (ଅତି ସାମାନ୍ୟ) ରୁ ୧୦ (ଅସହ୍ୟ) ମଧ୍ୟରେ, ଆପଣଙ୍କ କଷ୍ଟକୁ କେତେ ନମ୍ବର ଦେବେ?",
                "ta-IN": "1 முதல் 10 வரை, வலி எந்த அளவில் உள்ளது?"
            },
            "location": {
                "en-IN": "Could you pinpoint where exactly on your body you are feeling this?",
                "hi-IN": "क्या आप बता सकते हैं कि शरीर में ठीक किस जगह यह महसूस हो रहा है?",
                "te-IN": "మీ శరీరంలో సరిగ్గా ఎక్కడ నొప్పి లేదా అసౌకర్యం ఉందో చెప్పగలరా?",
                "or-IN": "ଶରୀରର ଠିକ୍ କେଉଁ ସ୍ଥାନରେ ଏହା କଷ୍ଟ ଦେଉଛି ସ୍ପଷ୍ଟ କରିବେ କି?",
                "ta-IN": "உடலில் எந்த இடத்தில் இந்த வலி உள்ளது?"
            },
            "general": {
                "en-IN": "Could you please clarify that in a few words so your doctor gets the exact picture?",
                "hi-IN": "क्या आप इसे थोड़े और शब्दों में स्पष्ट कर सकते हैं ताकि डॉक्टर को सही जानकारी मिले?",
                "te-IN": "దయచేసి కొంచెం స్పష్టంగా వివరించగలరా?",
                "or-IN": "ଦୟାକରି ଆଉ ଟିକେ ସ୍ପଷ୍ଟ ଭାବରେ କହିପାରିବେ କି ଯାହାଦ୍ୱାରା ଡାକ୍ତର ଠିକ୍ ଭାବେ ବୁଝିପାରିବେ?",
                "ta-IN": "தயவுசெய்து கொஞ்சம் தெளிவாக கூற முடியுமா?"
            }
        }

        group = prompts.get(param_name, prompts["general"])
        return group.get(language, group.get("en-IN", "Could you please clarify?"))
