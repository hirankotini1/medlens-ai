"""
MEDLENS AI — Clinical Interview Ontology & Unified Question Bank (SIH PS 26047)
Canonical Medical Ontology covering 17 specialized complaint pathways + generic fallback.
"""

from typing import Dict, Any, List, Optional
import re

PRIORITY_P0 = "P0"  # Urgent / Red Flag Safety Check
PRIORITY_P1 = "P1"  # Essential Core History
PRIORITY_P2 = "P2"  # Supporting Diagnostic History
PRIORITY_P3 = "P3"  # Contextual & Risk History
PRIORITY_P4 = "P4"  # Optional Systemic Probes & Lifestyle

CLINICAL_ONTOLOGY: Dict[str, Dict[str, Any]] = {
    "chest_pain": {
        "domain": "chest_pain",
        "label": "Chest Pain & Cardiovascular Evaluation",
        "triggers": [
            r"\bchest\b", r"\bheart\b", r"\bcardiac\b", r"\bangina\b",
            r"छाती", r"हृदय", r"सीने में दर्द", r"గుండె", r"ఛాతీ", r"நெஞ்சு", r"ଛାତି", r"ହୃଦ"
        ],
        "hpi_fields": ["onset", "duration", "location", "character", "severity", "radiation", "exertional_rel", "associated_symptoms"],
        "ros_systems": ["cardiovascular", "respiratory", "gastrointestinal"],
        "red_flag_terms": ["left arm", "jaw", "shoulder", "heavy sweating", "diaphoresis", "unconscious", "crushing", "10/10"],
        "questions": [
            {
                "id": "hpi.chest.location_radiation",
                "priority": PRIORITY_P1,
                "state_key": "location_and_radiation",
                "text": {
                    "en-IN": "Where exactly is the chest discomfort, and does it radiate to your left arm, jaw, neck, shoulder, or back?",
                    "hi-IN": "सीने में दर्द ठीक कहाँ है? क्या यह आपके बाएं हाथ, जबड़े, गर्दन या पीठ में फैलता है?",
                    "te-IN": "ఛాతీలో నొప్పి సరిగ్గా ఎక్కడ ఉంది? ఇది ఎడమ చేయి, దవడ, మెడ లేదా వీపుకు వ్యాపిస్తుందా?",
                    "or-IN": "ଛାତିରେ ଯନ୍ତ୍ରଣା ଠିକ୍ କେଉଁଠି ହେଉଛି? ଏହା ବାମ ହାତ, ହନୁହାଡ଼, ବେକ ବା ପିଠିକୁ ଯାଉଛି କି?",
                    "ta-IN": "மார்பில் வலி எங்கு உள்ளது? இடது கை, தாடை அல்லது முதுகுக்கு பரவுகிறதா?"
                },
                "quick_picks": ["Left-sided chest radiating to left arm", "Center retrosternal crushing pressure", "Right-sided localized pain", "Radiates to neck/jaw", "No radiation / localized only"],
                "red_flag_triggers": ["left arm", "jaw", "shoulder", "back radiation"]
            }
        ]
    },

    "fever": {
        "domain": "fever",
        "label": "Fever & Infectious Disease Screening",
        "triggers": [
            r"\bfever\b", r"\btemperature\b", r"\bchills\b", r"\bshivering\b", r"\bpyrexia\b",
            r"बुखार", r"तापमान", r"ठंड", r"జ్వరం", r"చలి", r"காய்ச்சல்", r"ଜ୍ୱର", r"ଥଣ୍ଡା"
        ],
        "hpi_fields": ["onset", "duration", "pattern", "highest_temp", "rigors", "associated_symptoms"],
        "ros_systems": ["respiratory", "urinary", "gastrointestinal", "dermatological"],
        "red_flag_terms": ["104", "105", "stiff neck", "photophobia", "altered sensorium", "petechiae"],
        "questions": [
            {
                "id": "hpi.fever.pattern_temp",
                "priority": PRIORITY_P1,
                "state_key": "pattern_and_temperature",
                "text": {
                    "en-IN": "How high has the fever been, and does it stay continuous all day or come and go in spikes with shivering and chills?",
                    "hi-IN": "बुखार कितना तेज रहा है? क्या यह पूरे दिन लगातार रहता है या कंपकंपी के साथ आता-जाता है?",
                    "te-IN": "జ్వరం ఎంత ఉంది? రోజంతా నిరంతరం ఉంటుందా లేదా వణుకుతో వచ్చి పోతుందా?",
                    "or-IN": "ଜ୍ୱର କେତେ ଡିଗ୍ରୀ ରହୁଛି? ଏହା ଦିନସାରା ଲାଗି ରହୁଛି ନା ଥଣ୍ଡା ଓ କମ୍ପ ସହିତ ଆସୁଛି ଯାଉଛି?",
                    "ta-IN": "காய்ச்சல் எவ்வளவு அதிகமாக உள்ளது? நாள் முழுவதும் தொடர்கிறதா?"
                },
                "quick_picks": ["Continuous high fever (> 102°F)", "Comes in spikes with shivering", "Low grade (99-100°F)", "Not measured"],
                "red_flag_triggers": ["> 103", "104", "severe rigors"]
            }
        ]
    },

    "cough": {
        "domain": "cough",
        "label": "Cough & Respiratory Tract Evaluation",
        "triggers": [
            r"\bcough\b", r"\bsputum\b", r"\bphlegm\b", r"\bhemoptysis\b",
            r"खांसी", r"कफ", r"దగ్గు", r"இருமல்", r"କାଶ", r"କଫ"
        ],
        "hpi_fields": ["duration", "type", "sputum_color", "blood", "nocturnal"],
        "ros_systems": ["respiratory", "ent", "cardiovascular"],
        "red_flag_terms": ["coughing blood", "pink frothy sputum", "hemoptysis", "choking"],
        "questions": [
            {
                "id": "hpi.cough.type_sputum",
                "priority": PRIORITY_P1,
                "state_key": "cough_type_and_blood",
                "text": {
                    "en-IN": "Is the cough dry or productive with phlegm/sputum? Have you seen any traces of red blood or rust-colored phlegm?",
                    "hi-IN": "क्या खांसी सूखी है या कफ/बलगम वाली? क्या बलगम में खून दिखाई दिया है?",
                    "te-IN": "పొడి దగ్గా లేదా కఫంతో కూడిన దగ్గా? కఫంలో రక్తం పడిందా?",
                    "or-IN": "କାଶ ଶୁଖିଲା ନା କଫ ବାହାରୁଛି? କଫରେ କିଛି ରକ୍ତ ପଡୁଛି କି?",
                    "ta-IN": "வறட்டு இருமலா அல்லது சளி வருகிறதா? ரத்தம் உள்ளதா?"
                },
                "quick_picks": ["Dry irritating cough", "Productive with yellow/green phlegm", "Traces of red blood (Hemoptysis)", "Worse at night or lying down"],
                "red_flag_triggers": ["blood in sputum", "hemoptysis", "rust colored"]
            }
        ]
    },

    "breathlessness": {
        "domain": "breathlessness",
        "label": "Dyspnea & Cardiopulmonary Distress",
        "triggers": [
            r"\bbreath\b", r"\bdyspnea\b", r"\bsob\b", r"\bwheez\b", r"\bstridor\b",
            r"सांस फूलना", r"दम घुटना", r"శ్వాస ఆడట్లేదు", r"ఆయాసం", r"மூச்சு திணறல்", r"ଶ୍ୱାସ", r"ଅଣନିଶ୍ୱାସୀ"
        ],
        "hpi_fields": ["onset", "orthopnea", "pnd", "exertional_limit", "wheeze"],
        "ros_systems": ["respiratory", "cardiovascular"],
        "red_flag_terms": ["cannot speak in full sentences", "gasping", "cyanosis", "stridor", "blue lips"],
        "questions": [
            {
                "id": "hpi.breath.severity_positional",
                "priority": PRIORITY_P0,
                "state_key": "orthopnea_and_limit",
                "text": {
                    "en-IN": "Are you struggling to breathe while resting, unable to lie flat without pillows (orthopnea), or waking up choking at night?",
                    "hi-IN": "क्या बैठे-बैठे भी सांस लेने में कठिनाई हो रही है? क्या सीधे लेटने पर सांस फूलती है या रात में घबराहट से नींद खुलती है?",
                    "te-IN": "విశ్రాంతిలో కూడా శ్వాస తీసుకోవడం కష్టంగా ఉందా? నిద్రలో ఊపిరాడక మెలకువ వస్తుందా?",
                    "or-IN": "ବସିଥିବା ସମୟରେ ମଧ୍ୟ ନିଶ୍ୱାସ ନେବା କଷ୍ଟ ହେଉଛି କି? ଶୋଇଲେ ଶ୍ୱାସ ବଢ଼ୁଛି କି?",
                    "ta-IN": "ஓய்வில் இருக்கும் போதும் மூச்சு திணறல் உள்ளதா?"
                },
                "quick_picks": ["Struggling at complete rest", "Short of breath on minimal walking", "Cannot lie flat without 2+ pillows", "Wheezing / Whistling sounds in chest"],
                "red_flag_triggers": ["struggling at rest", "gasping", "unable to speak full sentences"]
            }
        ]
    },

    "abdominal_pain": {
        "domain": "abdominal_pain",
        "label": "Abdominal & Acute Abdomen Evaluation",
        "triggers": [
            r"\babdomen\b", r"\babdominal\b", r"\bstomach\b", r"\bbelly\b", r"\bgut\b",
            r"पेट दर्द", r"पेट में दर्द", r"కడుపు నొప్పి", r"വയറുവేదన", r"வயிறு வலி", r"ପେଟ ଯନ୍ତ୍ରଣା", r"ପେଟ ଦରଜ"
        ],
        "hpi_fields": ["location", "quadrant", "radiation", "meals_relationship", "guarding"],
        "ros_systems": ["gastrointestinal", "hepatobiliary", "urinary"],
        "red_flag_terms": ["rigid abdomen", "board-like", "rebound tenderness", "black stool", "hematemesis"],
        "questions": [
            {
                "id": "hpi.abd.location_quadrant",
                "priority": PRIORITY_P1,
                "state_key": "location_and_quadrant",
                "text": {
                    "en-IN": "Which part of your abdomen hurts most — upper right, upper center, lower right (appendix), lower center, or all over?",
                    "hi-IN": "पेट के किस हिस्से में सबसे ज्यादा दर्द है — ऊपर दाईं ओर, बीच में, नीचे दाईं तरफ, या पूरे पेट में?",
                    "te-IN": "కడుపులో ఏ భాగంలో ఎక్కువ నొప్పి ఉంది?",
                    "or-IN": "ପେଟର କେଉଁ ଅଂଶରେ ସବୁଠାରୁ ଅଧିକ ଯନ୍ତ୍ରଣା?",
                    "ta-IN": "வயிற்றில் எந்த பகுதியில் வலி அதிகமாக உள்ளது?"
                },
                "quick_picks": ["Upper center (Burning/Acidity)", "Right upper under ribs", "Right lower abdomen (Appendix concern)", "All over / Diffuse"],
                "red_flag_triggers": ["right lower quadrant acute", "board-like rigidity"]
            }
        ]
    },

    "headache": {
        "domain": "headache",
        "label": "Headache & Neurological Evaluation",
        "triggers": [
            r"\bheadache\b", r"\bhead ache\b", r"\bmigraine\b", r"\bcephalalgia\b",
            r"सिरदर्द", r"सिर दर्द", r"తలనొప్పి", r"தலைவலி", r"ମୁଣ୍ଡବିନ୍ଧା"
        ],
        "hpi_fields": ["onset", "location", "character", "aura", "neck_stiffness", "neuro_deficits"],
        "ros_systems": ["neurological", "ophthalmic", "ent"],
        "red_flag_terms": ["thunderclap", "worst headache of life", "slurred speech", "facial droop", "arm weakness"],
        "questions": [
            {
                "id": "hpi.headache.onset_severity",
                "priority": PRIORITY_P0,
                "state_key": "onset_and_worst_ever",
                "text": {
                    "en-IN": "Did this headache hit instantly like a thunderclap reaching maximum severity in seconds? Is this the worst headache of your life?",
                    "hi-IN": "क्या यह सिरदर्द बिजली के झटके की तरह अचानक सेकंडों में सबसे तेज हो गया?",
                    "te-IN": "ఈ తలనొప్పి పిడుగు పడినట్లు కొన్ని సెకన్లలోనే అత్యంత తీవ్రంగా మారిందా?",
                    "or-IN": "ଏହି ମୁଣ୍ଡବିନ୍ଧା ହଠାତ୍ ବିଜୁଳି ପରି ସେକେଣ୍ଡ ମଧ୍ୟରେ ଅସହ୍ୟ ହୋଇଗଲା କି?",
                    "ta-IN": "இந்த தலைவலி திடீரென உச்சக்கட்டத்தை அடைந்ததா?"
                },
                "quick_picks": ["Sudden explosive / Thunderclap", "Gradual throbbing one-sided", "Dull constant pressure band across head"],
                "red_flag_triggers": ["thunderclap", "worst headache of life", "sudden explosive"]
            }
        ]
    },

    "vomiting": {
        "domain": "vomiting",
        "label": "Nausea & Acute Emesis",
        "triggers": [
            r"\bvomit\b", r"\bnausea\b", r"\bemesis\b", r"\bpuke\b",
            r"उल्टी", r"मतली", r"వాంతి", r"వాంతులు", r"வாந்தி", r"ବାନ୍ତି"
        ],
        "hpi_fields": ["frequency", "contents", "blood", "hydration", "food_intake"],
        "ros_systems": ["gastrointestinal", "metabolic"],
        "red_flag_terms": ["blood in vomit", "coffee ground", "dehydration", "no urine"],
        "questions": [
            {
                "id": "hpi.vomit.frequency_hydration",
                "priority": PRIORITY_P1,
                "state_key": "frequency_and_hydration",
                "text": {
                    "en-IN": "How many times have you vomited in the past 24 hours, and are you able to keep any water down?",
                    "hi-IN": "पिछले 24 घंटों में कितनी बार उल्टी हुई है? क्या आप पानी रोक पा रहे हैं?",
                    "te-IN": "గత 24 గంటల్లో ఎన్నిసార్లు వాంతులు అయ్యాయి?",
                    "or-IN": "ଗତ ୨୪ ଘଣ୍ଟା ମଧ୍ୟରେ କେତେ ଥର ବାନ୍ତି ହୋଇଛି?",
                    "ta-IN": "கடந்த 24 மணி நேரத்தில் எத்தனை முறை வாந்தி எடுத்தீர்கள்?"
                },
                "quick_picks": ["Cannot keep any water down", "4 to 6 times", "1 to 3 times", "Blood in vomit"],
                "red_flag_triggers": ["cannot keep water down", "blood in vomit"]
            }
        ]
    },

    "diarrhea": {
        "domain": "diarrhea",
        "label": "Acute Diarrhea & Dysentery",
        "triggers": [
            r"\bdiarrhea\b", r"\bdiarrhoea\b", r"\bloose\s*motions?\b", r"\bloose\s*stools?\b", r"\bdysentery\b",
            r"दस्त", r"पतला दस्त", r"విరేచనాలు", r"పాచి", r"வயிற்றுப்போக்கு", r"ଝାଡ଼ା", r"ପତଳା ଝାଡ଼ା"
        ],
        "hpi_fields": ["frequency", "consistency", "blood_mucus", "cramps", "dehydration"],
        "ros_systems": ["gastrointestinal"],
        "red_flag_terms": ["rice water", "cholera-like", "profuse watery", "blood in stool"],
        "questions": [
            {
                "id": "hpi.diarrhea.nature_hydration",
                "priority": PRIORITY_P1,
                "state_key": "nature_and_dehydration",
                "text": {
                    "en-IN": "How frequent are the loose stools, is there any blood or mucus, and do you feel excessive thirst?",
                    "hi-IN": "दस्त कितनी बार हो रहे हैं? क्या मल में खून या आंव है?",
                    "te-IN": "విరేచనాలు ఎంత తరచుగా అవుతున్నాయి?",
                    "or-IN": "ପତଳା ଝାଡ଼ା କେତେ ଥର ହେଉଛି?",
                    "ta-IN": "மலம் எவ்வளவு அடிக்கடி போகிறது?"
                },
                "quick_picks": ["Profuse watery stools (> 8 times)", "Blood and mucus present", "3 to 5 times per day"],
                "red_flag_triggers": ["blood in stool", "profuse watery"]
            }
        ]
    },

    "urinary_symptoms": {
        "domain": "urinary_symptoms",
        "label": "Urinary Tract & Renal Evaluation",
        "triggers": [
            r"\burine\b", r"\burinat\w*", r"\bdysuria\b", r"\bhematuria\b", r"\bbladder\b", r"\bkidney\b",
            r"पेशाब", r"मूत्र", r"మూత్రం", r"சிறுநீர்", r"ପରିସ୍ରା"
        ],
        "hpi_fields": ["dysuria", "frequency", "urgency", "hematuria", "flank_pain", "fever_chills"],
        "ros_systems": ["urinary", "gastrointestinal"],
        "red_flag_terms": ["gross hematuria", "cannot pass urine", "anuria", "severe flank pain with fever"],
        "questions": [
            {
                "id": "hpi.urinary.burning_blood",
                "priority": PRIORITY_P1,
                "state_key": "burning_and_hematuria",
                "text": {
                    "en-IN": "Do you feel sharp burning when passing urine, have you seen any blood, or are you unable to pass urine?",
                    "hi-IN": "क्या पेशाब करते समय तेज जलन या दर्द होता है? क्या पेशाब में खून दिखा?",
                    "te-IN": "మూత్ర విసర్జన సమయంలో మంట లేదా నొప్పి ఉందా?",
                    "or-IN": "ପରିସ୍ରା କରିବା ସମୟରେ ପୋଡ଼ାଜଳା ବା ରକ୍ତ ପଡୁଛି କି?",
                    "ta-IN": "சிறுநீர் கழிக்கும் போது எரிச்சல் அல்லது ரத்தம் வருகிறதா?"
                },
                "quick_picks": ["Severe burning sensation", "Visible blood in urine", "Cannot pass urine at all", "Frequent urination"],
                "red_flag_triggers": ["cannot pass urine", "gross hematuria"]
            }
        ]
    },

    "dizziness": {
        "domain": "dizziness",
        "label": "Dizziness, Vertigo & Syncope",
        "triggers": [
            r"\bdizzy\b", r"\bdizziness\b", r"\bvertigo\b", r"\bspinning\b", r"\blightheaded\b", r"\bfaint\b",
            r"चक्कर", r"घूमना", r"కళ్ళు తిరగడం", r"తలతిరుగుడు", r"மயக்கம்", r"ଚକ୍କର", r"ମୁଣ୍ଡ ବୁଲାଇବା"
        ],
        "hpi_fields": ["type", "spinning_vs_faint", "head_turn_trigger", "tinnitus", "neuro_signs"],
        "ros_systems": ["neurological", "ent", "cardiovascular"],
        "red_flag_terms": ["stroke symptoms", "sudden deafness", "slurred speech", "loss of consciousness"],
        "questions": [
            {
                "id": "hpi.dizzy.character",
                "priority": PRIORITY_P1,
                "state_key": "vertigo_vs_lightheaded",
                "text": {
                    "en-IN": "Does the room feel like it is spinning around you (vertigo), or do you feel faint and like you are about to pass out?",
                    "hi-IN": "क्या कमरा आपके चारों ओर घूमता हुआ महसूस होता है?",
                    "te-IN": "గది మీ చుట్టూ తిరుగుతున్నట్లు అనిపిస్తుందా?",
                    "or-IN": "ଚାରିପାଖ ଘୂରିବା ପରି ଲାଗୁଛି କି?",
                    "ta-IN": "சுற்றுப்புறம் சுழல்வது போல் உள்ளதா?"
                },
                "quick_picks": ["Room spinning around (Vertigo)", "Feeling faint / Lightheaded on standing"],
                "red_flag_triggers": ["loss of consciousness", "slurred speech"]
            }
        ]
    },

    "joint_pain": {
        "domain": "joint_pain",
        "label": "Joint & Musculoskeletal Evaluation",
        "triggers": [
            r"\bjoints?\b", r"\bknees?\b", r"\barthritis\b", r"\bswelling\b", r"\bhip\b", r"\bshoulder\b", r"\bach\w*",
            r"जोड़ों में दर्द", r"घुटने", r"నొప్పులు", r"కీళ్ల నొప్పి", r"మూட்டு வலி", r"ଗଣ୍ଠି", r"ଆଣ୍ଠୁ"
        ],
        "hpi_fields": ["joints_involved", "morning_stiffness", "swelling_redness", "weight_bearing", "trauma"],
        "ros_systems": ["musculoskeletal", "rheumatological"],
        "red_flag_terms": ["hot red swollen joint", "septic arthritis", "cannot bear weight", "joint deformity"],
        "questions": [
            {
                "id": "hpi.joint.stiffness_swelling",
                "priority": PRIORITY_P1,
                "state_key": "stiffness_and_swelling",
                "text": {
                    "en-IN": "Which joints hurt, is there swelling or redness, and is there morning stiffness?",
                    "hi-IN": "किन जोड़ों में दर्द है? क्या सूजन या अकड़न है?",
                    "te-IN": "ఏ కీళ్లలో నొప్పి ఉంది? వాపు ఉందా?",
                    "or-IN": "କେଉଁ ଗଣ୍ଠିରେ ଯନ୍ତ୍ରଣା? ଫୁଲା ଅଛି କି?",
                    "ta-IN": "எந்த மூட்டுகளில் வலி உள்ளது?"
                },
                "quick_picks": ["Knees — worse on walking", "Hands/fingers with morning stiffness", "Single swollen joint"],
                "red_flag_triggers": ["hot red swollen joint", "cannot bear weight"]
            }
        ]
    },

    "back_pain": {
        "domain": "back_pain",
        "label": "Spine & Low Back Pathology",
        "triggers": [
            r"\bback\b", r"\bspine\b", r"\blumbar\b", r"\bsciatica\b", r"\blumbago\b",
            r"पीठ दर्द", r"कमर दर्द", r"నడుము నొప్పి", r"వీపు నొప్పి", r"முதுகு வலி", r"ଅଣ୍ଟା", r"ପିଠି ଦରଜ"
        ],
        "hpi_fields": ["location", "sciatica_radiation", "bowel_bladder", "numbness", "lifting_trigger"],
        "ros_systems": ["musculoskeletal", "neurological"],
        "red_flag_terms": ["cauda equina", "bowel incontinence", "bladder incontinence", "saddle anesthesia", "foot drop"],
        "questions": [
            {
                "id": "hpi.back.red_flags",
                "priority": PRIORITY_P0,
                "state_key": "red_flag_neuro",
                "text": {
                    "en-IN": "Have you noticed any loss of control over passing urine or stool, or numbness in the groin/seat area?",
                    "hi-IN": "क्या पेशाब या मल पर नियंत्रण खोने, या सुन्नपन की समस्या हुई है?",
                    "te-IN": "మూత్రం లేదా మలం ఆపుకోలేకపోవడం లాంటి సమస్య ఉందా?",
                    "or-IN": "ପରିସ୍ରା ବା ଝାଡ଼ା ରୋକିବାରେ ଅସୁବିଧା କିମ୍ବା ମାନ୍ଦାପଣ ଅଛି କି?",
                    "ta-IN": "சிறுநீர் அல்லது மலம் கட்டுப்பாடு இழந்துள்ளதா?"
                },
                "quick_picks": ["No bowel or bladder problems", "Pain shoots down back of leg past knee", "Numbness in groin area"],
                "red_flag_triggers": ["loss of urine control", "bowel incontinence", "groin numbness"]
            }
        ]
    },

    "skin_allergy": {
        "domain": "skin_allergy",
        "label": "Dermatology, Eczema & Urticaria",
        "triggers": [
            r"\bskin\b", r"\brash\b", r"\bitch\b", r"\bhives\b", r"\ballergy\b", r"\beczema\b",
            r"त्वचा", r"खुजली", r"चकत्ते", r"దద్దుర్లు", r"துடிப்பு", r"ଚର୍ମ ରୋଗ", r"ଯାଦୁ", r"କୁଣ୍ଡିଆ"
        ],
        "hpi_fields": ["distribution", "morphology", "itching", "mucosal", "triggers"],
        "ros_systems": ["dermatological", "immunological"],
        "red_flag_terms": ["lips swollen", "throat swelling", "peeling skin", "blistering all over", "stevens johnson"],
        "questions": [
            {
                "id": "hpi.skin.swelling_mucosa",
                "priority": PRIORITY_P0,
                "state_key": "anaphylaxis_and_peeling",
                "text": {
                    "en-IN": "Along with the rash, do you have any swelling of lips, eyes, or tongue, or difficulty breathing?",
                    "hi-IN": "क्या दाने के साथ होंठ, आंख या जीभ में सूजन है, या सांस लेने में परेशानी है?",
                    "te-IN": "దద్దుర్లతో పాటు పెదవులు, కళ్ళు లేదా నాలుక వాపు ఉందా?",
                    "or-IN": "ଚମରେ ଦାଗ ସହିତ ଓଠ, ଆଖି ବା ଜିଭ ଫୁଲିଛି କି?",
                    "ta-IN": "சொறியுடன் உதடு அல்லது நாக்கு வீக்கம் உள்ளதா?"
                },
                "quick_picks": ["No facial or throat swelling", "Swelling of lips or eyes", "Throat feels tight / breathing affected"],
                "red_flag_triggers": ["throat tightness", "lip swelling", "tongue swelling"]
            }
        ]
    },

    "diabetes_metabolic": {
        "domain": "diabetes_metabolic",
        "label": "Diabetes Mellitus & Metabolic Monitoring",
        "triggers": [
            r"\bdiabet\w*", r"\bsugar\b", r"\bglucose\b", r"\bhba1c\b", r"\bpolydipsia\b",
            r"मधुमेह", r"शुगर", r"డయాబెటిస్", r"చక్కెర వ్యాధి", r"சர்க்கரை", r"ମଧୁମେହ", r"ଚିନି ରୋଗ"
        ],
        "hpi_fields": ["glycemic_control", "hypoglycemia", "neuropathy_feet", "vision_changes", "meds_compliance"],
        "ros_systems": ["endocrine", "ophthalmic", "neurological", "nephrological"],
        "red_flag_terms": ["hypoglycemia collapse", "shaking sweating faint", "diabetic foot ulcer", "deep sighing breath"],
        "questions": [
            {
                "id": "hpi.diabetes.hypo_feet",
                "priority": PRIORITY_P1,
                "state_key": "hypoglycemia_and_feet",
                "text": {
                    "en-IN": "Do you ever get sudden episodes of severe shaking, cold sweats, and hunger (low sugar), or have numbness in your feet?",
                    "hi-IN": "क्या कभी अचानक कंपकंपी, ठंडा पसीना या अत्यधिक भूख (कम शुगर) के दौरे पड़ते हैं? पैरों में सुन्नपन है?",
                    "te-IN": "హఠాత్తుగా వణుకు, చల్లని చెమటలు, తీవ్రమైన ఆకలి (షుగర్ తగ్గడం) వస్తుందా? కాళ్లలో తిమ్మిరి ఉందా?",
                    "or-IN": "ହଠାତ୍ କମ୍ପ, ଥଣ୍ଡା ଝାଳ କିମ୍ବା ଭୋକ (ଲୋ ସୁଗାର) ଲାଗୁଛି କି? ପାଦରେ ମାନ୍ଦାପଣ ଅଛି କି?",
                    "ta-IN": "திடீர் நடுக்கம் அல்லது கால் மரத்து போதல் உள்ளதா?"
                },
                "quick_picks": ["Frequent episodes of low sugar (Hypoglycemia)", "Burning / Numbness in both feet", "Recent non-healing foot wound", "Well controlled without hypo symptoms"],
                "red_flag_triggers": ["non healing ulcer", "hypoglycemia seizure", "blackened toe"]
            }
        ]
    },

    "hypertension_cardio": {
        "domain": "hypertension_cardio",
        "label": "Hypertension & Vascular Surveillance",
        "triggers": [
            r"\bhypertension\b", r"\bbp\b", r"\bblood\s*pressure\b",
            r"हाई बीपी", r"रक्तचाप", r"రక్తపోటు", r"ஹை பிபி", r"ରକ୍ତଚାପ", r"ହାଇ ବିପି"
        ],
        "hpi_fields": ["recent_readings", "compliance", "headache_occipital", "blurred_vision", "pedal_edema"],
        "ros_systems": ["cardiovascular", "ophthalmic", "renal"],
        "red_flag_terms": ["bp over 180", "malignant hypertension", "chest tightness", "severe back of head pain"],
        "questions": [
            {
                "id": "hpi.htn.bp_compliance",
                "priority": PRIORITY_P1,
                "state_key": "bp_control_and_headache",
                "text": {
                    "en-IN": "What was your most recent BP reading, and are you experiencing throbbing morning headaches at the back of your head or blurred vision?",
                    "hi-IN": "आपकी हाल की बीपी रीडिंग क्या थी? क्या सिर के पिछले हिस्से में सुबह का तेज दर्द या धुंधला दिखाई देता है?",
                    "te-IN": "మీ ఇటీవలి బీపీ ఎంత ఉంది? ఉదయాన్నే తల వెనుక భాగంలో నొప్పి లేదా కంటి చూపు మసకబారడం ఉందా?",
                    "or-IN": "ଆପଣଙ୍କର ନିକଟତମ ବିପି କେତେ ଥିଲା? ସକାଳେ ମୁଣ୍ଡର ପଛ ପାଖ ବିନ୍ଧିବା ବା ଝାପ୍‌ସା ଦେଖାଯାଉଛି କି?",
                    "ta-IN": "சமீபத்திய இரத்த அழுத்த அளவு என்ன?"
                },
                "quick_picks": ["BP > 160/100 mmHg on check", "Morning occipital headache", "Blurred or dimming vision", "Taking BP tablets regularly without issues"],
                "red_flag_triggers": ["bp over 180", "hypertensive crisis"]
            }
        ]
    },

    "throat_symptoms": {
        "domain": "throat_symptoms",
        "label": "ENT, Pharyngitis & Tonsillar Evaluation",
        "triggers": [
            r"\bthroat\b", r"\bswallow\b", r"\bpharyngitis\b", r"\btonsil\b", r"\bhoarse\b",
            r"गले में दर्द", r"गला खराब", r"గొంతు నొప్పి", r"தொண்டை வலி", r"ଗଳା ଯନ୍ତ୍ରଣା", r"ଗଳା ଖରାପ"
        ],
        "hpi_fields": ["pain_swallowing", "drooling", "voice_change", "ear_pain"],
        "ros_systems": ["ent", "respiratory"],
        "red_flag_terms": ["cannot swallow saliva", "drooling", "stridor", "trismus", "unable to open mouth"],
        "questions": [
            {
                "id": "hpi.throat.swallow_airway",
                "priority": PRIORITY_P0,
                "state_key": "airway_and_swallowing",
                "text": {
                    "en-IN": "Can you swallow your own saliva, or are you drooling, unable to open your mouth (trismus), or having breathing sounds (stridor)?",
                    "hi-IN": "क्या आप थूक निगल पा रहे हैं, या मुंह खोलने और सांस लेने में दिक्कत हो रही है?",
                    "te-IN": "లాలాజలం మింగలేకపోవడం లేదా నోరు తెరవడం కష్టంగా ఉందా?",
                    "or-IN": "ଛେପ ଢୋକିବାରେ ଅସୁବିଧା ହେଉଛି କି?",
                    "ta-IN": "எச்சில் முழுங்குவதில் சிரமம் உள்ளதா?"
                },
                "quick_picks": ["Mild to moderate throat pain on swallowing", "Cannot swallow even saliva / Drooling", "Severe ear pain referred from throat", "Normal voice / Hoarseness present"],
                "red_flag_triggers": ["cannot swallow saliva", "drooling", "unable to open mouth", "stridor"]
            }
        ]
    },

    "weakness_fatigue": {
        "domain": "weakness_fatigue",
        "label": "Systemic Weakness, Fatigue & Anemia Screening",
        "triggers": [
            r"\bweak\w*", r"\bfatigue\b", r"\btired\b", r"\bexhaust\w*", r"\bletharg\w*", r"\banemia\b",
            r"कमजोरी", r"थकान", r"అలసట", r"బలహీనత", r"சோர்வு", r"ଦୁର୍ବଳତା", r"କ୍ଳାନ୍ତ"
        ],
        "hpi_fields": ["duration", "exertional_dyspnea", "pallor", "weight_loss", "dizziness"],
        "ros_systems": ["hematological", "endocrine", "cardiovascular"],
        "red_flag_terms": ["unexplained rapid weight loss", "severe pallor", "fainting on minimal effort"],
        "questions": [
            {
                "id": "hpi.fatigue.anemia_weight",
                "priority": PRIORITY_P1,
                "state_key": "fatigue_and_pallor",
                "text": {
                    "en-IN": "How long have you felt this weakness? Have you noticed pale skin/eyes, breathlessness on minor walking, or unexplained weight loss?",
                    "hi-IN": "यह कमजोरी कब से है? क्या आंखें या नाखून पीले पड़े हैं, हल्का चलने पर सांस फूलती है, या वजन कम हुआ है?",
                    "te-IN": "ఈ బలహీనత ఎంత కాలంగా ఉంది? కొద్దిగా నడిచినా ఆయాసం వస్తుందా, బరువు తగ్గిందా?",
                    "or-IN": "ଏହି ଦୁର୍ବଳତା କେତେ ଦିନରୁ ଲାଗୁଛି? ଟିକେ ଚାଲିଲେ ଶ୍ୱାସ ବଢୁଛି କି?",
                    "ta-IN": "இந்த சோர்வு எவ்வளவு நாட்களாக உள்ளது?"
                },
                "quick_picks": ["Extreme exhaustion", "Gradual fatigue with pale nails/eyes", "Worse after minimal activity"],
                "red_flag_triggers": ["unexplained rapid weight loss", "severe pallor"]
            }
        ]
    }
}

