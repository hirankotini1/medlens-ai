"""
MedLens Clinical Interview Engine — Red Flag Engine
Detects critical red-flag symptoms across 5+ Indian languages, pauses routine questioning,
sets triage urgency to CRITICAL/HIGH, and provides safe, non-diagnostic patient instructions.
"""

from typing import Dict, Any, List, Optional
import re

RED_FLAG_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "id": "RF_CHEST_PAIN_ACUTE",
        "category": "cardiac",
        "urgency": "CRITICAL",
        "keywords": {
            "en-IN": ["chest pain", "crushing chest", "pressure in chest", "left arm numbness", "jaw pain", "sweating chest"],
            "hi-IN": ["छाती में दर्द", "सीने में दर्द", "छाती पर भारीपन", "सीने में भारीपन", "बाएं हाथ में दर्द", "सीना जकड़ना"],
            "te-IN": ["ఛాతీ నొప్పి", "గుండె నొప్పి", "ఛాతీలో బరువు", "ఎడమ చేయి నొప్పి"],
            "or-IN": ["ଛାତି ଯନ୍ତ୍ରଣା", "ଛାତି ଦରଜ", "ଛାତିରେ ଭାରୀ ଲାଗିବା", "ବାମ ହାତ ଯନ୍ତ୍ରଣା"],
            "ta-IN": ["மார்பு வலி", "நெஞ்சு வலி", "இடது கை வலி"]
        },
        "instruction": {
            "en-IN": "⚠️ Immediate Attention Required: Please sit down calmly, avoid exertion, and have someone contact emergency services (108/112) or reach the nearest hospital emergency room immediately.",
            "hi-IN": "⚠️ तत्काल ध्यान आवश्यक: कृपया शांति से बैठें, कोई परिश्रम न करें, और तुरंत 108/112 पर आपातकालीन सेवा या नजदीकी अस्पताल के आपातकालीन कक्ष से संपर्क करें।",
            "te-IN": "⚠️ అత్యవసర శ్రద్ధ అవసరం: దయచేసి ప్రశాంతంగా కూర్చోండి, శ్రమించవద్దు మరియు వెంటనే అత్యవసర సేవలను (108/112) సంప్రదించండి లేదా ఆసుపత్రికి వెళ్ళండి.",
            "or-IN": "⚠️ ତୁରନ୍ତ ଡାକ୍ତରୀ ଧ୍ୟାନ ଆବଶ୍ୟକ: ଦୟାକରି ଶାନ୍ତ ଭାବରେ ବସନ୍ତୁ, କୌଣସି ପରିଶ୍ରମ କରନ୍ତୁ ନାହିଁ ଏବଂ ତୁରନ୍ତ 108/112 ଡାକନ୍ତୁ କିମ୍ବା ନିକଟସ୍ଥ ଡାକ୍ତରଖାନାକୁ ଯାଆନ୍ତୁ।",
            "ta-IN": "⚠️ அவசர உதவி தேவை: தயவுசெய்து அமைதியாக உட்காரவும், உடனே அவசர சிகிச்சைப் பிரிவை அணுகவும்."
        },
        "physician_alert": "Acute crushing chest pain or potential ischemic symptoms reported. Immediate ECG and cardiac enzyme evaluation indicated."
    },
    {
        "id": "RF_BREATHLESSNESS_SEVERE",
        "category": "respiratory",
        "urgency": "CRITICAL",
        "keywords": {
            "en-IN": ["gasping", "cannot breathe", "severe breathlessness", "stridor", "turning blue", "suffocating"],
            "hi-IN": ["सांस नहीं ले पा रहा", "दम घुट रहा है", "गंभीर सांस फूलना", "सांस रुकना", "नीला पड़ना"],
            "te-IN": ["శ్వాస ఆడట్లేదు", "తీవ్రమైన ఆయాసం", "ఊపిరి ఆడట్లేదు", "శ్వాస తీసుకోవడంలో తీవ్ర ఇబ్బంది"],
            "or-IN": ["ନିଶ୍ୱାସ ନେଇପାରୁନାହିଁ", "ଦମ ବନ୍ଦ ହେଉଛି", "ଅଣନିଶ୍ୱାସୀ", "ଅତି ଭୀଷଣ କାଶ ସହ ନିଶ୍ୱାସ ବନ୍ଦ"],
            "ta-IN": ["மூச்சு திணறல்", "மூச்சு விட முடியவில்லை"]
        },
        "instruction": {
            "en-IN": "⚠️ Immediate Attention: Sit upright in a well-ventilated space. Do not lie flat. Seek emergency medical care immediately.",
            "hi-IN": "⚠️ तत्काल ध्यान: हवादार जगह पर सीधे बैठें। सीधे न लेटें। तुरंत आपातकालीन चिकित्सा सहायता लें।",
            "te-IN": "⚠️ అత్యవసర శ్రద్ధ: గాలి ఆడే ప్రదేశంలో నిటారుగా కూర్చోండి. వెంటనే అత్యవసర వైద్య సంరక్షణ పొందండి.",
            "or-IN": "⚠️ ତୁରନ୍ତ ଧ୍ୟାନ: ଖୋଲା ପବନ ଯାଗାରେ ସିଧା ହୋଇ ବସନ୍ତୁ। ଶୋଇବେ ନାହିଁ। ତୁରନ୍ତ ଜରୁରୀକାଳୀନ ଚିକିତ୍ସା ସେବା ନିଅନ୍ତୁ।",
            "ta-IN": "⚠️ அவசர உதவி: நேராக அமரவும். படுக்க வேண்டாம். உடனே மருத்துவரை அணுகவும்."
        },
        "physician_alert": "Severe acute dyspnea / respiratory distress. Oxygen saturation and airway management priority."
    },
    {
        "id": "RF_NEURO_STROKE_FAST",
        "category": "neurological",
        "urgency": "CRITICAL",
        "keywords": {
            "en-IN": ["face droop", "slurred speech", "paralysis", "sudden weakness in arm", "loss of speech", "facial asymmetry"],
            "hi-IN": ["मुंह टेढ़ा", "आवाज लड़खड़ाना", "एक तरफ कमजोरी", "बोल नहीं पा रहे", "अचानक लकवा"],
            "te-IN": ["ముఖం వంకర", "మాట తడబడటం", "ఒకవైపు పక్షవాతం", "మాట రాకపోవడం"],
            "or-IN": ["ମୁହଁ ବଙ୍କା", "କଥା ଝୁଣ୍ଟିବା", "ଗୋଟିଏ ପାଖ ଦୁର୍ବଳ", "ହଠାତ୍ ପକ୍ଷାଘାତ"],
            "ta-IN": ["முகம் கோணுதல்", "பேச்சு குளறுபடி", "பக்கவாதம்"]
        },
        "instruction": {
            "en-IN": "⚠️ Emergency Alert: Potential stroke warning signs detected. Note the exact time symptoms began. Do not eat or drink anything. Reach a stroke-ready center immediately.",
            "hi-IN": "⚠️ आपातकालीन अलर्ट: संभावित स्ट्रोक के लक्षण। लक्षण कब शुरू हुए समय नोट करें। कुछ भी खाएं-पिएं नहीं। तुरंत अस्पताल पहुंचें।",
            "te-IN": "⚠️ ఎమర్జెన్సీ అలర్ట్: పక్షవాతం లక్షణాలు గమనించబడ్డాయి. లక్షణాలు ప్రారంభమైన సమయాన్ని గుర్తించండి. వెంటనే ఆసుపత్రికి వెళ్ళండి.",
            "or-IN": "⚠️ ଜରୁରୀକାଳୀନ ସୂଚନା: ଷ୍ଟ୍ରୋକ୍ (Stroke) ର ଲକ୍ଷଣ ହୋଇପାରେ। ଖାଇବା ବା ପିଇବା ବନ୍ଦ ରଖନ୍ତୁ ଏବଂ ତୁରନ୍ତ ଷ୍ଟ୍ରୋକ୍ ଚିକିତ୍ସା ଥିବା ଡାକ୍ତରଖାନାକୁ ଯାଆନ୍ତୁ।",
            "ta-IN": "⚠️ பக்கவாத எச்சரிக்கை: உடனே ஸ்ட்ரோக் மையத்திற்கு செல்லவும்."
        },
        "physician_alert": "Suspected acute focal neurological deficit (FAST positive). Assess time of onset for thrombolysis window."
    },
    {
        "id": "RF_HEMORRHAGE_MASSIVE",
        "category": "vascular",
        "urgency": "CRITICAL",
        "keywords": {
            "en-IN": ["coughing up blood", "vomiting blood", "black tarry stool", "profuse bleeding", "massive blood"],
            "hi-IN": ["खून की उल्टी", "खांसी में खून", "काला मल", "भारी रक्तस्राव"],
            "te-IN": ["రక్తం వాంతులు", "దగ్గులో రక్తం", "నల్లటి మలం", "రక్తస్రావం"],
            "or-IN": ["ରକ୍ତ ବାନ୍ତି", "ଖାସରେ ରକ୍ତ", "କଳା ଝାଡ଼ା", "ଅତ୍ୟଧିକ ରକ୍ତସ୍ରାବ"],
            "ta-IN": ["ரத்த வாந்தி", "இருமல் ரத்தம்"]
        },
        "instruction": {
            "en-IN": "⚠️ Immediate Attention: Active acute blood loss. Please lie down with legs slightly elevated if feeling dizzy, and go to the nearest emergency facility immediately.",
            "hi-IN": "⚠️ तत्काल ध्यान: सक्रिय रक्तस्राव। यदि चक्कर आ रहे हों तो पैरों को थोड़ा ऊपर उठाकर लेटें और तुरंत अस्पताल जाएं।",
            "te-IN": "⚠️ అత్యవసర శ్రద్ధ: తీవ్ర రక్తస్రావం. వెంటనే అత్యవసర విభాగానికి వెళ్ళండి.",
            "or-IN": "⚠️ ତୁରନ୍ତ ଧ୍ୟାନ: ଅତ୍ୟଧିକ ରକ୍ତସ୍ରାବ। ମୁଣ୍ଡ ଘୁରାଉଥିଲେ ଶୋଇ ରୁହନ୍ତୁ ଏବଂ ତୁରନ୍ତ ଜରୁରୀକାଳୀନ ଚିକିତ୍ସାଳୟକୁ ଯାଆନ୍ତୁ।",
            "ta-IN": "⚠️ உடனடி கவனம்: ரத்தப்போக்கு உள்ளது, அவசரமாக மருத்துவமனைக்கு செல்லவும்."
        },
        "physician_alert": "Acute gastrointestinal hemorrhage or hemoptysis reported. Evaluate hemodynamics and crossmatch."
    },
    {
        "id": "RF_THUNDERCLAP_HEADACHE",
        "category": "neurological",
        "urgency": "CRITICAL",
        "keywords": {
            "en-IN": ["worst headache of my life", "thunderclap headache", "sudden severe headache with stiff neck"],
            "hi-IN": ["जिंदगी का सबसे भयानक सिरदर्द", "अचानक भयंकर सिरदर्द", "गर्दन में अकड़न के साथ सिरदर्द"],
            "te-IN": ["జీవితంలో అత్యంత తీవ్రమైన తలనొప్పి", "అకస్మాత్తుగా భయంకరమైన తలనొప్పి"],
            "or-IN": ["ଜୀବନର ସବୁଠୁ ଭୟଙ୍କର ମୁଣ୍ଡବିନ୍ଧା", "ହଠାତ୍ ପ୍ରଚଣ୍ଡ ମୁଣ୍ଡବିନ୍ଧା ସହ ବେକ ଟାଣ"],
            "ta-IN": ["கடுமையான தலைவலி", "திடீர் தலைவலி"]
        },
        "instruction": {
            "en-IN": "⚠️ Immediate Attention: Severe sudden headache requires immediate neurological evaluation. Seek emergency care right away.",
            "hi-IN": "⚠️ तत्काल ध्यान: अचानक तेज सिरदर्द के लिए तत्काल जांच जरूरी है। तुरंत आपातकालीन कक्ष जाएं।",
            "te-IN": "⚠️ అత్యవసర శ్రద్ధ: తీవ్రమైన ఆకస్మిక తలనొప్పికి వెంటనే అత్యవసర చికిత్స అవసరం.",
            "or-IN": "⚠️ ତୁରନ୍ତ ଧ୍ୟାନ: ହଠାତ୍ ପ୍ରଚଣ୍ଡ ମୁଣ୍ଡବିନ୍ଧା ପାଇଁ ତୁରନ୍ତ ଡାକ୍ତରୀ ପରୀକ୍ଷା ଆବଶ୍ୟକ। ଜରୁରୀକାଳୀନ ବିଭାଗକୁ ଯାଆନ୍ତୁ।",
            "ta-IN": "⚠️ உடனடி கவனம்: உடனடி மருத்துவ பரிசோதனை தேவை."
        },
        "physician_alert": "Thunderclap headache. Rule out Subarachnoid Hemorrhage (SAH) or cerebral venous sinus thrombosis."
    },
    {
        "id": "RF_ANAPHYLAXIS",
        "category": "allergy",
        "urgency": "CRITICAL",
        "keywords": {
            "en-IN": ["swollen throat", "tongue swelling", "hives with breathing difficulty", "anaphylaxis", "throat closing"],
            "hi-IN": ["गला सूज गया", "जीभ में सूजन", "सांस लेने में दिक्कत और चकत्ते", "गला बंद होना"],
            "te-IN": ["గొంతు వాపు", "నాలుక వాపు", "దద్దుర్లు మరియు శ్వాసలో ఇబ్బంది"],
            "or-IN": ["ଗଳା ଫୁଲିଯିବା", "ଜିଭ ଫୁଲିବା", "ଚମରେ ଫୋଟକା ସହ ନିଶ୍ୱାସ କଷ୍ଟ"],
            "ta-IN": ["தொண்டை வீக்கம்", "நாக்கு வீக்கம்"]
        },
        "instruction": {
            "en-IN": "⚠️ Emergency Alert: Suspected severe allergic reaction / anaphylaxis. Administer epinephrine auto-injector if prescribed, and call emergency services right away.",
            "hi-IN": "⚠️ आपातकालीन अलर्ट: गंभीर एलर्जी प्रतिक्रिया। यदि ऑटो-इंजेक्टर है तो प्रयोग करें और तुरंत 108/112 पर कॉल करें।",
            "te-IN": "⚠️ ఎమర్జెన్సీ అలర్ట్: తీవ్రమైన అలెర్జీ ప్రతిచర్య. వెంటనే అత్యవసర సేవలను పిలవండి.",
            "or-IN": "⚠️ ଜରୁରୀକାଳୀନ ସୂଚନା: ପ୍ରଚଣ୍ଡ ଆଲର୍ଜି ପ୍ରତିକ୍ରିୟା। ତୁରନ୍ତ ଜରୁରୀକାଳୀନ ସେବା 108 କୁ କଲ୍ କରନ୍ତୁ।",
            "ta-IN": "⚠️ தீவிர ஒவ்வாமை எச்சரிக்கை: அவசர ஊர்தியை அழைக்கவும்."
        },
        "physician_alert": "Suspected systemic anaphylaxis. IM Epinephrine 1:1000 protocol recommended."
    }
]


