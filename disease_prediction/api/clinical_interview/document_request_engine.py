"""
MEDLENS AI — Intelligent Document Request Engine
Evaluates patient responses and clinical state to identify when an uploaded
document (ECG, CBC, blood glucose, prescription, previous discharge summary, etc.)
would be clinically valuable, and suggests an optional upload prompt.

Safety & Design Principles:
1. Always optional: Never blocks clinical progression.
2. Contextually timed: Prompted when the patient explicitly references tests, prior care, or uncertain medications.
3. No duplicate prompts: Tracks requested, uploaded, and skipped documents.
4. Multilingual: Provides native prompts in English, Hindi, Telugu, and Odia.
"""

from typing import Dict, Any, Optional, List

class DocumentRequestEngine:
    """
    Analyzes patient dialogue and interview state to generate structured
    document upload recommendations.
    """

    # Keyword dictionaries for document categories
    TRIGGERS = {
        "ecg_report": {
            "id_prefix": "doc.ecg",
            "keywords": [
                "ecg", "ekg", "electrocardiogram", "echo", "echocardiogram",
                "treadmill test", "tmt", "heart report", "cardiac report",
                "ईसीजी", "इको", "గుండె పరీక్ష", "ఇసిజి", "ଇସିଜି"
            ],
            "reason": "The patient reported having a cardiac test or ECG related to the current complaint.",
            "urgency": "high",
            "messages": {
                "en-IN": "You mentioned having an ECG or cardiac test. If you have the report, you can upload it here for the doctor to review.",
                "hi-IN": "आपने ईसीजी या हृदय जांच का उल्लेख किया है। यदि आपके पास रिपोर्ट है, तो आप इसे डॉक्टर की समीक्षा के लिए यहां अपलोड कर सकते हैं।",
                "te-IN": "మీరు ECG లేదా గుండె పరీక్ష చేయించుకున్నట్లు పేర్కొన్నారు. మీ వద్ద రిపోర్ట్ ఉంటే, డాక్టర్ పరిశీలన కోసం ఇక్కడ అప్‌లోడ్ చేయవచ్చు.",
                "or-IN": "ଆପଣ ECG ବା ହୃଦରୋଗ ପରୀକ୍ଷା କଥା କହିଛନ୍ତି। ଯଦି ଆପଣଙ୍କ ପାଖରେ ରିପୋର୍ଟ ଅଛି, ତେବେ ଡାକ୍ତରବାବୁଙ୍କ ଦେଖିବା ପାଇଁ ଏଠାରେ ଅପଲୋଡ୍ କରିପାରିବେ।"
            }
        },
        "lab_report": {
            "id_prefix": "doc.lab",
            "keywords": [
                "cbc", "blood test", "blood report", "dengue test", "malaria test",
                "platelet", "hemoglobin", "wbc", "lft", "kft", "liver function",
                "kidney function", "urine test", "culture test",
                "खून की जांच", "रक्त परीक्षण", "బ్లడ్ టెస్ట్", "రక్త పరీక్ష", "ରକ୍ତ ପରୀକ୍ଷା"
            ],
            "reason": "The patient mentioned recent laboratory or blood work.",
            "urgency": "normal",
            "messages": {
                "en-IN": "You mentioned having a blood or lab test. If you have the report, you can upload it here.",
                "hi-IN": "आपने रक्त या लैब जांच का उल्लेख किया है। यदि आपके पास रिपोर्ट है, तो आप इसे यहां अपलोड कर सकते हैं।",
                "te-IN": "మీరు రక్త లేదా ల్యాబ్ పరీక్ష గురించి చెప్పారు. మీ వద్ద రిపోర్ట్ ఉంటే, ఇక్కడ అప్‌లోడ్ చేయవచ్చు.",
                "or-IN": "ଆପଣ ରକ୍ତ ବା ଲାବୋରେଟୋରୀ ପରୀକ୍ଷା ବିଷୟରେ କହିଛନ୍ତି। ଯଦି ଆପଣଙ୍କ ପାଖରେ ରିପୋର୍ଟ ଅଛି, ତେବେ ଏଠାରେ ଅପଲୋଡ୍ କରିପାରିବେ।"
            }
        },
        "glucose_report": {
            "id_prefix": "doc.glucose",
            "keywords": [
                "sugar test", "blood sugar", "glucose", "hba1c", "rbs", "fbs",
                "fasting sugar", "postprandial", "diabetes test",
                "शुगर की जांच", "डायबिटीज रिपोर्ट", "షుగర్ టెస్ట్", "ମଧୁମେହ ପରୀକ୍ଷା", "ଚିନି ପରୀକ୍ଷା"
            ],
            "reason": "The patient reported a recent blood glucose or HbA1c evaluation.",
            "urgency": "normal",
            "messages": {
                "en-IN": "If you have your recent blood sugar or HbA1c report, you can upload it here.",
                "hi-IN": "यदि आपके पास हाल की ब्लड शुगर या HbA1c रिपोर्ट है, तो आप इसे यहां अपलोड कर सकते हैं।",
                "te-IN": "మీ వద్ద ఇటీవలి బ్లడ్ షుగర్ లేదా HbA1c రిపోర్ట్ ఉంటే, ఇక్కడ అప్‌లోడ్ చేయవచ్చు.",
                "or-IN": "ଯଦି ଆପଣଙ୍କ ପାଖରେ ନିକଟରେ କରାଇଥିବା ବ୍ଲଡ ସୁଗାର ବା HbA1c ରିପୋର୍ଟ ଅଛି, ତେବେ ଏଠାରେ ଅପଲୋଡ୍ କରିପାରିବେ।"
            }
        },
        "prescription": {
            "id_prefix": "doc.rx",
            "keywords": [
                "prescription", "prescribed", "medicines given", "doctor gave medicines",
                "taking pills", "don't remember the medicine", "don't know the medicine name",
                "forgot the name", "strip", "parcha", "dawa",
                "डॉक्टर का पर्चा", "दवाई का पर्चा", "మందుల చీటీ", "డాక్టర్ ప్రిస్క్రిప్షన్", "ଡାକ୍ତରଙ୍କ ଚିଠା"
            ],
            "reason": "The patient mentioned active prescriptions or is uncertain about specific drug names.",
            "urgency": "normal",
            "messages": {
                "en-IN": "If you have your doctor's prescription or medicine list, you can upload it so medications and dosages can be recorded accurately.",
                "hi-IN": "यदि आपके पास डॉक्टर का पर्चा या दवाइयों की सूची है, तो आप इसे अपलोड कर सकते हैं ताकि दवाइयों और खुराक को सही ढंग से दर्ज किया जा सके।",
                "te-IN": "మీ వద్ద డాక్టర్ ప్రిస్క్రిప్షన్ లేదా మందుల జాబితా ఉంటే, ఖచ్చితమైన సమాచారం కోసం దాన్ని ఇక్కడ అప్‌లోడ్ చేయవచ్చు.",
                "or-IN": "ଯଦି ଆପଣଙ୍କ ପାଖରେ ଡାକ୍ତରଙ୍କ ପ୍ରେସକ୍ରିପସନ୍ ବା ଔଷଧ ତାଲିକା ଅଛି, ତେବେ ଠିକ୍ ମାତ୍ରା ଲେଖିବା ପାଇଁ ଆପଣ ଏଠାରେ ଅପଲୋଡ୍ କରିପାରିବେ।"
            }
        },
        "previous_diagnosis": {
            "id_prefix": "doc.prev_diag",
            "keywords": [
                "diagnosed with", "thyroid", "hypertension", "bp problem", "heart problem",
                "kidney problem", "asthma", "tb", "tuberculosis", "cancer",
                "पुरानी बीमारी", "थायरॉयड", "గత వ్యాధి", "థైరాయిడ్", "ପୂର୍ବ ରୋଗ"
            ],
            "reason": "The patient reported a pre-existing medical condition requiring clinical verification.",
            "urgency": "normal",
            "messages": {
                "en-IN": "If you have your previous medical report or diagnosis record, you can upload it to help verify your medical history.",
                "hi-IN": "यदि आपके पास अपनी पिछली बीमारी की रिपोर्ट या रिकॉर्ड है, तो आप इसे अपने मेडिकल इतिहास की पुष्टि के लिए अपलोड कर सकते हैं।",
                "te-IN": "మీ వద్ద మునుపటి వైద్య నివేదిక ఉంటే, మీ ఆరోగ్య చరిత్రను ధృవీకరించడానికి దాన్ని అప్‌లోడ్ చేయవచ్చు.",
                "or-IN": "ଯଦି ଆପଣଙ୍କ ପାଖରେ ପୂର୍ବ ରୋଗର ରିପୋର୍ଟ ଅଛି, ତେବେ ଡାକ୍ତରୀ ଇତିହାସ ନିଶ୍ଚିତ କରିବା ପାଇଁ ଅପଲୋଡ୍ କରିପାରିବେ।"
            }
        },
        "imaging_report": {
            "id_prefix": "doc.imaging",
            "keywords": [
                "x-ray", "xray", "ct scan", "mri", "ultrasound", "sonography", "usg",
                "एक्स-रे", "सीटी स्कैन", "एमआरआई", "ఎక్స్-రే", "సిటి స్కాన్", "ଏକ୍ସ-ରେ"
            ],
            "reason": "The patient mentioned recent diagnostic imaging or scans.",
            "urgency": "normal",
            "messages": {
                "en-IN": "You mentioned an X-Ray, Scan, or Ultrasound. If you have the report, you can upload it here.",
                "hi-IN": "आपने एक्स-रे, स्कैन या अल्ट्रासाउंड का उल्लेख किया है। यदि आपके पास रिपोर्ट है, तो आप इसे यहां अपलोड कर सकते हैं।",
                "te-IN": "మీరు ఎక్స్-రే లేదా స్కాన్ చేయించుకున్నట్లు చెప్పారు. మీ వద్ద రిపోర్ట్ ఉంటే, ఇక్కడ అప్‌లోడ్ చేయవచ్చు.",
                "or-IN": "ଆପଣ ଏକ୍ସ-ରେ ବା ସ୍କାନିଂ ବିଷୟରେ କହିଛନ୍ତି। ଯଦି ଆପଣଙ୍କ ପାଖରେ ରିପୋର୍ଟ ଅଛି, ତେବେ ଏଠାରେ ଅପଲୋଡ୍ କରିପାରିବେ।"
            }
        },
        "discharge_summary": {
            "id_prefix": "doc.discharge",
            "keywords": [
                "admitted", "hospital stay", "discharged", "discharge summary", "operation", "surgery",
                "अस्पताल में भर्ती", "डिस्चार्ज", "హాస్పిటల్లో చేరాను", "ଡାକ୍ତରଖାନାରେ ଭର୍ତ୍ତି"
            ],
            "reason": "The patient mentioned prior hospitalization or surgery.",
            "urgency": "normal",
            "messages": {
                "en-IN": "You mentioned being hospitalized. If you have the hospital discharge summary, you can upload it here.",
                "hi-IN": "आपने अस्पताल में भर्ती होने का उल्लेख किया है। यदि आपके पास डिस्चार्ज सारांश है, तो आप इसे यहां अपलोड कर सकते हैं।",
                "te-IN": "మీరు ఆసుపత్రిలో చేరినట్లు పేర్కొన్నారు. మీ వద్ద డిశ్చార్జ్ సమ్మరీ ఉంటే, ఇక్కడ అప్‌లోడ్ చేయవచ్చు.",
                "or-IN": "ଆପଣ ହସ୍ପିଟାଲରେ ଭର୍ତ୍ତି ହେବା କଥା କହିଛନ୍ତି। ଯଦି ଆପଣଙ୍କ ପାଖରେ ଡିସଚାର୍ଜ ସାରାଂଶ ଅଛି, ତେବେ ଏଠାରେ ଅପଲୋଡ୍ କରିପାରିବେ।"
            }
        }
    }

    @classmethod
    def evaluate_relevance(
        cls,
        state: Dict[str, Any],
        answer_text: str,
        current_language: str = "en-IN",
        extracted_entities: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Determines if a document upload request should be triggered based on:
        - Patient answer text
        - Extracted clinical entities
        - Active complaints and clinical pathway
        - Prior requested, uploaded, or skipped documents
        """
        if not answer_text or not answer_text.strip():
            return None

        lower_text = answer_text.lower()
        extracted = extracted_entities or {}

        # Retrieve tracked document lists from state
        doc_requests = state.get("document_requests", [])
        uploaded_docs = state.get("uploaded_documents", [])
        skipped_requests = state.get("skipped_document_requests", [])

        # Check existing uploaded document types
        uploaded_types = {d.get("document_type") for d in uploaded_docs if isinstance(d, dict)}
        already_requested_types = {r.get("request_type") for r in doc_requests if isinstance(r, dict)}
        skipped_types = set(skipped_requests)

        # Check triggers in priority order
        for doc_type, config in cls.TRIGGERS.items():
            # If already uploaded or skipped, do not repeat
            if doc_type in uploaded_types or doc_type in skipped_types:
                continue

            # Check if recently requested in this session
            if doc_type in already_requested_types:
                continue

            # Check keyword match in patient answer
            matched = any(kw in lower_text for kw in config["keywords"])

            # Check if extracted entities indicate this need
            if not matched:
                if doc_type == "prescription" and "medications" in extracted:
                    med_val = str(extracted["medications"].get("value", "")).lower()
                    if any(k in med_val for k in ["unknown", "forgot", "prescribed"]):
                        matched = True
                elif doc_type == "glucose_report" and any(k in lower_text for k in ["sugar", "diabetes", "diabetic"]):
                    if "glucose" in extracted or "hba1c" in extracted or "fasting" in lower_text:
                        matched = True

            if matched:
                req_id = f"{config['id_prefix']}.{len(doc_requests) + 1:03d}"
                lang_key = current_language if current_language in config["messages"] else "en-IN"
                msg_text = config["messages"].get(lang_key, config["messages"]["en-IN"])

                request_payload = {
                    "should_request": True,
                    "request_id": req_id,
                    "request_type": doc_type,
                    "reason": config["reason"],
                    "timing": "immediate",
                    "urgency": config["urgency"],
                    "message": config["messages"],
                    "display_prompt": msg_text,
                    "accept_label": "📎 Upload Document",
                    "skip_label": "Skip / Continue"
                }

                # Record in state
                cls.record_request(state, request_payload)
                return request_payload

        return None

    @classmethod
    def record_request(cls, state: Dict[str, Any], request_obj: Dict[str, Any]) -> None:
        """Records a document request in patient state to prevent duplicate prompts."""
        if "document_requests" not in state:
            state["document_requests"] = []
        state["document_requests"].append(request_obj)

    @classmethod
    def record_skip(cls, state: Dict[str, Any], request_id: str) -> None:
        """Records that the patient opted to skip an optional document request."""
        if "skipped_document_requests" not in state:
            state["skipped_document_requests"] = []
        if request_id not in state["skipped_document_requests"]:
            state["skipped_document_requests"].append(request_id)

    @classmethod
    def record_upload(cls, state: Dict[str, Any], doc_data: Dict[str, Any]) -> None:
        """Records an uploaded document in the interview state."""
        if "uploaded_documents" not in state:
            state["uploaded_documents"] = []
        state["uploaded_documents"].append(doc_data)