GENERIC_CLINICAL_PATHWAY: List[Dict[str, Any]] = [
    {
        "id": "hpi.generic.onset_duration",
        "priority": PRIORITY_P1,
        "state_key": "duration_and_onset",
        "text": {
            "en-IN": "Since when did this problem start, and did it begin suddenly within hours or gradually develop over days or weeks?",
            "hi-IN": "यह समस्या कब से शुरू हुई? क्या कुछ ही घंटों में अचानक आई या दिनों-हफ्तों में धीरे-धीरे बढ़ी?",
            "te-IN": "ఈ సమస్య ఎప్పటి నుండి మొదలైంది? కొన్ని గంటల్లో అకస్మాత్తుగా వచ్చిందా లేదా క్రమంగా పెరిగిందా?",
            "or-IN": "ଏହି ସମସ୍ୟା କେବେଠାରୁ ଆରମ୍ଭ ହୋଇଛି? ଏହା କିଛି ଘଣ୍ଟା ମଧ୍ୟରେ ହଠାତ୍ ଆସିଲା ନା ଧୀରେ ଧୀରେ ବଢ଼ିଲା?",
            "ta-IN": "இந்த பிரச்னை எப்போது தொடங்கியது? திடீரெனவா அல்லது மெதுவாகவா?"
        },
        "quick_picks": ["Started today (Acute)", "Past 2-3 days", "About 1-2 weeks ago", "Ongoing for months (Chronic)"]
    },
    {
        "id": "hpi.generic.location",
        "priority": PRIORITY_P1,
        "state_key": "location",
        "text": {
            "en-IN": "Where exactly on your body do you feel this discomfort or pain?",
            "hi-IN": "शरीर के किस हिस्से में यह तकलीफ या दर्द महसूस हो रहा है?",
            "te-IN": "మీ శరీరంలో సరిగ్గా ఎక్కడ నొప్పి లేదా అసౌకర్యం ఉంది?",
            "or-IN": "ଆପଣଙ୍କ ଶରୀରର ଠିକ୍ କେଉଁ ସ୍ଥାନରେ ଏହି କଷ୍ଟ ବା ଯନ୍ତ୍ରଣା ହେଉଛି?",
            "ta-IN": "உடலில் எந்த பகுதியில் வலி அல்லது அசௌகரியம் உள்ளது?"
        },
        "quick_picks": ["Localized to one spot", "All over body", "Right side", "Left side"]
    },
    {
        "id": "hpi.generic.character",
        "priority": PRIORITY_P2,
        "state_key": "character",
        "text": {
            "en-IN": "What does the discomfort feel like — is it sharp, dull aching, burning, throbbing, or heavy pressure?",
            "hi-IN": "दर्द कैसा महसूस होता है — तेज चुभन, हल्का मीठा दर्द, जलन, धड़कन जैसा, या भारीपन?",
            "te-IN": "నొప్పి ఎలా అనిపిస్తుంది — తీవ్రంగా, మంటగా, బరువుగా?",
            "or-IN": "ଯନ୍ତ୍ରଣା କିପରି ଲାଗୁଛି — ତୀକ୍ଷ୍ଣ, ପୋଡ଼ାଜଳା, ଧପ୍-ଧପ୍ ନା ଭାରୀ ବୋଝ ପରି?",
            "ta-IN": "வலி எந்த வகையில் உள்ளது — குத்துவது போல், எரிச்சல் அல்லது பாரமாகவா?"
        },
        "quick_picks": ["Dull continuous ache", "Sharp stabbing pain", "Burning sensation", "Throbbing / Pulsating", "Heavy pressure"]
    },
    {
        "id": "hpi.generic.radiation",
        "priority": PRIORITY_P2,
        "state_key": "radiation",
        "text": {
            "en-IN": "Does the discomfort stay in one place or spread/radiate to another part of your body?",
            "hi-IN": "क्या दर्द एक ही जगह रहता है या शरीर के किसी अन्य हिस्से में फैलता है?",
            "te-IN": "నొప్పి ఒకే చోట ఉంటుందా లేదా శరీరంలోని ఇతర భాగాలకు వ్యాపిస్తుందా?",
            "or-IN": "ଯନ୍ତ୍ରଣା ଗୋଟିଏ ସ୍ଥାନରେ ରହୁଛି ନା ଶରୀରର ଅନ୍ୟ ସ୍ଥାନକୁ ଯାଉଛି?",
            "ta-IN": "வலி ஒரே இடத்தில் உள்ளதா அல்லது வேறு இடத்திற்கு பரவுகிறதா?"
        },
        "quick_picks": ["Stays in one spot (No radiation)", "Spreads to back", "Spreads down arms/legs", "Spreads to neck/jaw"]
    },
    {
        "id": "hpi.generic.severity",
        "priority": PRIORITY_P1,
        "state_key": "severity",
        "text": {
            "en-IN": "On a scale from 1 to 10, how severe is your discomfort right now (1 = very mild, 10 = unbearable)?",
            "hi-IN": "1 से 10 के पैमाने पर, आपकी तकलीफ अभी कितनी तेज है (1 = बहुत हल्की, 10 = असहनीय)?",
            "te-IN": "1 నుండి 10 స్కేల్‌లో, మీ సమస్య ఇప్పుడు ఎంత తీవ్రంగా ఉంది (1 = చాలా తక్కువ, 10 = భరించలేనిది)?",
            "or-IN": "୧ ରୁ ୧୦ ମଧ୍ୟରେ, ଆପଣଙ୍କ କଷ୍ଟ ବା ଯନ୍ତ୍ରଣା ଏବେ କେତେ ତୀବ୍ର (୧ = ଖୁବ୍ ସାମାନ୍ୟ, ୧୦ = ଅସହ୍ୟ)?",
            "ta-IN": "1 முதல் 10 வரை, உங்கள் வலி எவ்வளவு தீவிரமாக உள்ளது?"
        },
        "quick_picks": ["1-3 (Mild discomfort)", "4-6 (Moderate)", "7-8 (Severe distress)", "9-10 (Unbearable pain)"]
    },
    {
        "id": "hpi.generic.triggers_relievers",
        "priority": PRIORITY_P2,
        "state_key": "aggravating_and_relieving",
        "text": {
            "en-IN": "Does anything specific make the problem better or worse, such as movement, food, rest, or taking medicine?",
            "hi-IN": "क्या किसी चीज से तकलीफ बढ़ती या घटती है — जैसे चलना, खाना, आराम करना, या कोई दवा लेना?",
            "te-IN": "ఏదైనా చేయడం వల్ల సమస్య ఎక్కువవుతుందా లేదా తగ్గుతుందా?",
            "or-IN": "କୌଣସି ନିର୍ଦ୍ଦିଷ୍ଟ କାରଣରୁ ଏହା ବଢ଼ୁଛି ବା କମୁଛି କି — ଚାଲିବା, ଖାଇବା ବା ବିଶ୍ରାମ ନେବା?",
            "ta-IN": "ஏதாவது செய்தால் வலி அதிகமாகிறதா அல்லது குறைகிறதா?"
        },
        "quick_picks": ["Better with rest", "Worse with physical movement", "Better after taking medicine", "No clear trigger"]
    },
    {
        "id": "hpi.generic.associated_symptoms",
        "priority": PRIORITY_P2,
        "state_key": "associated_symptoms",
        "text": {
            "en-IN": "Do you have any other symptoms along with this, like fever, nausea, dizziness, or weakness?",
            "hi-IN": "क्या इसके साथ कोई और लक्षण हैं जैसे बुखार, जी मिचलाना, चक्कर या कमजोरी?",
            "te-IN": "దీనితో పాటు జ్వరం, వికారం, కళ్ళు తిరగడం లేదా బలహీనత వంటి ఏవైనా ఇతర లక్షణాలు ఉన్నాయా?",
            "or-IN": "ଏହା ସହିତ ଆଉ କୌଣସି ଲକ୍ଷଣ ଅଛି କି — ଯେପରିକି ଜ୍ୱର, ବାନ୍ତି, ଚକ୍କର ବା ଦୁର୍ବଳତା?",
            "ta-IN": "இதனுடன் காய்ச்சல், மயக்கம் அல்லது சோர்வு போன்ற பிற அறிகுறிகள் உள்ளதா?"
        },
        "quick_picks": ["No other symptoms", "Mild fever", "Nausea or vomiting", "Feeling very weak"]
    }
]