class RedFlagEngine:
    """Detects emergency clinical red flags, pauses questioning, and alerts triage."""

    @classmethod
    def evaluate(cls, text: str, current_language: str = "en-IN") -> Optional[Dict[str, Any]]:
        """
        Scans input text across all supported language patterns for red flags.
        Returns match dict if found, else None.
        """
        if not text:
            return None

        normalized_text = text.lower().strip()

        for rf in RED_FLAG_DEFINITIONS:
            # Check all languages in case patient code switches (e.g. Hindi in English session)
            for lang, keywords in rf["keywords"].items():
                for kw in keywords:
                    if kw.lower() in normalized_text:
                        instruction_text = rf["instruction"].get(current_language) or rf["instruction"].get("en-IN")
                        return {
                            "flag_id": rf["id"],
                            "matched_keyword": kw,
                            "category": rf["category"],
                            "urgency": rf["urgency"],
                            "instruction": instruction_text,
                            "physician_alert": rf["physician_alert"],
                            "matched_language": lang,
                            "trigger_text": text
                        }

        return None

    @classmethod
    def format_interruption_response(cls, red_flag_match: Dict[str, Any], language: str = "en-IN") -> Dict[str, Any]:
        """
        Generates the interview response structure when a red flag interrupts questioning.
        """
        return {
            "status": "PAUSED_RED_FLAG",
            "is_emergency": True,
            "urgency": red_flag_match.get("urgency", "CRITICAL"),
            "red_flag": red_flag_match,
            "message": red_flag_match.get("instruction", "Critical symptoms reported. Immediate medical care advised."),
            "action_required": "SEEK_IMMEDIATE_CARE",
            "allow_minimal_continuation": True,  # Allows patient/clinician to confirm/clarify if not an acute 911 scenario
            "can_resume_prompt": {
                "en-IN": "If you are already in a hospital or safe, would you like to continue answering questions for your doctor's summary?",
                "hi-IN": "यदि आप पहले से ही अस्पताल या सुरक्षित स्थान पर हैं, क्या आप डॉक्टर के सारांश के लिए सवाल जारी रखना चाहते हैं?",
                "te-IN": "మీరు ఇప్పటికే ఆసుపత్రిలో లేదా సురక్షితంగా ఉంటే, డాక్టర్ సారాంశం కోసం ప్రశ్నలను కొనసాగించాలనుకుంటున్నారా?",
                "or-IN": "ଯଦି ଆପଣ ପୂର୍ବରୁ ଡାକ୍ତରଖାନାରେ ଅଛନ୍ତି ବା ସୁରକ୍ଷିତ ଅଛନ୍ତି, ଡାକ୍ତରଙ୍କ ପାଇଁ ପ୍ରଶ୍ନୋତ୍ତର ଜାରି ରଖିବାକୁ ଚାହାଁନ୍ତି କି?",
                "ta-IN": "நீங்கள் ஏற்கனவே மருத்துவமனையில் இருந்தால், வினாக்களை தொடர விரும்புகிறீர்களா?"
            }.get(language, "If you are in a safe clinical environment, would you like to continue?")
        }
