"""
MEDLENS AI — Clinical Answer Extractor & NLP Normalizer (SIH PS 26047)
Extracts clinical entities, parameters, and qualifiers from free-form spoken/typed text:
- Duration extraction & temporal normalization (e.g., 'since yesterday' -> '1 day')
- Severity scoring (numeric 1-10 scale or qualitative mapping)
- Onset detection (sudden vs gradual)
- Anatomical location & radiation paths
- Pain character (crushing, sharp, throbbing, dull)
- Triggers & Relieving factors
- Associated symptoms & systemic features
- Medications, Allergies & Surgical references
- Confidence evaluation & Conversation Memory generator
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

class ClinicalAnswerExtractor:
    """Extracts structured medical entities from free-form patient responses."""

    # Common temporal patterns
    DURATION_PATTERNS = [
        (r"(today|since\s*morning|आज|ఈరోజు|ଆଜି)", "Today (< 1 day)"),
        (r"(yesterday|since\s*yesterday|कल\s*से|నిన్నటి\s*నుండి|ଗତକାଲି)", "1 day"),
        (r"(\d+)\s*(day|days|दिन|రోజులు|ଦିନ)", lambda m: f"{m.group(1)} days"),
        (r"(\d+)\s*(week|weeks|हफ्ते|వారాలు|ସପ୍ତାହ)", lambda m: f"{m.group(1)} weeks"),
        (r"(\d+)\s*(month|months|महीने|నెలలు|ମାସ)", lambda m: f"{m.group(1)} months"),
        (r"(one|a)\s*week", "1 week"),
        (r"(one|a)\s*month", "1 month"),
        (r"(two|2)\s*weeks", "2 weeks"),
        (r"(few|several)\s*days", "3-4 days"),
        (r"(few|several)\s*months", "3-4 months"),
        (r"(chronic|long\s*time|years|वर्षों)", "Chronic (> 6 months)")
    ]

    # Pain & Discomfort Character
    PAIN_CHARACTERS = {
        "crushing": [r"crush", r"heavy\s*pressure", r"weight", r"दबाव", r"భారం", r"ଚାପ"],
        "sharp_stabbing": [r"sharp", r"stabbing", r"needle", r"knife", r"तीखा", r"గుచ్చినట్లు", r"ଛୁଞ୍ଚି"],
        "burning": [r"burn", r"burning", r"fire", r"acid", r"जलन", r"మంట", r"ପୋଡ଼ାଜଳା"],
        "throbbing": [r"throb", r"pulsat", r"pounding", r"धड़कन", r"దబదబ", r"ଧପ୍-ଧପ୍"],
        "dull_ache": [r"dull", r"constant\s*ache", r"mild\s*pain", r"हल्का\s*दर्द", r"ମାନ୍ଦା"]
    }

    # Anatomical Locations
    LOCATIONS = {
        "left_chest": [r"left\s*side\s*chest", r"left\s*chest", r"बाईं\s*तरफ\s*सीने", r"ఎడమ\s*ఛాతీ", r"ବାମ\s*ଛାତି"],
        "center_chest": [r"center\s*chest", r"middle\s*chest", r"substernal", r"बीच\s*में", r"మధ్యలో", r"ମଝିରେ"],
        "right_chest": [r"right\s*side\s*chest", r"right\s*chest", r"दाईं\s*तरफ", r"కుడి\s*వైపు", r"ଡାହାଣ\s*ପାଖ"],
        "upper_abdomen": [r"upper\s*stomach", r"upper\s*abdom", r"epigastr", r"ऊपर\s*पेट", r"పై\s*కడుపు", r"ଉପର\s*ପେଟ"],
        "right_lower_abdomen": [r"lower\s*right\s*abdom", r"appendix\s*side", r"दाईं\s*निचली", r"కింద\s*కుడి", r"ତଳ\s*ଡାହାଣ"],
        "lower_back": [r"lower\s*back", r"lumbar", r"कमर", r"నడుము", r"ଅଣ୍ଟା"],
        "forehead": [r"front\s*of\s*head", r"forehead", r"कपाल", r"ముందు\s*తల", r"କପାଳ"]
    }

    # Radiation Paths
    RADIATION_PATTERNS = {
        "left_arm": [r"left\s*arm", r"left\s*shoulder", r"बाईं\s*भुजा", r"ఎడమ\s*చేయి", r"ବାମ\s*ହାତ"],
        "jaw_neck": [r"jaw", r"neck", r"throat", r"जबड़ा", r"గడ్డం", r"దవడ", r"ହନୁହାଡ଼"],
        "back_scapula": [r"upper\s*back", r"shoulder\s*blade", r"पीठ", r"వీపు", r"ପିଠି"],
        "down_leg": [r"down\s*the\s*leg", r"sciatica", r"feet", r"पैरों\s*में", r"కాలు\s*వరకు", r"ଗୋଡ଼"]
    }

    def extract_entities_from_text(self, text: str, question_id: Optional[str] = None) -> Dict[str, Any]:
        """Analyzes patient utterance and extracts all recognizable clinical parameters."""
        if not text or not text.strip():
            return {"confidence": 0.0, "extracted": {}}

        clean_text = text.lower().strip()
        extracted: Dict[str, Any] = {}
        matched_indicators = 0

        # 1. Duration Extraction
        duration_val = self._extract_duration(clean_text)
        if duration_val:
            extracted["duration"] = duration_val
            matched_indicators += 1

        # 2. Severity Extraction
        severity_val = self._extract_severity(clean_text)
        if severity_val is not None:
            extracted["severity"] = severity_val
            matched_indicators += 1

        # 3. Onset Mode (Sudden vs Gradual)
        onset_val = self._extract_onset(clean_text)
        if onset_val:
            extracted["onset"] = onset_val
            matched_indicators += 1

        # 4. Pain Character
        for char_name, patterns in self.PAIN_CHARACTERS.items():
            if any(re.search(p, clean_text) for p in patterns):
                extracted["character"] = char_name
                matched_indicators += 1
                break

        # 5. Anatomical Location
        for loc_name, patterns in self.LOCATIONS.items():
            if any(re.search(p, clean_text) for p in patterns):
                extracted["location"] = loc_name
                matched_indicators += 1
                break

        # 6. Radiation
        for rad_name, patterns in self.RADIATION_PATTERNS.items():
            if any(re.search(p, clean_text) for p in patterns):
                extracted["radiation"] = rad_name
                matched_indicators += 1
                break

        # 7. Exertional / Relieving Factors
        if re.search(r"worse.*(walk|stairs|work|effort|exertion)|चलने.*बढ़ता|నడిస్తే.*ఎక్కువ", clean_text):
            extracted["exertional_relationship"] = "worsens_on_exertion"
            matched_indicators += 1
        elif re.search(r"better.*rest|आराम.*कम|విశ్రాంతి.*తగ్గు", clean_text):
            extracted["relieving_factors"] = "relieved_by_rest"
            matched_indicators += 1

        # 8. Associated Symptoms Detection
        associated = []
        if re.search(r"\bfever\b|\btemp\b|बुखार|జ్వరం|ଜ୍ୱର", clean_text):
            associated.append("fever")
        if re.search(r"\bsweat\b|पसीना|చెమట|ଝାଳ", clean_text):
            associated.append("sweating")
        if re.search(r"\bvomit\b|\bnausea\b|उल्टी|వాంతి|ବାନ୍ତି", clean_text):
            associated.append("vomiting/nausea")
        if re.search(r"\bbreath\b|सांस|శ్వాస|ଶ୍ୱାସ", clean_text):
            associated.append("breathlessness")
        if re.search(r"\bdizzy\b|\bfaint\b|चक्कर|కళ్ళు\s*తిరగడం|ଚକ୍କର", clean_text):
            associated.append("dizziness")
        
        if associated:
            extracted["associated_symptoms"] = associated
            matched_indicators += 1

        # 9. Medications Extraction
        meds = self._extract_medications(clean_text)
        if meds:
            extracted["medications"] = meds
            matched_indicators += 1

        # 10. Allergies Extraction
        allergies = self._extract_allergies(clean_text)
        if allergies:
            extracted["allergies"] = allergies
            matched_indicators += 1

        # Compute Confidence Score
        confidence = 0.94 if matched_indicators >= 2 else (0.85 if matched_indicators == 1 else 0.70)
        if len(text.split()) < 2:
            confidence = 0.55  # single-word or very short utterance

        return {
            "confidence": confidence,
            "raw_text": text,
            "extracted": extracted,
            "timestamp": datetime.now().isoformat()
        }

    def _extract_duration(self, text: str) -> Optional[str]:
        for pattern, replacement in self.DURATION_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if callable(replacement):
                    return replacement(match)
                return replacement
        return None

    def _extract_severity(self, text: str) -> Optional[int]:
        # Numeric scale check (e.g., '7', '8/10', 'level 6')
        num_match = re.search(r"\b([1-9]|10)\s*(?:out of 10|\/10|scale)?\b", text)
        if num_match:
            try:
                score = int(num_match.group(1))
                if 1 <= score <= 10:
                    return score
            except Exception:
                pass

        # Qualitative mapping
        if re.search(r"unbearable|worst|severe\s*distress|असहनीय|భరించలేని|ଅସହ୍ୟ", text):
            return 9
        if re.search(r"severe|heavy|बहुत\s*तेज|తీవ్రమైన|ତୀବ୍ର", text):
            return 7
        if re.search(r"moderate|medium|मध्यम|మధ్యస్థ|ମଧ୍ୟମ", text):
            return 5
        if re.search(r"mild|slight|कम|తక్కువ|ସାମାନ୍ୟ", text):
            return 3
        return None

    def _extract_onset(self, text: str) -> Optional[str]:
        if re.search(r"sudden|suddenly|instant|acute|अचानक|హఠాత్తుగా|ଅଚାନକ|ହଠାତ୍", text):
            return "sudden"
        if re.search(r"gradual|slowly|over\s*days|धीरे-धीरे|క్రమంగా|ଧୀରେ ଧୀରେ", text):
            return "gradual"
        return None

    def _extract_medications(self, text: str) -> List[str]:
        if re.search(r"\b(no\s+.*med\w*|no\s+med\w*|do\s+not\s+take\s+any|not\s+taking\s+any|none|nothing|koyi\s+dawai\s+nahi|mandulu\s+levu|no\s+drugs)\b", text, re.IGNORECASE):
            return ["no regular medications"]
        common_rx = [
            "metformin", "telmisartan", "amlodipine", "atorvastatin", "aspirin", "insulin",
            "pantoprazole", "omeprazole", "paracetamol", "crocin", "dolo", "thyroxine", "losartan"
        ]
        found = []
        for rx in common_rx:
            if rx in text:
                found.append(rx.title())
        return found

    def _extract_allergies(self, text: str) -> List[str]:
        if re.search(r"\b(no allerg\w*|none|nothing|koyi allergy nahi|allergy ledu)\b", text, re.IGNORECASE):
            return ["no known allergies"]
        common_allergens = ["penicillin", "sulfa", "aspirin", "ibuprofen", "contrast", "peanuts", "egg"]
        found = []
        if "allerg" in text or "reaction" in text or "एलर्जी" in text or "అలెర్జీ" in text or "ଆଲର୍ଜି" in text:
            for ag in common_allergens:
                if ag in text:
                    found.append(ag.title())
        return found

    def build_contextual_conversation_prefix(self, state: Dict[str, Any], question_id: str, lang_code: str = "en-IN") -> str:
        """
        Creates natural, empathetic conversation memory acknowledging previous patient statements.
        Supports multi-parameter contextual memory across en, hi, te, and or.
        """
        hpi = state.get("hpi", {})
        complaints = state.get("chief_complaints", [])
        primary = complaints[0] if complaints else "problem"
        clean_primary = primary.replace("_", " ")

        def get_val(key):
            item = hpi.get(key)
            if isinstance(item, dict):
                return item.get("value")
            return item

        duration = get_val("duration")
        location = get_val("location")
        severity = get_val("severity")

        # 1. Questions regarding Radiation / Spreading
        if "radiation" in question_id or "spread" in question_id:
            if location and duration:
                if lang_code == "hi-IN":
                    return f"समझ गया, आपको {duration} से {location} में दर्द है। "
                elif lang_code == "te-IN":
                    return f"అర్థమైంది, మీకు {duration} నుండి {location}లో అసౌకర్యంగా ఉంది. "
                elif lang_code == "or-IN":
                    return f"ବୁଝିପାରିଲି, ଆପଣଙ୍କୁ {duration} ଧରି {location}ରେ ଯନ୍ତ୍ରଣା ହେଉଛି। "
                return f"Understood. Since this {clean_primary} has been present for {duration} in your {location}: "
            elif duration:
                if lang_code == "hi-IN":
                    return f"जैसा कि आपने बताया कि यह {duration} से है, "
                elif lang_code == "te-IN":
                    return f"మీరు చెప్పినట్లు ఇది {duration} నుండి ఉంది, "
                elif lang_code == "or-IN":
                    return f"ଆପଣ କହିବା ଅନୁସାରେ ଏହା {duration} ଧରି ହେଉଛି, "
                return f"Noted that this began {duration} ago. "

        # 2. Questions regarding Severity / Intensity
        if "severity" in question_id or "scale" in question_id:
            if lang_code == "hi-IN":
                return f"इस {clean_primary} की गंभीरता समझने के लिए: "
            elif lang_code == "te-IN":
                return f"ఈ {clean_primary} తీవ్రతను అర్థం చేసుకోవడానికి: "
            elif lang_code == "or-IN":
                return f"ଏହି {clean_primary}ର ତୀବ୍ରତା ବୁଝିବା ପାଇଁ: "
            return f"To gauge how intense this {clean_primary} is right now: "

        # 3. Questions regarding Triggers & Relieving Factors
        if "trigger" in question_id or "aggravat" in question_id or "reliev" in question_id:
            if lang_code == "hi-IN":
                return f"यह जानने के लिए कि क्या चीज इसे बढ़ाती या घटाती है: "
            elif lang_code == "te-IN":
                return f"ఏది దీన్ని పెంచుతుందో లేదా తగ్గిస్తుందో తెలుసుకోవడానికి: "
            elif lang_code == "or-IN":
                return f"କେଉଁ କାରଣରୁ ଏହା ବଢ଼ୁଛି ବା କମୁଛି ଜାଣିବା ପାଇଁ: "
            return f"Regarding your {clean_primary}, to see what brings it on or eases it: "

        # 4. Questions regarding Pain Character / Quality
        if "character" in question_id or "type" in question_id:
            if lang_code == "hi-IN":
                return f"दर्द का स्वरूप समझने के लिए: "
            elif lang_code == "te-IN":
                return f"నొప్పి రకాన్ని స్పష్టంగా అర్థం చేసుకోవడానికి: "
            elif lang_code == "or-IN":
                return f"ଯନ୍ତ୍ରଣାର ପ୍ରକାର ବୁଝିବା ପାଇଁ: "
            return f"To understand the exact sensation of this {clean_primary}: "

        # 5. Questions regarding Medication History
        if "medication" in question_id or "med." in question_id or "drug" in question_id:
            if lang_code == "hi-IN":
                return f"डॉक्टर द्वारा सुरक्षित परामर्श और दवा समीक्षा के लिए: "
            elif lang_code == "te-IN":
                return f"వైద్యుల సురక్షిత చికిత్స మరియు ఔషధ సమీక్ష కోసం: "
            elif lang_code == "or-IN":
                return f"ଡାକ୍ତରଙ୍କ ସଠିକ୍ ପରାମର୍ଶ ଏବଂ ଔଷଧ ଯାଞ୍ଚ ପାଇଁ: "
            return f"For your attending physician to safely review your treatment profile: "

        # 6. Questions regarding Allergies
        if "allergy" in question_id:
            if lang_code == "hi-IN":
                return f"आपकी सुरक्षा और सही दवा चयन के लिए: "
            elif lang_code == "te-IN":
                return f"మీ భద్రత మరియు సరైన ఔషధ ఎంపిక కోసం: "
            elif lang_code == "or-IN":
                return f"ଆପଣଙ୍କ ସୁରକ୍ଷା ଏବଂ ସଠିକ୍ ଔଷଧ ନିର୍ଦ୍ଧାରଣ ପାଇଁ: "
            return f"To prevent any adverse reactions with prescribed treatments: "

        # Default Duration Memory
        if duration and ("pattern" in question_id or "onset" in question_id):
            if lang_code == "hi-IN":
                return f"जैसा कि आपने बताया कि यह {duration} से है: "
            elif lang_code == "te-IN":
                return f"మీరు పేర్కొన్నట్లు ఇది {duration} నుండి ఉంది: "
            elif lang_code == "or-IN":
                return f"ଆପଣ କହିବା ଅନୁଯାୟୀ ଏହା {duration} ଧରି ହେଉଛି: "
            return f"You mentioned this has been present for {duration}: "

        return ""

    @classmethod
    def extract_complaints(cls, text: str) -> List[str]:
        """
        Extracts all presenting clinical complaints from patient statements,
        supporting multi-complaint presentations (e.g. 'I have fever, cough and weakness').
        """
        if not text:
            return []
        from .ontology import CLINICAL_ONTOLOGY
        t_low = text.lower()
        found = []
        for domain, pw in CLINICAL_ONTOLOGY.items():
            for pattern in pw.get("triggers", []):
                if re.search(pattern, t_low, re.IGNORECASE):
                    # Clean domain to friendly name e.g. fever, cough, weakness
                    name = domain
                    if domain == "weakness_fatigue":
                        name = "weakness"
                    elif domain == "urinary_symptoms":
                        name = "urinary symptoms"
                    elif domain == "throat_symptoms":
                        name = "sore throat"
                    elif domain == "diabetes_metabolic":
                        name = "diabetes"
                    elif domain == "hypertension_cardio":
                        name = "hypertension"
                    else:
                        name = domain.replace("_", " ")

                    if name not in found:
                        found.append(name)
                    break
        return found

    @classmethod
    def extract_from_text(
        cls,
        text: str,
        target_parameter: Optional[str] = None,
        language: str = "en-IN"
    ) -> Dict[str, Dict[str, Any]]:
        extractor = cls()
        res = extractor.extract_entities_from_text(text, target_parameter)
        extracted = res.get("extracted", {})
        conf = res.get("confidence", 0.85)

        # Check for multiple complaints in the utterance
        complaints = cls.extract_complaints(text)
        if complaints and "chief_complaints" not in extracted:
            extracted["chief_complaints"] = complaints

        out = {}
        for k, v in extracted.items():
            out[k] = {
                "value": v,
                "confidence": conf,
                "raw_text": text
            }
        return out