SYSTEMIC_INQUIRY_MODULES: List[Dict[str, Any]] = [
    {
        "id": "pmh.chronic_illnesses",
        "priority": PRIORITY_P1,
        "category": "past_medical",
        "text": {
            "en-IN": "Have you ever been diagnosed with any major long-term medical conditions like Diabetes, High BP, Heart Disease, Kidney Disease, or Asthma?",
            "hi-IN": "क्या आपको पहले कोई पुरानी बीमारी हुई है जैसे डायबिटीज, हाई बीपी, हृदय रोग, किडनी रोग, या अस्थमा?",
            "te-IN": "మీకు గతంలో డయాబెటిస్, హై బీపీ, గుండె జబ్బు, కిడ్నీ సమస్య లేదా ఆస్తమా వంటి దీర్ଘకాలిక వ్యాధులు ఉన్నాయా?",
            "or-IN": "ଆପଣଙ୍କର ପୂର୍ବରୁ କୌଣସି ପୁରୁଣା ରୋଗ ହୋଇଛି କି — ମଧୁମେହ, ହାଇ ବିପି, ହୃଦରୋଗ, କିଡନୀ ରୋଗ ବା ଶ୍ୱାସ?",
            "ta-IN": "சர்க்கரை நோய், இரத்த அழுத்தம், இதய நோய் போன்ற நீண்டகால நோய்கள் உள்ளதா?"
        },
        "quick_picks": ["Diabetes Mellitus", "Hypertension (High BP)", "Coronary Heart Disease", "Asthma / Bronchitis", "None / No known conditions"]
    },
    {
        "id": "psh.prior_surgeries",
        "priority": PRIORITY_P2,
        "category": "past_surgical",
        "text": {
            "en-IN": "Have you undergone any surgeries, major operations, or hospital admissions in the past?",
            "hi-IN": "क्या पहले आपका कोई ऑपरेशन या सर्जरी हुई है? अस्पताल में भर्ती हुए हैं?",
            "te-IN": "మీకు గతంలో ఏదైనా శస్త్రచికిత్స లేదా ఆపరేషన్ జరిగిందా?",
            "or-IN": "ଆପଣଙ୍କର ପୂର୍ବରୁ କୌଣସି ଅପରେସନ ବା ସର୍ଜରୀ ହୋଇଛି କି?",
            "ta-IN": "கடந்த காலத்தில் ஏதேனும் அறுவை சிகிச்சை செய்துள்ளீர்களா?"
        },
        "quick_picks": ["Cesarean Section (C-Section)", "Appendectomy", "Gallbladder surgery", "Cardiac stenting / Bypass", "No past surgeries"]
    },
    {
        "id": "med.current_reconciliation",
        "priority": PRIORITY_P1,
        "category": "medications",
        "text": {
            "en-IN": "Are you currently taking any prescription tablets, injections, or regular medications? Please tell me their names and dosage if known.",
            "hi-IN": "क्या आप अभी कोई दवाइयां, गोलियां या इंजेक्शन ले रहे हैं? उनके नाम बताएं।",
            "te-IN": "మీరు ప్రస్తుతం ఏవైనా మందులు, ఇంజెక్షన్లు వాడుతున్నారా? వాటి పేర్లు చెప్పండి.",
            "or-IN": "ଆପଣ ବର୍ତ୍ତମାନ କୌଣସି ଔଷଧ, ଇଞ୍ଜେକ୍ସନ ଖାଉଛନ୍ତି କି? ସେଗୁଡ଼ିକର ନାମ କ'ଣ?",
            "ta-IN": "தற்போது ஏதேனும் மாத்திரைகள் அல்லது மருந்துகள் உட்கொள்கிறீர்களா?"
        },
        "quick_picks": ["Taking BP medicines", "Taking Diabetes tablets / Insulin", "Painkillers as needed", "Thyroid tablets", "Not taking any medications"]
    },
    {
        "id": "allergy.drug_reactions",
        "priority": PRIORITY_P1,
        "category": "allergies",
        "text": {
            "en-IN": "Are you allergic to any medicines like Penicillin, Sulfa drugs, or pain relievers? What reaction did you have?",
            "hi-IN": "क्या किसी दवाई से एलर्जी है जैसे पेनिसिलिन, सल्फा, या दर्द की दवा? क्या असर हुआ था?",
            "te-IN": "పెన్సిలిన్, సల్ఫా లేదా నొప్పి మందుల వల్ల మీకు ఏదైనా అలెర్జీ ఉందా? ఎలాంటి రియాక్షన్ వచ్చింది?",
            "or-IN": "ପେନିସିଲିନ୍, ସଲ୍ଫା ବା ଯନ୍ତ୍ରଣା ଔଷଧରୁ ଆପଣଙ୍କୁ କିଛି ଆଲର୍ଜି ଅଛି କି? କି ପ୍ରତିକ୍ରିୟା ହୋଇଥିଲା?",
            "ta-IN": "பெனிசிலின் அல்லது பிற மருந்துகளால் ஏதேனும் ஒவ்வாமை உள்ளதா?"
        },
        "quick_picks": ["Allergic to Penicillin (Rash / Swelling)", "Allergic to Sulfa drugs", "Allergic to Aspirin / NSAIDs", "Food / Peanut allergy", "No Known Drug Allergies (NKDA)"]
    }
]

def get_pathway_for_complaint(complaint_text: str) -> Optional[Dict[str, Any]]:
    """Identifies the best specialized clinical pathway matching a complaint."""
    if not complaint_text:
        return None

    text = complaint_text.lower()
    for pathway_id, pathway in CLINICAL_ONTOLOGY.items():
        for pattern in pathway["triggers"]:
            if re.search(pattern, text, re.IGNORECASE):
                return pathway

    return None

def get_generic_pathway() -> List[Dict[str, Any]]:
    """Returns the OPQRST generic clinical questions for non-specialized complaints."""
    return GENERIC_CLINICAL_PATHWAY
