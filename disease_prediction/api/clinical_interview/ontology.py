"""
MEDLENS AI — Clinical Interview Ontology & Unified Question Bank (SIH PS 26047)
Canonical Medical Ontology covering 17 specialized complaint pathways + systemic & AYUSH pathways.
Each pathway provides complete slot-based clinical questioning across:
- onset & duration
- anatomical location & radiation/quadrant
- character & sensation quality
- severity & progression
- triggers & relieving factors
- complaint-specific associated symptoms
- red flag emergency triage checks
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
            r"छाती", r"हृदय", r"सीने में दर्द", r"సీన\s*दर्द", r"గుండె", r"ఛాతీ", r"நெஞ்சு", r"ଛାତି", r"ହୃଦ",
            r"chhati\s*me\s*dard", r"chaati\s*dard", r"seena\s*dard", r"gunde\s*noppi", r"nenju\s*vali"
        ],
        "hpi_fields": ["onset", "duration", "location", "character", "severity", "radiation", "exertional_rel", "associated_symptoms"],
        "ros_systems": ["cardiovascular", "respiratory", "gastrointestinal"],
        "red_flag_terms": ["left arm", "jaw", "shoulder", "heavy sweating", "diaphoresis", "unconscious", "crushing", "10/10"],
        "questions": [
            {
                "id": "hpi.chest.location_radiation",
                "priority": PRIORITY_P1,
                "state_key": "location_and_radiation",
                "section": "Chest Pain Location",
                "why_asking": "Identifies exact chest location and radiation paths characteristic of cardiac ischemia.",
                "text": {
                    "en-IN": "Where exactly is the chest discomfort, and does it radiate to your left arm, jaw, neck, shoulder, or back?",
                    "hi-IN": "सीने में दर्द ठीक कहाँ है? क्या यह आपके बाएं हाथ, जबड़े, गर्दन या पीठ में फैलता है?",
                    "te-IN": "ఛాతీలో నొప్పి సరిగ్గా ఎక్కడ ఉంది? ఇది ఎడమ చేయి, దవడ, మెడ లేదా వీపుకు వ్యాపిస్తుందా?",
                    "or-IN": "ଛାତିରେ ଯନ୍ତ୍ରଣା ଠିକ୍ କେଉଁଠି ହେଉଛି? ଏହା ବାମ ହାତ, ହନୁହାଡ଼, ବେକ ବା ପିଠିକୁ ଯାଉଛି କି?",
                    "ta-IN": "மார்பில் வலி எங்கு உள்ளது? இடது கை, தாடை அல்லது முதுகுக்கு பரவுகிறதா?"
                },
                "quick_picks": ["Left-sided chest radiating to left arm", "Center retrosternal crushing pressure", "Right-sided localized pain", "Radiates to neck/jaw", "No radiation / localized only"],
                "red_flag_triggers": ["left arm", "jaw", "shoulder", "back radiation"]
            },
            {
                "id": "hpi.chest.character",
                "priority": PRIORITY_P1,
                "state_key": "character",
                "section": "Chest Pain Quality",
                "why_asking": "Differentiates ischemic heaviness/pressure from pleuritic or musculoskeletal sharpness.",
                "text": {
                    "en-IN": "How would you describe the feeling — is it heavy crushing pressure, sharp like a needle, burning like acidity, or an ache?",
                    "hi-IN": "दर्द का अहसास कैसा है — भारी दबाव या जकड़न, सुई जैसी चुभन, एसिडिटी जैसी जलन, या हल्का दर्द?",
                    "te-IN": "నొప్పి ఎలా అనిపిస్తుంది — తీవ్రమైన బరువు, సూదితో గుచ్చినట్లు, మంటగా లేదా సాధారణ నొప్పా?",
                    "or-IN": "ଯନ୍ତ୍ରଣା କିପରି ଲାଗୁଛି — ଛାତି ଉପରେ ଭାରୀ ଚାପ, ଛୁଞ୍ଚି ଭଳି ଫୋଡ଼ି ହେବା, ପୋଡ଼ାଜଳା ନା ମାନ୍ଦା ଦରଜ?",
                    "ta-IN": "வலி பாரமாக உள்ளதா, குத்துவது போல் உள்ளதா அல்லது எரிகிறதா?"
                },
                "quick_picks": ["Crushing heavy pressure / tight band", "Sharp stabbing pain", "Burning sensation / acid reflux", "Dull continuous ache"]
            },
            {
                "id": "hpi.chest.exertion",
                "priority": PRIORITY_P1,
                "state_key": "exertional_relationship",
                "section": "Exertional Relationship",
                "why_asking": "Assesses whether pain is brought on by physical exertion and relieved by rest (angina pattern).",
                "text": {
                    "en-IN": "Does physical effort like walking or climbing stairs worsen the pain, and does sitting to rest relieve it?",
                    "hi-IN": "क्या चलने या सीढ़ियां चढ़ने पर दर्द बढ़ता है और आराम करने से घटता है?",
                    "te-IN": "నడవడం లేదా మెట్లు ఎక్కడం వల్ల నొప్పి ఎక్కువవుతుందా, విశ్రాంతి తీసుకుంటే తగ్గుతుందా?",
                    "or-IN": "ଚାଲିବା ବା ସିଡ଼ି ଚଢ଼ିବା ଦ୍ୱାରା ଯନ୍ତ୍ରଣା ବଢୁଛି କି, ଏବଂ ବିଶ୍ରାମ ନେଲେ କମୁଛି କି?",
                    "ta-IN": "நடக்கும்போது வலி கூடுகிறதா, ஓய்வில் குறைகிறதா?"
                },
                "quick_picks": ["Yes, exertion definitely worsens it", "Relieved quickly with rest", "Occurs at rest / unrelated to exertion", "Worse when lying flat / after meals"]
            },
            {
                "id": "hpi.chest.associated",
                "priority": PRIORITY_P1,
                "state_key": "associated_symptoms",
                "section": "Associated Autonomic Features",
                "why_asking": "Identifies autonomic red flags (diaphoresis, nausea, dyspnea) associated with acute coronary syndrome.",
                "text": {
                    "en-IN": "Along with the chest pain, are you experiencing cold sweating, difficulty breathing, dizziness, or nausea?",
                    "hi-IN": "क्या सीने के दर्द के साथ ठंडा पसीना, सांस लेने में तकलीफ, चक्कर या उल्टी जैसा लग रहा है?",
                    "te-IN": "ఛాతీ నొప్పితో పాటు చల్లని చెమటలు, ఆయాసం, కళ్ళు తిరగడం లేదా వికారం ఉందా?",
                    "or-IN": "ଛାତି ଯନ୍ତ୍ରଣା ସହିତ ଝାଳ ବୋହିବା, ଶ୍ୱାସ କଷ୍ଟ, ମୁଣ୍ଡ ଘୁରାଇବା ବା ବାନ୍ତି ଲାଗୁଛି କି?",
                    "ta-IN": "மார்பு வலியுடன் வியர்வை, மூச்சு திணறல் அல்லது குமட்டல் உள்ளதா?"
                },
                "quick_picks": ["Profuse cold sweating (Diaphoresis)", "Shortness of breath / gasping", "Feeling lightheaded / dizzy", "No sweating or breathlessness"]
            }
        ]
    },

    "fever": {
        "domain": "fever",
        "label": "Fever & Infectious Disease Screening",
        "triggers": [
            r"\bfever\b", r"\btemperature\b", r"\bchills\b", r"\bshivering\b", r"\bpyrexia\b",
            r"बुखार", r"तापमान", r"ठंड", r"జ్వరం", r"చలి", r"காய்ச்சல்", r"ଜ୍ୱର", r"ଥଣ୍ଡା",
            r"bukhar", r"jwaram", r"jwar", r"jwara", r"taap"
        ],
        "hpi_fields": ["onset", "duration", "pattern", "highest_temp", "rigors", "associated_symptoms"],
        "ros_systems": ["respiratory", "urinary", "gastrointestinal", "dermatological"],
        "red_flag_terms": ["104", "105", "stiff neck", "photophobia", "altered sensorium", "petechiae"],
        "questions": [
            {
                "id": "hpi.fever.duration_onset",
                "priority": PRIORITY_P1,
                "state_key": "duration_and_onset",
                "section": "Fever Onset & Duration",
                "why_asking": "Determines infection chronicity and acute vs gradual progression.",
                "text": {
                    "en-IN": "How many days have you had the fever, and did it begin suddenly or develop gradually?",
                    "hi-IN": "बुखार कितने दिनों से है, और क्या यह अचानक आया या धीरे-धीरे बढ़ा?",
                    "te-IN": "జ్వరం ఎన్ని రోజులుగా ఉంది? అకస్మాత్తుగా వచ్చిందా లేదా క్రమంగా పెరిగిందా?",
                    "or-IN": "ଜ୍ୱର କେତେ ଦିନରୁ ହେଉଛି, ଏବଂ ଏହା ହଠାତ୍ ଆସିଲା ନା ଧୀରେ ଧୀରେ ବଢ଼ିଲା?",
                    "ta-IN": "காய்ச்சல் எத்தனை நாட்களாக உள்ளது? திடீரென தொடங்கியதா?"
                },
                "quick_picks": ["1-2 days (Recent onset)", "3-5 days", "1 week or longer", "Started today suddenly with chills"]
            },
            {
                "id": "hpi.fever.pattern_temp",
                "priority": PRIORITY_P1,
                "state_key": "pattern_and_temperature",
                "section": "Fever Spikes & Rigors",
                "why_asking": "Evaluates temperature magnitude and intermittent vs continuous spikes with rigors.",
                "text": {
                    "en-IN": "How high has the fever reached, and does it stay continuous all day or come and go in spikes with shivering and chills?",
                    "hi-IN": "बुखार कितना तेज रहा है? क्या यह पूरे दिन लगातार रहता है या कंपकंपी के साथ आता-जाता है?",
                    "te-IN": "జ్వరం ఎంత ఉంది? రోజంతా నిరంతరం ఉంటుందా లేదా వణుకుతో వచ్చి పోతుందా?",
                    "or-IN": "ଜ୍ୱର କେତେ ଡିଗ୍ରୀ ରହୁଛି? ଏହା ଦିନସାରା ଲାଗି ରହୁଛି ନା ଥଣ୍ଡା ଓ କମ୍ପ ସହିତ ଆସୁଛି ଯାଉଛି?",
                    "ta-IN": "காய்ச்சல் எவ்வளவு அதிகமாக உள்ளது? நாள் முழுவதும் தொடர்கிறதா?"
                },
                "quick_picks": ["Continuous high fever (> 102°F)", "Comes in spikes with shivering & chills", "Low grade (99-100°F)", "Not measured with thermometer"],
                "red_flag_triggers": ["> 103", "104", "severe rigors"]
            },
            {
                "id": "hpi.fever.associated",
                "priority": PRIORITY_P1,
                "state_key": "associated_symptoms",
                "section": "Associated Symptoms",
                "why_asking": "Screens for primary infection source: respiratory, gastrointestinal, urinary, or dengue/vector-borne.",
                "text": {
                    "en-IN": "Are you experiencing severe body ache, headache, cough, sore throat, or burning urination with the fever?",
                    "hi-IN": "क्या बुखार के साथ बदन दर्द, सिरदर्द, खांसी, गले में खराश या पेशाब में जलन है?",
                    "te-IN": "జ్వరంతో పాటు ఒళ్ళు నొప్పులు, తలనొప్పి, దగ్గు, గొంతు నొప్పి లేదా మూత్రంలో మంట ఉన్నాయా?",
                    "or-IN": "ଜ୍ୱର ସହିତ ଶରୀର ଯନ୍ତ୍ରଣା, ମୁଣ୍ଡବିନ୍ଧା, କାଶ, ଗଳା ଖରାପ ବା ପରିସ୍ରାରେ ପୋଡ଼ାଜଳା ହେଉଛି କି?",
                    "ta-IN": "காய்ச்சலுடன் உடல் வலி, தலைவலி, இருமல் அல்லது சிறுநீர் எரிச்சல் உள்ளதா?"
                },
                "quick_picks": ["Severe body ache & headache (Dengue/Flu)", "Cough & sore throat", "Burning sensation during urination", "Nausea, vomiting or abdominal pain"]
            },
            {
                "id": "hpi.fever.rash_warning",
                "priority": PRIORITY_P0,
                "state_key": "rash_and_bleeding",
                "section": "Fever Warning Signs",
                "why_asking": "Screens for dengue hemorrhagic warning signs, petechiae, or neck stiffness.",
                "text": {
                    "en-IN": "Have you noticed any red spots or rash on your skin, bleeding from gums/nose, pain behind your eyes, or stiff neck?",
                    "hi-IN": "क्या त्वचा पर लाल चकत्ते, मसूड़ों या नाक से खून, आंखों के पीछे दर्द, या गर्दन में अकड़न महसूस हुई है?",
                    "te-IN": "చర్మంపై ఎర్రటి మచ్చలు, చిగుళ్ల నుండి రక్తం, కళ్ళ వెనుక నొప్పి లేదా మెడ బిగుతుగా ఉండటం గమనించారా?",
                    "or-IN": "ଚର୍ମରେ ଲାଲ ଦାଗ, ମାଢ଼ି ବା ନାକରୁ ରକ୍ତ, ଆଖି ପଛରେ ଯନ୍ତ୍ରଣା ବା ବେକ ଟାଣ ହୋଇଛି କି?",
                    "ta-IN": "தோலில் தடிப்புகள், ஈறுகளில் ரத்தம் அல்லது கழுத்து விறைப்பு உள்ளதா?"
                },
                "quick_picks": ["Pain behind the eyes (Retro-orbital)", "Red rash / tiny red spots on skin", "Stiff neck and intolerance to light", "No rash, bleeding, or neck stiffness"],
                "red_flag_triggers": ["bleeding gums", "petechiae", "stiff neck", "retro orbital pain"]
            }
        ]
    },

    "cough": {
        "domain": "cough",
        "label": "Cough & Respiratory Tract Evaluation",
        "triggers": [
            r"\bcough\w*", r"\bsputum\b", r"\bphlegm\b", r"\bhemoptysis\b",
            r"खांसी", r"कफ", r"दग्गु", r"இருமல்", r"କାଶ", r"କଫ",
            r"khansi", r"daggu", r"kaas", r"kaasa", r"irumal"
        ],
        "hpi_fields": ["duration", "type", "sputum_color", "blood", "nocturnal"],
        "ros_systems": ["respiratory", "ent", "cardiovascular"],
        "red_flag_terms": ["coughing blood", "pink frothy sputum", "hemoptysis", "choking"],
        "questions": [
            {
                "id": "hpi.cough.duration",
                "priority": PRIORITY_P1,
                "state_key": "duration",
                "section": "Cough Duration",
                "why_asking": "Classifies cough as acute (< 3 weeks), subacute (3-8 weeks), or chronic (> 8 weeks).",
                "text": {
                    "en-IN": "How long have you had this cough, and did it begin with a cold, fever, or allergy?",
                    "hi-IN": "यह खांसी कितने समय से है, और क्या यह सर्दी, बुखार या एलर्जी से शुरू हुई थी?",
                    "te-IN": "ఈ దగ్గు ఎంత కాలంగా ఉంది? జలుబు, జ్వరం లేదా అలెర్జీతో మొదలైందా?",
                    "or-IN": "ଏହି କାଶ କେତେ ଦିନରୁ ହେଉଛି, ଏବଂ ଏହା ଥଣ୍ଡା, ଜ୍ୱର ବା ଆଲର୍ଜିରୁ ଆରମ୍ଭ ହୋଇଥିଲା କି?",
                    "ta-IN": "இந்த இருமல் எவ்வளவு நாட்களாக உள்ளது?"
                },
                "quick_picks": ["Less than 1 week (Acute)", "1 to 3 weeks", "More than 3 weeks (Persistent)", "Chronic cough for several months"]
            },
            {
                "id": "hpi.cough.type_sputum",
                "priority": PRIORITY_P1,
                "state_key": "character",
                "section": "Cough Type & Sputum",
                "why_asking": "Distinguishes dry irritating cough from productive bacterial/viral sputum and checks for hemoptysis.",
                "text": {
                    "en-IN": "Is the cough dry or productive with phlegm/sputum? Have you seen any traces of red blood or rust-colored phlegm?",
                    "hi-IN": "क्या खांसी सूखी है या कफ/बलगम वाली? क्या बलगम में खून या गहरा रंग दिखाई दिया है?",
                    "te-IN": "పొడి దగ్గా లేదా కఫంతో కూడిన దగ్గా? కఫంలో రక్తం పడిందా?",
                    "or-IN": "କାଶ ଶୁଖିଲା ନା କଫ ବାହାରୁଛି? କଫରେ କିଛି ରକ୍ତ ବା ଗାଢ଼ ରଙ୍ଗ ଦେଖାଯାଉଛି କି?",
                    "ta-IN": "வறட்டு இருமலா அல்லது சளி வருகிறதா? ரத்தம் உள்ளதா?"
                },
                "quick_picks": ["Dry continuous irritating cough", "Productive with yellow/green phlegm", "Traces of red blood (Hemoptysis)", "Clear or white thin mucus"],
                "red_flag_triggers": ["blood in sputum", "hemoptysis", "rust colored"]
            },
            {
                "id": "hpi.cough.triggers_nocturnal",
                "priority": PRIORITY_P2,
                "state_key": "triggers",
                "section": "Cough Triggers & Timing",
                "why_asking": "Identifies asthma/bronchospasm triggers (cold air, night, lying down) or GERD-induced cough.",
                "text": {
                    "en-IN": "Is the cough worse at night, when lying flat, in cold air, or accompanied by wheezing or whistling sounds?",
                    "hi-IN": "क्या खांसी रात में, सीधे लेटने पर, या ठंडी हवा में बढ़ती है? क्या सीने से सीटी जैसी आवाज आती है?",
                    "te-IN": "రాత్రిపూట, పడుకున్నప్పుడు లేదా చల్లటి గాలిలో దగ్గు ఎక్కువవుతుందా? ఛాతీలో పిల్లికూతలు వస్తున్నాయా?",
                    "or-IN": "ରାତିରେ, ଶୋଇଲେ ବା ଥଣ୍ଡା ପବନରେ କାଶ ବଢ଼ୁଛି କି? ଛାତିରୁ ଶୁଁ-ଶୁଁ ଶବ୍ଦ ହେଉଛି କି?",
                    "ta-IN": "இரவில் அல்லது படுக்கும்போது இருமல் கூடுகிறதா?"
                },
                "quick_picks": ["Worse at night or when lying flat", "Wheezing / Whistling sounds in chest", "Triggered by dust, pollen, or smoke", "No specific nocturnal worsening"]
            },
            {
                "id": "hpi.cough.associated",
                "priority": PRIORITY_P2,
                "state_key": "associated_symptoms",
                "section": "Associated Respiratory Features",
                "why_asking": "Identifies systemic or upper airway involvement (fever, dyspnea, throat pain).",
                "text": {
                    "en-IN": "Do you also have fever, shortness of breath, sore throat, or chest soreness when coughing?",
                    "hi-IN": "क्या खांसने पर सीने में दर्द, बुखार, सांस फूलना या गले में खराश होती है?",
                    "te-IN": "దగ్గుతో పాటు జ్వరం, ఆయాసం, గొంతు నొప్పి లేదా ఛాతీలో నొప్పి ఉందా?",
                    "or-IN": "କାଶିବା ବେଳେ ଛାତିରେ ଯନ୍ତ୍ରଣା, ଜ୍ୱର, ଶ୍ୱାସ ବା ଗଳା ଖରାପ ହେଉଛି କି?",
                    "ta-IN": "இருமும் போது மார்பு வலி, காய்ச்சல் அல்லது தொண்டை வலி உள்ளதா?"
                },
                "quick_picks": ["Chest soreness only when coughing hard", "Accompanied by high fever", "Noticeable shortness of breath", "Runny nose & sore throat only"]
            }
        ]
    },

    "breathlessness": {
        "domain": "breathlessness",
        "label": "Dyspnea & Cardiopulmonary Distress",
        "triggers": [
            r"\bbreath\w*", r"\bdyspnea\b", r"\bsob\b", r"\bwheez\b", r"\bstridor\b",
            r"सांस फूलना", r"दम घुटना", r"శ్వాస ఆడట్లేదు", r"ఆయాసం", r"மூச்சு திணறல்", r"ଶ୍ୱାସ", r"ଅଣନିଶ୍ୱାସୀ",
            r"saans\s*foolna", r"dam\s*ghutna", r"swasa", r"aayasam"
        ],
        "hpi_fields": ["onset", "orthopnea", "pnd", "exertional_limit", "wheeze"],
        "ros_systems": ["respiratory", "cardiovascular"],
        "red_flag_terms": ["cannot speak in full sentences", "gasping", "cyanosis", "stridor", "blue lips"],
        "questions": [
            {
                "id": "hpi.breath.severity_positional",
                "priority": PRIORITY_P0,
                "state_key": "severity",
                "section": "Dyspnea Severity & Orthopnea",
                "why_asking": "Identifies urgent respiratory distress (orthopnea, resting dyspnea, PND).",
                "text": {
                    "en-IN": "Are you struggling to breathe while resting, unable to lie flat without extra pillows (orthopnea), or waking up gasping at night?",
                    "hi-IN": "क्या बैठे-बैठे भी सांस लेने में कठिनाई हो रही है? क्या सीधे लेटने पर सांस फूलती है या रात में घबराहट से नींद खुलती है?",
                    "te-IN": "విశ్రాంతిలో కూడా శ్వాస తీసుకోవడం కష్టంగా ఉందా? నిద్రలో ఊపిరాడక మెలకువ వస్తుందా?",
                    "or-IN": "ବସିଥିବା ସମୟରେ ମଧ୍ୟ ନିଶ୍ୱାସ ନେବା କଷ୍ଟ ହେଉଛି କି? ଶୋଇଲେ ଶ୍ୱାସ ବଢ଼ୁଛି କି?",
                    "ta-IN": "ஓய்வில் இருக்கும் போதும் மூச்சு திணறல் உள்ளதா?"
                },
                "quick_picks": ["Struggling to breathe at complete rest", "Short of breath on minimal walking", "Cannot lie flat without 2+ pillows", "Wheezing / Whistling sounds in chest"],
                "red_flag_triggers": ["struggling at rest", "gasping", "unable to speak full sentences"]
            },
            {
                "id": "hpi.breath.onset",
                "priority": PRIORITY_P1,
                "state_key": "onset",
                "section": "Dyspnea Onset",
                "why_asking": "Differentiates acute onset (pulmonary embolism, acute asthma, pneumothorax) from subacute/chronic heart failure or COPD.",
                "text": {
                    "en-IN": "Did this breathing difficulty start suddenly within minutes to hours, or has it built up gradually over days or weeks?",
                    "hi-IN": "क्या सांस की तकलीफ मिनटों-घंटों में अचानक शुरू हुई, या दिनों-हफ्तों में धीरे-धीरे बढ़ी?",
                    "te-IN": "ఈ శ్వాస సమస్య కొన్ని నిమిషాలు లేదా గంటల్లో అకస్మాత్తుగా మొదలైందా, లేదా క్రమంగా పెరిగిందా?",
                    "or-IN": "ଏହି ନିଶ୍ୱାସ କଷ୍ଟ କିଛି ମିନିଟ ବା ଘଣ୍ଟା ମଧ୍ୟରେ ହଠାତ୍ ଆସିଲା ନା ଧୀରେ ଧୀରେ ବଢ଼ିଲା?",
                    "ta-IN": "திடீரென ஏற்பட்டதா அல்லது மெதுவாக அதிகரித்ததா?"
                },
                "quick_picks": ["Sudden acute onset (< 2 hours)", "Developed over the past 2-3 days", "Gradually worsening over several weeks", "Long-standing chronic issue"]
            },
            {
                "id": "hpi.breath.cough_wheeze",
                "priority": PRIORITY_P2,
                "state_key": "associated_symptoms",
                "section": "Associated Respiratory Features",
                "why_asking": "Assesses bronchospasm, sputum, or cardiac pulmonary edema.",
                "text": {
                    "en-IN": "Do you have an audible wheeze, cough with colored or frothy phlegm, or swollen ankles/feet?",
                    "hi-IN": "क्या सांस लेते समय सीटी की आवाज, कफ वाली खांसी, या पैरों/टखनों में सूजन है?",
                    "te-IN": "శ్వాసలో పిల్లికూతలు, కఫంతో కూడిన దగ్గు లేదా కాళ్ళ వాపులు ఉన్నాయా?",
                    "or-IN": "ନିଶ୍ୱାସ ନେଲାବେଳେ ଶବ୍ଦ, କଫ କାଶ ବା ଗୋଡ଼ ଫୁଲିବା ଅଛି କି?",
                    "ta-IN": "மூச்சில் விசில் சத்தம், சளி அல்லது கால் வீக்கம் உள்ளதா?"
                },
                "quick_picks": ["Audible wheezing in chest", "Swelling in both feet / ankles (Edema)", "Cough with yellow/green phlegm", "No cough or swelling"]
            }
        ]
    },

    "abdominal_pain": {
        "domain": "abdominal_pain",
        "label": "Abdominal & Acute Abdomen Evaluation",
        "triggers": [
            r"\babdomen\b", r"\babdominal\b", r"\bstomach\b", r"\bbelly\b", r"\bgut\b",
            r"पेट दर्द", r"पेट में दर्द", r"కడుపు నొప్పి", r"വയറുവേദന", r"வயிறு வலி", r"ପେଟ ଯନ୍ତ୍ରଣା", r"ପେଟ ଦରଜ",
            r"pet\s*dard", r"pet\s*me\s*dard", r"pet\s*re\s*kasta", r"kadupu\s*noppi", r"vayaru\s*vali"
        ],
        "hpi_fields": ["location", "quadrant", "radiation", "meals_relationship", "guarding"],
        "ros_systems": ["gastrointestinal", "hepatobiliary", "urinary"],
        "red_flag_terms": ["rigid abdomen", "board-like", "rebound tenderness", "black stool", "hematemesis"],
        "questions": [
            {
                "id": "hpi.abd.location_quadrant",
                "priority": PRIORITY_P1,
                "state_key": "location",
                "section": "Abdominal Location",
                "why_asking": "Pinpoints the abdominal quadrant to isolate organ pathology (gallbladder, appendix, stomach, colon).",
                "text": {
                    "en-IN": "Which part of your abdomen hurts most — upper center, upper right (under ribs), lower right (appendix area), lower center, or all over?",
                    "hi-IN": "पेट के किस हिस्से में सबसे ज्यादा दर्द है — ऊपर बीच में, ऊपर दाईं ओर, नीचे दाईं तरफ (अपेंडिक्स), या पूरे पेट में?",
                    "te-IN": "కడుపులో ఏ భాగంలో ఎక్కువ నొప్పి ఉంది — పై భాగం మధ్యలో, కుడివైపు పక్కటెముకల కింద, కింద కుడివైపు లేదా పొట్టంతా?",
                    "or-IN": "ପେଟର କେଉଁ ଅଂଶରେ ସବୁଠାରୁ ଅଧିକ ଯନ୍ତ୍ରଣା — ଉପର ମଝିରେ, ଡାହାଣ କଡ଼ରେ, ତଳ ଡାହାଣ ପାଖରେ ନା ସମଗ୍ର ପେଟରେ?",
                    "ta-IN": "வயிற்றில் எந்த பகுதியில் வலி அதிகமாக உள்ளது — மேல் நடுவிலா, வலது பக்கமா அல்லது கீழ் பகுதியிலா?"
                },
                "quick_picks": ["Upper center (Burning / Acidity / Gastric)", "Right upper under ribs (Gallbladder/Liver)", "Right lower abdomen (Appendix concern)", "Lower central pelvic area", "All over / Diffuse cramping"],
                "red_flag_triggers": ["right lower quadrant acute", "board-like rigidity"]
            },
            {
                "id": "hpi.abd.character",
                "priority": PRIORITY_P1,
                "state_key": "character",
                "section": "Pain Character",
                "why_asking": "Differentiates burning peptic acidity from colicky spasm (stones/obstruction) or sharp localized peritonitis.",
                "text": {
                    "en-IN": "What does the abdominal pain feel like — burning sensation, sharp cramping spasms that come in waves, or a constant dull ache?",
                    "hi-IN": "पेट का दर्द कैसा महसूस होता है — एसिडिटी जैसी जलन, रुक-रुक कर मरोड़ उठना, या लगातार हल्का मीठा दर्द?",
                    "te-IN": "కడుపు నొప్పి ఎలా అనిపిస్తుంది — మంటగా, విడతల వారీగా వచ్చే తీవ్రమైన మెలిపెట్టే నొప్పా, లేదా నిరంతర మొద్దు నొప్పా?",
                    "or-IN": "ପେଟ ଯନ୍ତ୍ରଣା କିପରି ଲାଗୁଛି — ପୋଡ଼ାଜଳା, ମୋଡ଼ି ହୋଇ ଆସୁଥିବା କଷ୍ଟ, ନା ଲାଗିରହୁଥିବା ମାନ୍ଦା ଦରଜ?",
                    "ta-IN": "வலி எரிகிறதா, அலை அலையாக வருகிறதா அல்லது தொடர்ந்து வலிக்கிறதா?"
                },
                "quick_picks": ["Burning acidity sensation", "Cramping spasms in waves (Colicky)", "Sharp continuous localized pain", "Dull bloated ache"]
            },
            {
                "id": "hpi.abd.relation_food",
                "priority": PRIORITY_P1,
                "state_key": "triggers",
                "section": "Relation to Food",
                "why_asking": "Assesses relationship to meals: postprandial gallbladder/pancreatic pain vs empty-stomach peptic ulcer relief.",
                "text": {
                    "en-IN": "Is the stomach pain related to food — does it get worse immediately after meals, after oily/spicy food, or on an empty stomach?",
                    "hi-IN": "क्या पेट दर्द का खाने से संबंध है — क्या खाना खाने के तुरंत बाद, तैलीय/मसालेदार खाने से, या खाली पेट दर्द बढ़ता है?",
                    "te-IN": "కడుపు నొప్పికి ఆహారంతో సంబంధం ఉందా — భోజనం చేసిన వెంటనే, నూనె/మసాలా ఆహారాల వల్ల లేదా ఖాళీ కడుపుతో ఉన్నప్పుడు పెరుగుతుందా?",
                    "or-IN": "ଖାଇବା ସହିତ ଏହାର ସମ୍ପର୍କ ଅଛି କି — ଖାଇବା ପରେ ପରେ, ତେଲିଆ/ମସଲା ଖାଦ୍ୟ ଖାଇଲେ ବା ଖାଲି ପେଟରେ ଯନ୍ତ୍ରଣା ବଢୁଛି କି?",
                    "ta-IN": "சாப்பிட்ட பிறகு, காரமான உணவால் அல்லது வெறும் வயிற்றில் வலி கூடுகிறதா?"
                },
                "quick_picks": ["Worse immediately after eating", "Worse after fatty, greasy, or spicy food", "Relieved after eating / Worse on empty stomach", "Unrelated to food"]
            },
            {
                "id": "hpi.abd.associated",
                "priority": PRIORITY_P1,
                "state_key": "associated_symptoms",
                "section": "Associated GI Symptoms",
                "why_asking": "Screens for bowel obstruction, gastroenteritis, hepatitis, or acute pancreatitis.",
                "text": {
                    "en-IN": "Are you experiencing vomiting, loose watery motions (diarrhea), severe constipation/inability to pass gas, or fever?",
                    "hi-IN": "क्या आपको उल्टी, दस्त (लूज मोशन), पेट साफ न होना/गैस पास न होना, या बुखार है?",
                    "te-IN": "వాంతులు, విరేచనాలు (డయేరియా), తీవ్రమైన మలబద్ధకం లేదా జ్వరం వంటివి ఏవైనా ఉన్నాయా?",
                    "or-IN": "ବାନ୍ତି, ଝାଡ଼ା, ପେଟ ସଫା ନହେବା ବା ଜ୍ୱର ହେଉଛି କି?",
                    "ta-IN": "வாந்தி, வயிற்றுப்போக்கு, மலச்சிக்கல் அல்லது காய்ச்சல் உள்ளதா?"
                },
                "quick_picks": ["Nausea & vomiting", "Watery loose stools / diarrhea", "Inability to pass stools or gas (Obstruction concern)", "High fever with chills", "No vomiting or bowel changes"]
            },
            {
                "id": "hpi.abd.severity",
                "priority": PRIORITY_P2,
                "state_key": "severity",
                "section": "Pain Severity & Guarding",
                "why_asking": "Evaluates acute abdomen severity and peritoneal signs.",
                "text": {
                    "en-IN": "On a scale from 1 to 10, how severe is the abdominal pain, and does touching or pressing on the stomach make it unbearable?",
                    "hi-IN": "1 से 10 के पैमाने पर दर्द कितना तेज है? क्या पेट को छूने या दबाने से दर्द बहुत ज्यादा बढ़ जाता है?",
                    "te-IN": "1 నుండి 10 స్కేల్‌లో నొప్పి ఎంత తీవ్రంగా ఉంది? పొట్టపై నొక్కితే తట్టుకోలేనంతగా పెరుగుతుందా?",
                    "or-IN": "୧ ରୁ ୧୦ ମଧ୍ୟରେ ଯନ୍ତ୍ରଣା କେତେ ତୀବ୍ର? ପେଟ ଉପରେ ହାତ ଲଗାଇଲେ ବା ଦବାଇଲେ ଅସହ୍ୟ ହେଉଛି କି?",
                    "ta-IN": "1 முதல் 10 வரை வலி எவ்வளவு? வயிற்றைத் தொட்டால் வலிக்கிறதா?"
                },
                "quick_picks": ["1-3 (Mild manageable)", "4-6 (Moderate cramping)", "7-8 (Severe pain)", "9-10 (Unbearable / Board-like rigidity)"]
            }
        ]
    },

    "headache": {
        "domain": "headache",
        "label": "Headache & Neurological Evaluation",
        "triggers": [
            r"\bheadache\w*", r"\bhead ache\b", r"\bmigraine\b", r"\bcephalalgia\b",
            r"सिरदर्द", r"सिर दर्द", r"తలనొప్పి", r"தலைவலி", r"ମୁଣ୍ଡବିନ୍ଧା",
            r"sar\s*dard", r"matha\s*darda", r"munda\s*bindha", r"talanappi", r"thalai\s*vali"
        ],
        "hpi_fields": ["onset", "location", "character", "aura", "neck_stiffness", "neuro_deficits"],
        "ros_systems": ["neurological", "ophthalmic", "ent"],
        "red_flag_terms": ["thunderclap", "worst headache of life", "slurred speech", "facial droop", "arm weakness"],
        "questions": [
            {
                "id": "hpi.headache.onset_severity",
                "priority": PRIORITY_P0,
                "state_key": "onset",
                "section": "Onset & Thunderclap Rule-out",
                "why_asking": "Rules out subarachnoid hemorrhage (thunderclap headache hitting peak within seconds).",
                "text": {
                    "en-IN": "Did this headache hit instantly like a thunderclap reaching maximum severity in seconds? Is this the worst headache of your life?",
                    "hi-IN": "क्या यह सिरदर्द बिजली के झटके की तरह अचानक सेकंडों में सबसे तेज हो गया? क्या यह आपकी जिंदगी का सबसे भयानक सिरदर्द है?",
                    "te-IN": "ఈ తలనొప్పి పిడుగు పడినట్లు కొన్ని సెకన్లలోనే అత్యంత తీవ్రంగా మారిందా? ఇది మీ జీవితంలోనే అత్యంత భయంకరమైన తలనొప్పా?",
                    "or-IN": "ଏହି ମୁଣ୍ଡବିନ୍ଧା ହଠାତ୍ ବିଜୁଳି ପରି ସେକେଣ୍ଡ ମଧ୍ୟରେ ଅସହ୍ୟ ହୋଇଗଲା କି? ଏହା ଆପଣଙ୍କ ଜୀବନର ସବୁଠୁ ଭୟଙ୍କର ମୁଣ୍ଡବିନ୍ଧା କି?",
                    "ta-IN": "இந்த தலைவலி திடீரென இடி போல் தாக்கியதா? உங்கள் வாழ்க்கையிலேயே மிகக் கடுமையான தலைவலியா?"
                },
                "quick_picks": ["Sudden explosive thunderclap (< 1 minute)", "Gradual throbbing onset over hours", "Dull constant pressure band across head", "Chronic recurring episodes"],
                "red_flag_triggers": ["thunderclap", "worst headache of life", "sudden explosive"]
            },
            {
                "id": "hpi.headache.location",
                "priority": PRIORITY_P1,
                "state_key": "location",
                "section": "Headache Location",
                "why_asking": "Differentiates unilateral migraine/cluster headache from frontal sinus or tension band distribution.",
                "text": {
                    "en-IN": "Where exactly is the headache located — one side of the head, across your forehead, at the back of your head/neck, or all over?",
                    "hi-IN": "सिरदर्द ठीक कहाँ है — सिर के एक तरफ (आधे सिर में), माथे के सामने, सिर के पिछले हिस्से/गर्दन में, या पूरे सिर में?",
                    "te-IN": "తలనొప్పి సరిగ్గా ఎక్కడ ఉంది — ఒక వైపు మాత్రమేనా, నుదురు భాగాన, తల వెనుక మెడ భాగంలోనా, లేదా తలంతా?",
                    "or-IN": "ମୁଣ୍ଡବିନ୍ଧା ଠିକ୍ କେଉଁଠି ହେଉଛି — ଗୋଟିଏ ପାଖରେ (ଅଧକପାଳୀ), କପାଳରେ, ପଛପାଖ ବେକରେ ନା ସମଗ୍ର ମୁଣ୍ଡରେ?",
                    "ta-IN": "தலைவலி எங்கு உள்ளது — ஒரு பக்கமா, நெற்றியிலா அல்லது பின் தலையிலா?"
                },
                "quick_picks": ["One side of head (Unilateral / Temple)", "Across forehead / Behind eyes", "Back of head & neck (Occipital)", "Tight band around entire head"]
            },
            {
                "id": "hpi.headache.character",
                "priority": PRIORITY_P1,
                "state_key": "character",
                "section": "Headache Sensation",
                "why_asking": "Identifies pulsating vascular migraine vs dull tension band vs stabbing neuralgia.",
                "text": {
                    "en-IN": "What does the headache feel like — throbbing and pulsating like a heartbeat, tight band squeezing the head, or sharp stabbing?",
                    "hi-IN": "सिरदर्द का अहसास कैसा है — धड़कन जैसा धप-धप करने वाला, सिर को कसकर बांधने जैसा, या तेज चुभन?",
                    "te-IN": "తలనొప్పి ఎలా అనిపిస్తుంది — దబదబ కొట్టుకున్నట్లు (థ్రాబింగ్), తలను బిగించి కట్టినట్లు, లేదా సూదులతో గుచ్చినట్లు?",
                    "or-IN": "ମୁଣ୍ଡବିନ୍ଧା କିପରି ଲାଗୁଛି — ଧପ୍-ଧପ୍ ସ୍ପନ୍ଦନ ପରି, ମୁଣ୍ଡକୁ କଷି ବାନ୍ଧିବା ପରି, ନା ତୀକ୍ଷ୍ଣ ଛୁଞ୍ଚି ଫୋଡ଼ିବା ପରି?",
                    "ta-IN": "தலைவலி துடிப்பது போல் உள்ளதா, இறுக்குவது போல் உள்ளதா அல்லது குத்துவது போல் உள்ளதா?"
                },
                "quick_picks": ["Pulsating / Throbbing with heartbeat", "Dull tight squeezing band", "Sharp stabbing / electric shock sensation", "Heavy dull ache"]
            },
            {
                "id": "hpi.headache.associated",
                "priority": PRIORITY_P1,
                "state_key": "associated_symptoms",
                "section": "Associated Sensory & Autonomic Symptoms",
                "why_asking": "Screens for migraine criteria (photophobia, phonophobia, nausea, visual aura) and meningism.",
                "text": {
                    "en-IN": "Do you experience nausea, vomiting, sensitivity to bright light or loud sounds, or seeing flashing zigzag lights (aura)?",
                    "hi-IN": "क्या सिरदर्द के साथ जी मिचलाना, उल्टी, तेज रोशनी या आवाज से परेशानी, या आंखों के सामने चमकती रोशनी दिखती है?",
                    "te-IN": "తలనొప్పితో పాటు వికారం, వాంతులు, వెలుతురు లేదా శబ్దాలు చూడలేకపోవడం, లేదా కళ్ల ముందు మెరుపులు కనిపిస్తున్నాయా?",
                    "or-IN": "ମୁଣ୍ଡବିନ୍ଧା ସହିତ ବାନ୍ତି ଭାବ, ଆଲୋକ ବା ଶବ୍ଦ ଅସହ୍ୟ ହେବା, କିମ୍ବା ଆଖି ଆଗରେ ବିଜୁଳି ଚମକିବା ଭଳି ଦେଖାଯାଉଛି କି?",
                    "ta-IN": "குமட்டல், வாந்தி, வெளிச்சம் அல்லது சத்தம் பார்த்தால் தலைவலி கூடுகிறதா?"
                },
                "quick_picks": ["Sensitivity to bright light & loud sound", "Nausea or vomiting", "Visual zigzag lines / flashing aura", "Stiff neck / Pain when bending neck", "No associated symptoms"],
                "red_flag_triggers": ["stiff neck", "fever with headache", "diplopia"]
            },
            {
                "id": "hpi.headache.triggers",
                "priority": PRIORITY_P2,
                "state_key": "triggers",
                "section": "Triggers & Aggravators",
                "why_asking": "Identifies lifestyle and environmental triggers (lack of sleep, stress, screen time, skipped meals).",
                "text": {
                    "en-IN": "Does anything trigger or worsen the headache — such as lack of sleep, stress, long screen time, coughing, or bending forward?",
                    "hi-IN": "क्या किसी चीज से सिरदर्द बढ़ता है — जैसे नींद की कमी, तनाव, स्क्रीन पर ज्यादा समय, खांसने या आगे झुकने से?",
                    "te-IN": "నిద్రలేమి, ఒత్తిడి, ఎక్కువ స్క్రీన్ చూడటం, దగ్గడం లేదా ముందుకు వంగడం వల్ల తలనొప్పి పెరుగుతుందా?",
                    "or-IN": "ନିଦ୍ରାହୀନତା, ମାନସିକ ଚାପ, ମୋବାଇଲ/ସ୍କ୍ରିନ ଦେଖିବା, କାଶିବା ବା ଆଗକୁ ନଇଁବା ଦ୍ୱାରା ଏହା ବଢ଼ୁଛି କି?",
                    "ta-IN": "தூக்கமின்மை, மன அழுத்தம் அல்லது திரையைப் பார்ப்பதால் தலைவலி கூடுகிறதா?"
                },
                "quick_picks": ["Worse with stress / lack of sleep", "Worse with long screen use / reading", "Worse when coughing, straining, or bending forward", "Relieved in a quiet dark room"]
            }
        ]
    },

    "joint_pain": {
        "domain": "joint_pain",
        "label": "Joint & Musculoskeletal Evaluation",
        "triggers": [
            r"\bjoint\w*", r"\bknee\w*", r"\barthritis\b", r"\bgout\b", r"\bswollen\s*joint\b",
            r"जोड़ों में दर्द", r"घुटने में दर्द", r"కీళ్ల నొప్పి", r"కీళ్లు", r"மூட்டு வலி", r"ଗଣ୍ଠି ଯନ୍ତ୍ରଣା", r"ଆଣ୍ଠୁ ଗଣ୍ଠି",
            r"jodon\s*me\s*dard", r"ghutne\s*me\s*dard", r"godige\s*bindha", r"mokaali\s*noppi", r"mootu\s*vali"
        ],
        "hpi_fields": ["joints_involved", "symmetry", "swelling", "morning_stiffness", "mobility"],
        "ros_systems": ["musculoskeletal", "rheumatological"],
        "red_flag_terms": ["hot red swollen joint", "inability to bear any weight", "septic arthritis"],
        "questions": [
            {
                "id": "hpi.joint.location",
                "priority": PRIORITY_P1,
                "state_key": "location",
                "section": "Joint Location & Symmetry",
                "why_asking": "Identifies specific joints (knee, hip, ankle, small hand joints) and symmetric vs asymmetric involvement.",
                "text": {
                    "en-IN": "Which specific joints are hurting (e.g., one knee, both knees, hips, fingers, wrists, or ankles)?",
                    "hi-IN": "किन जोड़ों में दर्द है — एक घुटने में, दोनों घुटनों में, कूल्हे, उंगलियों, कलाई या टखनों में?",
                    "te-IN": "ఏ కీళ్లలో నొప్పి ఉంది — ఒక మోకాలా, రెండు మోకాళ్ళా, తుంటి, చేతి వేళ్ళు లేదా మడమలా?",
                    "or-IN": "କେଉଁ ନିର୍ଦ୍ଦିଷ୍ଟ ଗଣ୍ଠିରେ ଯନ୍ତ୍ରଣା ହେଉଛି — ଗୋଟିଏ ଆଣ୍ଠୁ, ଉଭୟ ଆଣ୍ଠୁ, ଅଣ୍ଟା, ଆଙ୍ଗୁଠି ବା ଗୋଇଠି?",
                    "ta-IN": "எந்த மூட்டுகளில் வலி உள்ளது — ஒரு முழங்கால், இரண்டு முழங்கால்கள், இடுப்பு அல்லது விரல்களிலா?"
                },
                "quick_picks": ["One knee only (Right / Left)", "Both knees symmetrically", "Small joints of fingers & wrists", "Ankles or feet", "Multiple joints all over body"]
            },
            {
                "id": "hpi.joint.swelling_stiffness",
                "priority": PRIORITY_P1,
                "state_key": "character",
                "section": "Swelling & Morning Stiffness",
                "why_asking": "Differentiates inflammatory arthritis (morning stiffness > 30 mins) from degenerative osteoarthritis.",
                "text": {
                    "en-IN": "Is there visible swelling, warmth, or morning stiffness in the joints that takes more than 30 minutes to loosen up?",
                    "hi-IN": "क्या जोड़ों में सूजन, गर्माहट, या सुबह उठने पर 30 मिनट से अधिक जकड़न (अकड़न) रहती है?",
                    "te-IN": "కీళ్లలో వాపు, వేడి లేదా ఉదయం లేవగానే 30 నిమిషాలకు పైగా కీళ్లు బిగుసుకుపోయినట్లు ఉంటుందా?",
                    "or-IN": "ଗଣ୍ଠିରେ ଫୁଲା, ଗରମ ଅନୁଭବ, କିମ୍ବା ସକାଳେ ଉଠିଲେ ଅଧଘଣ୍ଟାରୁ ଅଧିକ ସମୟ ଜଡ଼ତା ବା ଟାଣ ଲାଗି ରହୁଛି କି?",
                    "ta-IN": "மூட்டுகளில் வீக்கம் அல்லது காலையில் எழுந்ததும் 30 நிமிடங்களுக்கு மேல் விறைப்பு உள்ளதா?"
                },
                "quick_picks": ["Morning stiffness lasting > 30 minutes (Inflammatory)", "Stiff for 5-10 minutes on waking, worse with walking (Osteoarthritis)", "Visible swelling, redness & warmth", "No swelling or significant stiffness"],
                "red_flag_triggers": ["hot red swollen joint", "fever with joint swelling"]
            },
            {
                "id": "hpi.joint.mobility_triggers",
                "priority": PRIORITY_P1,
                "state_key": "triggers",
                "section": "Weight-Bearing & Mobility",
                "why_asking": "Assesses functional mechanical limitation and weight-bearing tolerance.",
                "text": {
                    "en-IN": "Does walking, climbing stairs, or bearing weight worsen the pain? Can you walk independently?",
                    "hi-IN": "क्या चलने, सीढ़ियां चढ़ने या वजन डालने पर दर्द बढ़ता है? क्या आप बिना सहारे चल पा रहे हैं?",
                    "te-IN": "నడవడం, మెట్లు ఎక్కడం వల్ల నొప్పి ఎక్కువవుతుందా? ఎవరి సాయం లేకుండా నడవగలరా?",
                    "or-IN": "ଚାଲିବା, ସିଡ଼ି ଚଢ଼ିବା ଦ୍ୱାରା ଯନ୍ତ୍ରଣା ବଢୁଛି କି? ବିନା ସାହାଯ୍ୟରେ ଚାଲିପାରୁଛନ୍ତି କି?",
                    "ta-IN": "நடக்கும்போது அல்லது படிக்கட்டுகளில் ஏறும்போது வலி கூடுகிறதா?"
                },
                "quick_picks": ["Worse when climbing stairs or walking long distances", "Unable to bear weight on the joint", "Pain even while resting in bed", "Creaking / Clicking sounds in joint on movement"]
            },
            {
                "id": "hpi.joint.onset_trauma",
                "priority": PRIORITY_P2,
                "state_key": "onset",
                "section": "Onset & Injury History",
                "why_asking": "Rules out acute ligamentous/meniscal injury or crystal gout attack.",
                "text": {
                    "en-IN": "Did the joint pain begin suddenly after a fall, twist, or sports injury, or has it developed gradually over months?",
                    "hi-IN": "क्या दर्द किसी चोट, गिरने या मुड़ने के बाद अचानक शुरू हुआ, या महीनों में धीरे-धीरे बढ़ा?",
                    "te-IN": "కింద పడటం, బెణకడం వల్ల అకస్మాత్తుగా వచ్చిందా, లేదా నెలల తరబడి క్రమంగా పెరిగిందా?",
                    "or-IN": "ପଡ଼ିଯିବା, ମୋଡ଼ି ହେବା ବା ଆଘାତ ପରେ ହଠାତ୍ ଆସିଲା ନା ମାସ ମାସ ଧରି ବଢ଼ିଲା?",
                    "ta-IN": "விழுந்ததால் அல்லது காயம் ஏற்பட்டதால் திடீரென வந்ததா?"
                },
                "quick_picks": ["Started gradually over months / years (Wear & Tear)", "Sudden pain after fall / twisting injury", "Sudden overnight severe big toe pain (Gout concern)", "Started after a viral infection"]
            }
        ]
    },

    "back_pain": {
        "domain": "back_pain",
        "label": "Spine & Lumbosacral Evaluation",
        "triggers": [
            r"\bback\b", r"\bspine\b", r"\blumbago\b", r"\bsciatica\b", r"\bdisc\b",
            r"कमर दर्द", r"पीठ दर्द", r"నడుము నొప్పి", r"వీపు నొప్పి", r"முதுகு வலி", r"ଅଣ୍ଟା ଯନ୍ତ୍ରଣା", r"ପିଠି ଦରଜ",
            r"kamar\s*dard", r"peeth\s*dard", r"nadumu\s*noppi", r"anta\s*bindha"
        ],
        "hpi_fields": ["location", "radiation", "sciatica", "cauda_equina_flags", "posture"],
        "ros_systems": ["musculoskeletal", "neurological"],
        "red_flag_terms": ["bowel incontinence", "bladder incontinence", "saddle anesthesia", "leg weakness"],
        "questions": [
            {
                "id": "hpi.back.location_radiation",
                "priority": PRIORITY_P1,
                "state_key": "location_and_radiation",
                "section": "Spine Location & Sciatica Radiation",
                "why_asking": "Assesses lumbosacral disc herniation radiating along sciatic nerve distribution.",
                "text": {
                    "en-IN": "Where is the back pain located, and does it shoot down your buttocks, thigh, leg, or foot (sciatica)?",
                    "hi-IN": "कमर का दर्द ठीक कहाँ है, और क्या यह कूल्हे, जांघ, या पैर के नीचे तक जाता है (सायटिका)?",
                    "te-IN": "నడుము నొప్పి ఎక్కడ ఉంది? ఇది తొడ, పిక్క లేదా పాదం వరకు పాకుతుందా (సయాటికా)?",
                    "or-IN": "ଅଣ୍ଟା ଯନ୍ତ୍ରଣା କେଉଁଠି ହେଉଛି, ଏବଂ ଏହା ନିତମ୍ବ ବା ଗୋଡ଼ ତଳକୁ ଯାଉଛି କି (ସାୟାଟିକା)?",
                    "ta-IN": "முதுகு வலி எங்கு உள்ளது? பிட்டம், தொடை அல்லது கால் வரை பரவுகிறதா?"
                },
                "quick_picks": ["Lower back localized only (No radiation)", "Shoots down one leg to calf / foot (Sciatica)", "Shoots down both legs", "Upper / Mid back between shoulder blades"]
            },
            {
                "id": "hpi.back.red_flags_cauda",
                "priority": PRIORITY_P0,
                "state_key": "safety_check",
                "section": "Cauda Equina Red Flags",
                "why_asking": "Rules out surgical cauda equina syndrome (loss of bowel/bladder control, saddle numbness).",
                "text": {
                    "en-IN": "Have you experienced any loss of bowel or bladder control, difficulty passing urine, or numbness between your legs (groin/saddle area)?",
                    "hi-IN": "क्या पेशाब या शौच पर नियंत्रण में कोई कठिनाई, पेशाब रुकना, या दोनों पैरों के बीच सुन्नपन महसूस हुआ है?",
                    "te-IN": "మూత్రం లేదా మల విసర్జనపై నియంత్రణ కోల్పోవడం, లేదా కాళ్ల మధ్య మొద్దుబారడం వంటివి ఉన్నాయా?",
                    "or-IN": "ପରିସ୍ରା ବା ଝାଡ଼ା ଉପରେ ନିୟନ୍ତ୍ରଣ ହରାଇବା, କିମ୍ବା ଜଙ୍ଘ ମଧ୍ୟଭାଗରେ କାଲୁଆ ଲାଗିବା ଅଛି କି?",
                    "ta-IN": "சிறுநீர் அல்லது மலம் கட்டுப்பாடு இழப்பது போல் உள்ளதா?"
                },
                "quick_picks": ["No numbness or urinary / bowel problems", "Numbness / Tingling in feet or toes", "Difficulty passing urine / Retention", "Weakness in foot (Foot drop)"],
                "red_flag_triggers": ["loss of bladder control", "bowel incontinence", "saddle numbness", "foot drop"]
            },
            {
                "id": "hpi.back.character_triggers",
                "priority": PRIORITY_P1,
                "state_key": "triggers",
                "section": "Postural Triggers & Lifting",
                "why_asking": "Identifies mechanical strain vs disc herniation aggravated by flexion.",
                "text": {
                    "en-IN": "Did the pain start after lifting something heavy or bending, and is it worse with sitting, standing, or walking?",
                    "hi-IN": "क्या दर्द भारी वजन उठाने या झुकने के बाद शुरू हुआ? क्या बैठने, खड़े होने या चलने से बढ़ता है?",
                    "te-IN": "బరువులు ఎత్తడం లేదా వంగడం వల్ల నొప్పి మొదలైందా? కూర్చున్నప్పుడు లేదా నడిచినప్పుడు ఎక్కువవుతుందా?",
                    "or-IN": "ଭାରୀ ଜିନିଷ ଉଠାଇବା ପରେ ଏହା ଆରମ୍ଭ ହୋଇଥିଲା କି? ବସିଲେ ବା ଚାଲିଲେ ବଢ଼ୁଛି କି?",
                    "ta-IN": "பளு தூக்கியதால் வந்ததா? உட்கார்ந்தால் கூடுகிறதா?"
                },
                "quick_picks": ["Started immediately after lifting heavy weight", "Worse when sitting or bending forward (Disc pattern)", "Worse when walking or standing straight (Spinal stenosis)", "Relieved when lying flat with knees bent"]
            }
        ]
    },

    "vomiting": {
        "domain": "vomiting",
        "label": "Nausea & Acute Emesis",
        "triggers": [
            r"\bvomit\w*", r"\bnausea\b", r"\bemesis\b", r"\bpuke\b",
            r"उल्टी", r"मतली", r"వాంతి", r"వాంతులు", r"வாந்தி", r"ବାନ୍ତି",
            r"ulti", r"vaanti", r"baanti", r"matli"
        ],
        "hpi_fields": ["frequency", "contents", "blood", "hydration", "food_intake"],
        "ros_systems": ["gastrointestinal", "metabolic"],
        "red_flag_terms": ["blood in vomit", "coffee ground", "dehydration", "no urine"],
        "questions": [
            {
                "id": "hpi.vomit.frequency_hydration",
                "priority": PRIORITY_P1,
                "state_key": "frequency",
                "section": "Frequency & Fluid Tolerance",
                "why_asking": "Assesses dehydration risk and fluid retention ability.",
                "text": {
                    "en-IN": "How many times have you vomited in the past 24 hours, and are you able to keep sips of water down?",
                    "hi-IN": "पिछले 24 घंटों में कितनी बार उल्टी हुई है, और क्या आप पानी भी पचा पा रहे हैं या वह भी निकल जाता है?",
                    "te-IN": "గత 24 గంటల్లో ఎన్నిసార్లు వాంతులు అయ్యాయి? కనీసం నీళ్లు తాగినా వాంతి కాకుండా ఉంటున్నాయా?",
                    "or-IN": "ଗତ ୨୪ ଘଣ୍ଟା ମଧ୍ୟରେ କେତେ ଥର ବାନ୍ତି ହୋଇଛି, ଏବଂ ପାଣି ଟିକେ ପିଇଲେ ପେଟରେ ରହୁଛି କି?",
                    "ta-IN": "கடந்த 24 மணி நேரத்தில் எத்தனை முறை வாந்தி எடுத்தீர்கள்? தண்ணீர் குடித்தால் தங்குகிறதா?"
                },
                "quick_picks": ["1-2 times (Mild)", "3-5 times today", "Persistent (> 6 times) / Cannot keep water down", "Nausea only (No actual vomiting)"]
            },
            {
                "id": "hpi.vomit.color_blood",
                "priority": PRIORITY_P0,
                "state_key": "safety_check",
                "section": "Vomitus Appearance & Bleeding",
                "why_asking": "Rules out upper gastrointestinal hemorrhage (hematemesis) or bowel obstruction (feculent/bilious).",
                "text": {
                    "en-IN": "What does the vomit look like — clear fluid, food particles, greenish-yellow bile, or have you seen red blood or dark coffee-ground material?",
                    "hi-IN": "उल्टी में क्या निकला है — केवल पानी, खाना, पीला-हरा पित्त, या खून या काले दाने जैसी उल्टी हुई है?",
                    "te-IN": "వాంతిలో ఏముంది — ఆహారమా, ఆకుపచ్చ/పసుపు రంగు పిత్తమా, లేదా రక్తం పడిందా?",
                    "or-IN": "ବାନ୍ତିରେ କ'ଣ ବାହାରୁଛି — ଖାଦ୍ୟ, ହଳଦିଆ/ସବୁଜ ପିତ୍ତ, ନା ରକ୍ତ କିଛି ପଡୁଛି?",
                    "ta-IN": "வாந்தியில் ரத்தம் அல்லது பித்தம் உள்ளதா?"
                },
                "quick_picks": ["Undigested food & clear fluid", "Greenish-yellow bitter bile", "Traces of red blood or coffee-ground color", "No blood seen"],
                "red_flag_triggers": ["blood in vomit", "hematemesis", "coffee ground emesis"]
            },
            {
                "id": "hpi.vomit.associated",
                "priority": PRIORITY_P1,
                "state_key": "associated_symptoms",
                "section": "Associated GI & Systemic Symptoms",
                "why_asking": "Determines gastroenteritis vs acute abdomen vs central neurological cause.",
                "text": {
                    "en-IN": "Do you also have severe stomach pain, loose watery motions, high fever, or severe headache with vomiting?",
                    "hi-IN": "क्या उल्टी के साथ पेट में तेज दर्द, दस्त, तेज बुखार, या बहुत तेज सिरदर्द भी है?",
                    "te-IN": "వాంతులతో పాటు కడుపు నొప్పి, విరేచనాలు, జ్వరం లేదా తీవ్రమైన తలనొప్పి ఉందా?",
                    "or-IN": "ବାନ୍ତି ସହିତ ପେଟ ଯନ୍ତ୍ରଣା, ଝାଡ଼ା, ଜ୍ୱର ବା ତୀବ୍ର ମୁଣ୍ଡବିନ୍ଧା ଅଛି କି?",
                    "ta-IN": "வயிற்று வலி, பேதி அல்லது காய்ச்சல் உள்ளதா?"
                },
                "quick_picks": ["Severe abdominal pain & cramps", "Accompanied by loose watery stools", "High fever with chills", "Severe headache & dizziness"]
            }
        ]
    },

    "diarrhea": {
        "domain": "diarrhea",
        "label": "Acute Gastroenteritis & Diarrheal Illness",
        "triggers": [
            r"\bdiarrhea\b", r"\bloose\s*motions?\b", r"\bloose\s*stools?\b", r"\bdysentery\b",
            r"दस्त", r"पेचिश", r"విరేచనాలు", r"డయేరియా", r"வயிற்றுப்போக்கு", r"ଝାଡ଼ା", r"ପେଟ ଖରାପ",
            r"dast", r"jhada", r"virechanalu", r"vayittrupokku"
        ],
        "hpi_fields": ["frequency", "consistency", "blood", "mucus", "hydration"],
        "ros_systems": ["gastrointestinal", "renal"],
        "red_flag_terms": ["blood in stool", "rice water stool", "anuria", "sunken eyes"],
        "questions": [
            {
                "id": "hpi.diarrhea.frequency_consistency",
                "priority": PRIORITY_P1,
                "state_key": "character",
                "section": "Diarrhea Frequency & Consistency",
                "why_asking": "Quantifies severity of fluid loss and hydration status.",
                "text": {
                    "en-IN": "How many loose or watery motions have you had in the last 24 hours, and are they completely watery like rice-water?",
                    "hi-IN": "पिछले 24 घंटों में कितनी बार पतले दस्त हुए हैं? क्या वे पूरी तरह पानी की तरह हैं?",
                    "te-IN": "గత 24 గంటల్లో ఎన్నిసార్లు విరేచనాలు అయ్యాయి? పూర్తిగా నీళ్లలా అవుతున్నాయా?",
                    "or-IN": "ଗତ ୨୪ ଘଣ୍ଟା ମଧ୍ୟରେ କେତେ ଥର ପାଣି ପରି ଝାଡ଼ା ହୋଇଛି?",
                    "ta-IN": "எத்தனை முறை வயிற்றுப்போக்கு ஏற்பட்டது? முற்றிலும் நீராக உள்ளதா?"
                },
                "quick_picks": ["2 to 4 loose motions (Mild)", "5 to 8 watery stools today (Moderate)", "> 8 watery motions / continuous (Severe fluid loss)", "Semi-formed soft stools"]
            },
            {
                "id": "hpi.diarrhea.blood_mucus",
                "priority": PRIORITY_P0,
                "state_key": "safety_check",
                "section": "Dysentery & Blood in Stool",
                "why_asking": "Differentiates invasive bacterial dysentery/IBD from secretory viral diarrhea.",
                "text": {
                    "en-IN": "Have you seen any red blood, black tarry color, or sticky mucus in the stools?",
                    "hi-IN": "क्या मल में खून, काला रंग, या चिपचिपा आंव/म्यूकस दिखाई दिया है?",
                    "te-IN": "మలంలో రక్తం, నల్లటి రంగు లేదా జిగట పదార్థం పడిందా?",
                    "or-IN": "ଝାଡ଼ାରେ ରକ୍ତ, କଳା ରଙ୍ଗ ବା ଆମ୍ବ (Mucus) ପଡୁଛି କି?",
                    "ta-IN": "மலத்தில் ரத்தம் அல்லது சீழ் உள்ளதா?"
                },
                "quick_picks": ["Traces of red blood with mucus (Dysentery concern)", "Black tarry stools (Melena concern)", "Watery without any blood or mucus", "Sticky mucus only"],
                "red_flag_triggers": ["blood in stool", "melena", "dysentery"]
            },
            {
                "id": "hpi.diarrhea.hydration_status",
                "priority": PRIORITY_P1,
                "state_key": "severity",
                "section": "Dehydration Symptoms",
                "why_asking": "Screens for clinical dehydration requiring urgent ORS or IV rehydration.",
                "text": {
                    "en-IN": "Are you feeling extreme thirst, dry tongue, dizziness upon standing, or reduced urine passing?",
                    "hi-IN": "क्या बहुत ज्यादा प्यास, मुंह सूखना, खड़े होने पर चक्कर, या पेशाब कम आना महसूस हो रहा है?",
                    "te-IN": "తీవ్రమైన దాహం, నోరు ఎండిపోవడం, లేచినప్పుడు కళ్ళు తిరగడం లేదా మూత్రం తగ్గిపోవడం జరిగిందా?",
                    "or-IN": "ଅତ୍ୟଧିକ ଶୋଷ, ପାଟି ଶୁଖିବା, ଛିଡ଼ା ହେଲେ ମୁଣ୍ଡ ଘୁରାଇବା ବା ପରିସ୍ରା କମିଯିବା ହୋଇଛି କି?",
                    "ta-IN": "அதிக தாகம், நாக்கு வறட்சி அல்லது சிறுநீர் குறைந்துள்ளதா?"
                },
                "quick_picks": ["Extreme thirst & dry mouth", "Feeling dizzy / lightheaded when standing", "Urine output significantly reduced / dark", "Drinking ORS / adequate hydration maintained"]
            }
        ]
    },

    "urinary_symptoms": {
        "domain": "urinary_symptoms",
        "label": "Urinary Tract & Renal Evaluation",
        "triggers": [
            r"\burin\w*", r"\bdysuria\b", r"\bhematuria\b", r"\bbladder\b",
            r"पेशाब", r"मूत्र", r"మూత్రం", r"சிறுநீர்", r"ପରିସ୍ରା",
            r"peshab", r"mutram", r"parisra", r"siruneer"
        ],
        "hpi_fields": ["dysuria", "frequency", "hematuria", "flank_pain", "fever_rigors"],
        "ros_systems": ["urinary", "renal"],
        "red_flag_terms": ["visible blood in urine", "anuria", "severe flank colic", "rigors"],
        "questions": [
            {
                "id": "hpi.urinary.dysuria_frequency",
                "priority": PRIORITY_P1,
                "state_key": "character",
                "section": "Dysuria & Urgency",
                "why_asking": "Screens for lower urinary tract infection (cystitis/urethritis).",
                "text": {
                    "en-IN": "Do you feel a burning sensation or pain when urinating, or an urgent need to urinate frequently?",
                    "hi-IN": "क्या पेशाब करते समय जलन या दर्द होता है, या बार-बार तुरंत पेशाब जाने की इच्छा होती है?",
                    "te-IN": "మూత్రం పోసేటప్పుడు మంట లేదా నొప్పి ఉందా, లేదా తరచుగా మూత్రానికి వెళ్లాల్సి వస్తుందా?",
                    "or-IN": "ପରିସ୍ରା କଲାବେଳେ ପୋଡ଼ାଜଳା ବା ଯନ୍ତ୍ରଣା ହେଉଛି କି, କିମ୍ବା ବାରମ୍ବାର ପରିସ୍ରା ଲାଗୁଛି କି?",
                    "ta-IN": "சிறுநீர் கழிக்கும் போது எரிச்சல் அல்லது அவசரமாக போக வேண்டுமா?"
                },
                "quick_picks": ["Burning pain during urination (Dysuria)", "Urgent need to urinate every few minutes", "Difficulty starting urine stream / weak flow", "Pain at end of urination"]
            },
            {
                "id": "hpi.urinary.hematuria_color",
                "priority": PRIORITY_P0,
                "state_key": "safety_check",
                "section": "Hematuria & Urine Color",
                "why_asking": "Rules out frank hematuria (calculus, malignancy, glomerulonephritis).",
                "text": {
                    "en-IN": "Have you seen any red blood, pink tint, or dark cola color in your urine?",
                    "hi-IN": "क्या पेशाब में खून, गुलाबी रंग, या गहरा भूरा रंग दिखाई दिया है?",
                    "te-IN": "మూత్రంలో రక్తం, గులాబీ రంగు లేదా ముదురు రంగు గమనించారా?",
                    "or-IN": "ପରିସ୍ରାରେ ରକ୍ତ, ଗୋଲାପି ରଙ୍ଗ ବା କଳା ରଙ୍ଗ ଦେଖାଯାଇଛି କି?",
                    "ta-IN": "சிறுநீரில் ரத்தம் அல்லது அடர் நிறம் உள்ளதா?"
                },
                "quick_picks": ["Visible red blood in urine (Hematuria)", "Cloudy foul-smelling urine", "Normal pale yellow color", "Dark concentrated yellow"]
            },
            {
                "id": "hpi.urinary.flank_fever",
                "priority": PRIORITY_P1,
                "state_key": "associated_symptoms",
                "section": "Upper Tract & Kidney Signs",
                "why_asking": "Differentiates simple cystitis from pyelonephritis or ureteric stone colic.",
                "text": {
                    "en-IN": "Do you have sharp pain in your side or back (flank), or high fever with shivering chills?",
                    "hi-IN": "क्या कमर के एक तरफ या पसलियों के नीचे तेज दर्द है, या कंपकंपी के साथ तेज बुखार है?",
                    "te-IN": "నడుము ఒక వైపు తీవ్రమైన నొప్పి లేదా చలితో కూడిన జ్వరం ఉందా?",
                    "or-IN": "କଡ଼ରେ ବା ଅଣ୍ଟାରେ ତୀବ୍ର ଯନ୍ତ୍ରଣା, କିମ୍ବା କମ୍ପ ସହିତ ଜ୍ୱର ଅଛି କି?",
                    "ta-IN": "பக்கவாட்டில் வலி அல்லது நடுக்கத்துடன் காய்ச்சல் உள்ளதா?"
                },
                "quick_picks": ["Severe one-sided flank pain radiating to groin (Renal colic)", "High fever with chills (Pyelonephritis concern)", "No back pain or fever", "Mild lower pelvic ache only"]
            }
        ]
    },

    "dizziness": {
        "domain": "dizziness",
        "label": "Dizziness, Vertigo & Syncope Evaluation",
        "triggers": [
            r"\bdizz\w*", r"\bvertigo\b", r"\blightheaded\b", r"\bgiddiness\b", r"\bfaint\b",
            r"चक्कर", r"కళ్ళు తిరగడం", r"மயக்கம்", r"ମୁଣ୍ଡ ଘୁରାଇବା", r"ଚକ୍କର",
            r"chakkar", r"kallu\s*thiragadam", r"thala\s*suttrudhu", r"munda\s*ghuriba"
        ],
        "hpi_fields": ["true_vertigo", "presyncope", "head_movement_trigger", "ear_symptoms", "neuro_flags"],
        "ros_systems": ["neurological", "ent", "cardiovascular"],
        "red_flag_terms": ["syncope", "loss of consciousness", "diplopia", "ataxia"],
        "questions": [
            {
                "id": "hpi.dizziness.vertigo_type",
                "priority": PRIORITY_P1,
                "state_key": "character",
                "section": "Vertigo vs Lightheadedness",
                "why_asking": "Differentiates true vestibular spinning vertigo from cardiovascular presyncope/orthostasis.",
                "text": {
                    "en-IN": "Does the room feel like it is spinning around you (vertigo), or do you feel lightheaded like you might black out or faint?",
                    "hi-IN": "क्या ऐसा लगता है कि कमरा या पंखा घूम रहा है (वर्टिगो), या कमजोरी से आंखों के आगे अंधेरा छाने जैसा लगता है?",
                    "te-IN": "గది గిర్రున తిరుగుతున్నట్లు ఉందా (వెర్టిగో), లేదా కళ్ళు చీకట్లు కమ్మి స్పృహ తప్పుతుందేమో అనిపిస్తుందా?",
                    "or-IN": "ଘର ବା ଆଖପାଖ ଘୁରୁଥିବା ପରି ଲାଗୁଛି କି, କିମ୍ବା ଆଖି ଆଗରେ ଅନ୍ଧାର ଛାଇ ହୋଇ ବେହୋସ ହେଲା ଭଳି ଲାଗୁଛି?",
                    "ta-IN": "அறை சுற்றுவது போல் உள்ளதா அல்லது மயக்கம் வருவது போல் உள்ளதா?"
                },
                "quick_picks": ["Room spinning around me (True Vertigo)", "Lightheaded / Feeling faint on standing", "Unsteadiness / Loss of balance while walking", "Floating woozy sensation"]
            },
            {
                "id": "hpi.dizziness.triggers",
                "priority": PRIORITY_P1,
                "state_key": "triggers",
                "section": "Positional Triggers",
                "why_asking": "Identifies BPPV (triggered by rolling in bed / tilting head) vs orthostatic hypotension on standing.",
                "text": {
                    "en-IN": "Does turning your head, rolling over in bed, or suddenly standing up trigger or worsen the dizziness?",
                    "hi-IN": "क्या सिर घुमाने, बिस्तर पर करवट लेने, या अचानक खड़े होने पर चक्कर बढ़ते हैं?",
                    "te-IN": "తల తిప్పినప్పుడు, మంచంపై పక్కకు తిరిగినప్పుడు లేదా హఠాత్తుగా నిలబడినప్పుడు కళ్ళు తిరుగుతున్నాయా?",
                    "or-IN": "ମୁଣ୍ଡ ଘୁରାଇଲେ, ବିଛଣାରେ କଡ଼ ଲେଉଟାଇଲେ ବା ହଠାତ୍ ଛିଡ଼ା ହେଲେ ଚକ୍କର ବଢୁଛି କି?",
                    "ta-IN": "தலையை திருப்பும்போது அல்லது படுக்கையில் புரளும்போது தலை சுற்றுகிறதா?"
                },
                "quick_picks": ["Triggered by rolling over in bed or looking up (BPPV pattern)", "Triggered only when standing up quickly (Orthostatic)", "Constant dizziness regardless of position", "Triggered by loud sounds or crowded places"]
            },
            {
                "id": "hpi.dizziness.associated",
                "priority": PRIORITY_P1,
                "state_key": "associated_symptoms",
                "section": "Associated Auditory & Neuro Features",
                "why_asking": "Screens for Meniere's disease, acoustic neuroma, or posterior circulation stroke.",
                "text": {
                    "en-IN": "Do you have ringing in your ears (tinnitus), hearing loss, ear fullness, or double vision?",
                    "hi-IN": "क्या कान में सीटी जैसी आवाज (टिनिटस), कम सुनाई देना, कान में भारीपन, या एक चीज दो दिखाई देती है?",
                    "te-IN": "చెవుల్లో రింగింగ్ శబ్దం, వినికిడి తగ్గడం లేదా ఒక వస్తువు రెండుగా కనిపించడం ఉందా?",
                    "or-IN": "କାନରେ ଶବ୍ଦ ହେବା, କମ୍ ଶୁଣାଯିବା, କାନ ଭାରୀ ଲାଗିବା ବା ଗୋଟିଏ ଜିନିଷ ଦୁଇଟି ଦେଖାଯାଉଛି କି?",
                    "ta-IN": "காது இரைச்சல், கேட்கும் திறன் குறைவு அல்லது இரட்டை பார்வை உள்ளதா?"
                },
                "quick_picks": ["Ringing sound in ears (Tinnitus)", "Hearing loss or ear fullness in one ear", "Nausea or vomiting with dizziness", "No ear symptoms or visual changes"]
            }
        ]
    },

    "skin_allergy": {
        "domain": "skin_allergy",
        "label": "Dermatology, Rash & Urticaria Evaluation",
        "triggers": [
            r"\brash\b", r"\bitch\w*", r"\bhives\b", r"\burticaria\b", r"\bskin\s*allergy\b",
            r"चकत्ते", r"खुजली", r"ఎలర్జీ", r"దురద", r"சொறி", r"தினவு", r"ଚର୍ମ କୁଣ୍ଡିଆ", r"ଫଳିବା",
            r"khujli", r"chakatte", r"durada", r"kundia"
        ],
        "hpi_fields": ["location", "morphology", "itching_severity", "triggers_meds", "mucosal_involvement"],
        "ros_systems": ["dermatological", "allergy"],
        "red_flag_terms": ["lip swelling", "tongue swelling", "blistering all over", "throat tightness"],
        "questions": [
            {
                "id": "hpi.skin.location_spread",
                "priority": PRIORITY_P1,
                "state_key": "location",
                "section": "Rash Distribution & Spread",
                "why_asking": "Documents extent and anatomical pattern of dermatological lesions.",
                "text": {
                    "en-IN": "Where on your body did the rash or itching start, and is it spreading to other areas?",
                    "hi-IN": "त्वचा पर दाने या खुजली कहाँ से शुरू हुई, और क्या यह शरीर के बाकी हिस्सों में फैल रही है?",
                    "te-IN": "చర్మంపై దద్దుర్లు లేదా దురద ఎక్కడ మొదలైంది? ఇతర భాగాలకు వ్యాపిస్తోందా?",
                    "or-IN": "ଚର୍ମରେ କୁଣ୍ଡିଆ ବା ଲାଲ ଦାଗ କେଉଁଠୁ ଆରମ୍ଭ ହେଲା, ଏବଂ ଅନ୍ୟ ଜାଗାକୁ ବ୍ୟାପୁଛି କି?",
                    "ta-IN": "தடிப்புகள் எங்கு தொடங்கியது? உடலின் மற்ற பகுதிகளுக்கு பரவுகிறதா?"
                },
                "quick_picks": ["Localized to arms / legs only", "Spread all over chest, back & abdomen", "Face, neck and scalp involved", "Confined to hands or feet only"]
            },
            {
                "id": "hpi.skin.character",
                "priority": PRIORITY_P1,
                "state_key": "character",
                "section": "Lesion Morphology",
                "why_asking": "Distinguishes urticarial wheals from eczematous scaly plaques, viral exanthem, or blistering pemphigoid.",
                "text": {
                    "en-IN": "What does the rash look like — raised red itchy welts (hives), fluid-filled blisters, dry scaly patches, or flat red spots?",
                    "hi-IN": "चकत्ते कैसे दिखते हैं — लाल उभरे हुए चकत्ते (पित्ती), पानी भरे छाले, सूखी पपड़ीदार त्वचा, या चपटे लाल धब्बे?",
                    "te-IN": "దద్దుర్లు ఎలా ఉన్నాయి — ఎర్రటి దద్దుర్లు (హైవ్స్), నీటి బొబ్బలు, పొడి పొట్టు రాలే మచ్చలా?",
                    "or-IN": "ଦାଗଗୁଡ଼ିକ କିପରି ଦେଖାଯାଉଛି — ଫଳିଯାଇଥିବା ଲାଲ ଚିହ୍ନ, ପାଣି ଫୋଟକା ନା ଶୁଖିଲା ଖାଉଟି ପରି?",
                    "ta-IN": "தடிப்புகள் கொப்புளங்களாக உள்ளதா அல்லது சிவந்த தடிப்புகளா?"
                },
                "quick_picks": ["Raised itchy wheals / hives (Urticaria)", "Fluid-filled blisters or peeling skin", "Dry, red, scaly itching patches", "Tiny red dots (Petechiae concern)"]
            },
            {
                "id": "hpi.skin.triggers_meds",
                "priority": PRIORITY_P1,
                "state_key": "triggers",
                "section": "Drug & Allergen Exposure",
                "why_asking": "Identifies drug-induced eruptions (SJS/DRESS) or contact allergens.",
                "text": {
                    "en-IN": "Did this begin after taking any new antibiotic or medication, using a new soap/detergent, or eating specific foods?",
                    "hi-IN": "क्या यह किसी नई दवा, एंटीबायोटिक, नए साबुन/डिटर्जेंट, या किसी खास खाने के बाद शुरू हुआ?",
                    "te-IN": "ఏదైనా కొత్త మందు, యాంటీబయాటిక్, కొత్త సబ్బు లేదా ఆహారం తీసుకున్న తర్వాత మొదలైందా?",
                    "or-IN": "କୌଣସି ନୂଆ ଔଷଧ ଖାଇବା ପରେ, ନୂଆ ସାବୁନ ବ୍ୟବହାର କଲେ ବା କୌଣସି ଖାଦ୍ୟରୁ ଏହା ଆରମ୍ଭ ହେଲା କି?",
                    "ta-IN": "புதிய மருந்து, சோப் அல்லது உணவுக்குப் பிறகு தொடங்கியதா?"
                },
                "quick_picks": ["Started after taking a new prescription / antibiotic", "After contact with new soap, detergent, or plant", "After eating seafood, nuts, or specific food", "No known exposure / Came without clear trigger"]
            }
        ]
    },

    "diabetes_metabolic": {
        "domain": "diabetes_metabolic",
        "label": "Diabetes, Glycemic & Metabolic Intake",
        "triggers": [
            r"\bdiabetes\b", r"\bsugar\b", r"\bglucose\b", r"\bhba1c\b",
            r"मधुमेह", r"शुगर", r"చక్కెర వ్యాధి", r"சர்க்கரை நோய்", r"ମଧୁମେହ", r"ଚିନି ରୋଗ"
        ],
        "hpi_fields": ["polyuria", "polydipsia", "hypoglycemia", "foot_ulcers", "med_compliance"],
        "ros_systems": ["endocrine", "renal", "ophthalmic"],
        "red_flag_terms": ["frequent hypoglycemia", "non healing ulcer", "gangrene", "fruity breath"],
        "questions": [
            {
                "id": "hpi.diabetes.polyuria_thirst",
                "priority": PRIORITY_P1,
                "state_key": "character",
                "section": "Osmotic Symptoms",
                "why_asking": "Screens for uncontrolled hyperglycemia (polyuria, polydipsia, weight loss).",
                "text": {
                    "en-IN": "Are you experiencing excessive thirst, waking up multiple times at night to urinate, or unexplained weight loss?",
                    "hi-IN": "क्या बहुत ज्यादा प्यास लगना, रात में बार-बार पेशाब के लिए उठना, या वजन कम होना महसूस हो रहा है?",
                    "te-IN": "విపరీతమైన దాహం, రాత్రిపూట మాటిమాటికి మూత్రానికి వెళ్లడం, బరువు తగ్గడం గమనించారా?",
                    "or-IN": "ଅତ୍ୟଧିକ ଶୋଷ ଲାଗିବା, ରାତିରେ ବାରମ୍ବାର ପରିସ୍ରା ଯିବା ବା ଓଜନ କମିବା ହୋଇଛି କି?",
                    "ta-IN": "அதிக தாகம், இரவில் அடிக்கடி சிறுநீர் கழிப்பது உள்ளதா?"
                },
                "quick_picks": ["Excessive urination especially at night (Polyuria)", "Extreme unquenchable thirst", "Sudden unexplained weight loss", "Well-controlled / No osmotic symptoms"]
            },
            {
                "id": "hpi.diabetes.hypoglycemia_feet",
                "priority": PRIORITY_P1,
                "state_key": "safety_check",
                "section": "Hypoglycemia & Peripheral Neuropathy",
                "why_asking": "Evaluates medication safety (hypoglycemia episodes) and diabetic foot / neuropathy.",
                "text": {
                    "en-IN": "Do you get episodes of sweating, shakiness, or dizziness between meals, or burning numbness in your feet?",
                    "hi-IN": "क्या खाने के बीच में अचानक पसीना, हाथ कांपना, या चक्कर आते हैं? क्या पैरों में जलन या सुन्नपन है?",
                    "te-IN": "ఆహారాల మధ్యలో వణుకు, చెమటలు, కళ్ళు తిరగడం లేదా కాళ్ళలో మంటలు/మొద్దుబారడం ఉందా?",
                    "or-IN": "ଖାଇବା ଡେରି ହେଲେ ଝାଳ ବୋହିବା, ହାତ ଥରିବା, କିମ୍ବା ପାଦରେ ପୋଡ଼ାଜଳା ବା କାଲୁଆ ଲାଗୁଛି କି?",
                    "ta-IN": "நடுக்கம், வியர்வை அல்லது கால்களில் எரிச்சல் உள்ளதா?"
                },
                "quick_picks": ["Frequent episodes of shakiness & sweating (Low sugar)", "Burning numbness & pins-and-needles in feet", "Recent non-healing blister or foot wound", "No hypo episodes or numbness"]
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
                "state_key": "character",
                "section": "BP Control & Symptoms",
                "why_asking": "Screens for hypertensive urgency (morning occipital headache, blurred vision, dizziness).",
                "text": {
                    "en-IN": "What was your most recent BP reading, and are you experiencing throbbing morning headaches at the back of your head or blurred vision?",
                    "hi-IN": "आपकी हाल की बीपी रीडिंग क्या थी? क्या सिर के पिछले हिस्से में सुबह का तेज दर्द या धुंधला दिखाई देता है?",
                    "te-IN": "మీ ఇటీవలి బీపీ ఎంత ఉంది? ఉదయాన్నే తల వెనుక భాగంలో నొప్పి లేదా కంటి చూపు మసకబారడం ఉందా?",
                    "or-IN": "ଆପଣଙ୍କର ନିକଟତମ ବିପି କେତେ ଥିଲା? ସକାଳେ ମୁଣ୍ଡର ପଛ ପାଖ ବିନ୍ଧିବା ବା ଝାପ୍‌ସା ଦେଖାଯାଉଛି କି?",
                    "ta-IN": "சமீபத்திய இரத்த அழுத்த அளவு என்ன? காலையில் தலைவலி உள்ளதா?"
                },
                "quick_picks": ["Recent BP high (> 160/100 mmHg)", "Throbbing headache at back of head on waking", "Blurred vision or seeing spots", "Taking medicines regularly / BP in normal range"]
            }
        ]
    },

    "throat_symptoms": {
        "domain": "throat_symptoms",
        "label": "ENT, Pharyngitis & Tonsillar Evaluation",
        "triggers": [
            r"\bthroat\w*", r"\bswallow\w*", r"\bpharyngitis\b", r"\btonsil\b", r"\bhoarse\b",
            r"गले में दर्द", r"गला खराब", r"గొంతు నొప్పి", r"தொண்டை வலி", r"ଗଳା ଯନ୍ତ୍ରଣା", r"ଗଳା ଖରାପ",
            r"gala\s*dard", r"gonthu\s*noppi", r"gala\s*kharap"
        ],
        "hpi_fields": ["pain_swallowing", "drooling", "voice_change", "ear_pain"],
        "ros_systems": ["ent", "respiratory"],
        "red_flag_terms": ["cannot swallow saliva", "drooling", "stridor", "trismus", "unable to open mouth"],
        "questions": [
            {
                "id": "hpi.throat.swallow_character",
                "priority": PRIORITY_P1,
                "state_key": "character",
                "section": "Sore Throat & Odynophagia",
                "why_asking": "Evaluates painful swallowing (odynophagia) and checks for peritonsillar abscess signs.",
                "text": {
                    "en-IN": "Does your throat feel raw and scratchy, or is there sharp pain specifically when swallowing food and liquids?",
                    "hi-IN": "क्या गले में केवल खराश है, या खाना-पानी निगलते समय तेज दर्द होता है?",
                    "te-IN": "గొంతు గరుకుగా ఉందా, లేదా ఆహారం, నీళ్లు మింగేటప్పుడు తీవ్రమైన నొప్పి వస్తోందా?",
                    "or-IN": "ଗଳାରେ କେବଳ ଖରଖର ଲାଗୁଛି, ନା ଖାଦ୍ୟ ବା ପାଣି ଢୋକିବା ବେଳେ ତୀବ୍ର କଷ୍ଟ ହେଉଛି?",
                    "ta-IN": "தொண்டை கரகரப்பாக உள்ளதா அல்லது விழுங்கும்போது வலிக்கிறதா?"
                },
                "quick_picks": ["Severe pain when swallowing (Odynophagia)", "Dry scratchy raw sensation", "Pain radiates to one ear", "Mild irritation only"]
            },
            {
                "id": "hpi.throat.airway_safety",
                "priority": PRIORITY_P0,
                "state_key": "safety_check",
                "section": "Airway Obstruction Red Flags",
                "why_asking": "Rules out epiglottitis or deep neck space infection causing stridor or trismus.",
                "text": {
                    "en-IN": "Can you swallow your own saliva, or are you drooling, unable to open your mouth wide, or having noisy breathing?",
                    "hi-IN": "क्या आप थूक निगल पा रहे हैं, या मुंह खोलने में दिक्कत और सांस में आवाज आ रही है?",
                    "te-IN": "లాలాజలం మింగగలుగుతున్నారా, లేదా నోరు తెరవడం కష్టంగా ఉందా?",
                    "or-IN": "ଛେପ ଢୋକି ପାରୁଛନ୍ତି କି, କିମ୍ବା ପାଟି ଖୋଲିବା ବା ନିଶ୍ୱାସ ନେବା କଷ୍ଟ ହେଉଛି କି?",
                    "ta-IN": "எச்சில் முழுங்க முடிகிறதா அல்லது மூச்சு விட சிரமமா?"
                },
                "quick_picks": ["Can swallow saliva without difficulty", "Difficulty opening mouth wide (Trismus)", "Drooling / Unable to swallow saliva", "Hoarse muffled 'hot-potato' voice"],
                "red_flag_triggers": ["cannot swallow saliva", "drooling", "unable to open mouth", "stridor"]
            }
        ]
    },

    "weakness_fatigue": {
        "domain": "weakness_fatigue",
        "label": "Systemic Weakness, Fatigue & Anemia Screening",
        "triggers": [
            r"\bweak\w*", r"\bfatigue\b", r"\btired\b", r"\bexhaust\w*", r"\bletharg\w*", r"\banemia\b",
            r"कमजोरी", r"थकान", r"అలసట", r"బలహీనత", r"சோர்வு", r"ଦୁର୍ବଳତା", r"କ୍ଳାନ୍ତ",
            r"kamzori", r"thakan", r"alasata", r"durbalata"
        ],
        "hpi_fields": ["duration", "exertional_dyspnea", "pallor", "weight_loss", "dizziness"],
        "ros_systems": ["hematological", "endocrine", "cardiovascular"],
        "red_flag_terms": ["unexplained rapid weight loss", "severe pallor", "fainting on minimal effort"],
        "questions": [
            {
                "id": "hpi.fatigue.duration_functional",
                "priority": PRIORITY_P1,
                "state_key": "duration",
                "section": "Fatigue Duration & Impact",
                "why_asking": "Determines chronicity and functional impairment from systemic fatigue.",
                "text": {
                    "en-IN": "How long have you felt this weakness, and does it prevent you from completing your daily routine or work?",
                    "hi-IN": "यह कमजोरी कितने समय से है, और क्या यह आपके रोजमर्रा के काम करने में बाधा डाल रही है?",
                    "te-IN": "ఈ బలహీనత ఎంత కాలంగా ఉంది? మీ రోజువారీ పనులు చేసుకోలేనంతగా ఉందా?",
                    "or-IN": "ଏହି ଦୁର୍ବଳତା କେତେ ଦିନରୁ ଲାଗୁଛି, ଏବଂ ଏହା ଦୈନନ୍ଦିନ କାମ କରିବାରେ ବାଧା ସୃଷ୍ଟି କରୁଛି କି?",
                    "ta-IN": "இந்த சோர்வு எவ்வளவு நாட்களாக உள்ளது? வேலை செய்ய முடிகிறதா?"
                },
                "quick_picks": ["Started recently over past few days", "Present for 2 to 4 weeks", "Chronic ongoing exhaustion for months", "Prevents basic household tasks"]
            },
            {
                "id": "hpi.fatigue.anemia_signs",
                "priority": PRIORITY_P1,
                "state_key": "associated_symptoms",
                "section": "Anemia & Systemic Signs",
                "why_asking": "Screens for iron deficiency anemia, thyroid dysfunction, or occult bleeding.",
                "text": {
                    "en-IN": "Have you noticed pale skin/eyes, shortness of breath after climbing just a few stairs, or dizziness when standing?",
                    "hi-IN": "क्या आंखें या नाखून पीले पड़े हैं, थोड़ी दूर चलने पर सांस फूलती है, या खड़े होने पर चक्कर आते हैं?",
                    "te-IN": "కళ్ళు లేదా గోర్లు పాలిపోయాయా, కొద్దిగా నడిచినా ఆయాసం వస్తుందా?",
                    "or-IN": "ଆଖି ବା ନଖ ଧଳା ପଡ଼ିଯାଇଛି କି, ଟିକେ ଚାଲିଲେ ଶ୍ୱାସ ବଢ଼ୁଛି ବା ମୁଣ୍ଡ ଘୁରାଉଛି କି?",
                    "ta-IN": "கண்கள் வெளிறிப் போய் உள்ளதா? மூச்சு திணறல் ஏற்படுகிறதா?"
                },
                "quick_picks": ["Pale eyes/nails & breathlessness on minor walking", "Feeling dizzy upon standing up quickly", "Cold hands and feet with hair fall", "No breathlessness or paleness"]
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
        "state_key": "past_medical",
        "text": {
            "en-IN": "Have you ever been diagnosed with any major long-term medical conditions like Diabetes, High BP, Heart Disease, Kidney Disease, or Asthma?",
            "hi-IN": "क्या आपको पहले कोई पुरानी बीमारी हुई है जैसे डायबिटीज, हाई बीपी, हृदय रोग, किडनी रोग, या अस्थमा?",
            "te-IN": "మీకు గతంలో డయాబెటిస్, హై బీపీ, గుండె జబ్బు, కిడ్నీ సమస్య లేదా ఆస్తమా వంటి దీర్ఘకాలిక వ్యాధులు ఉన్నాయా?",
            "or-IN": "ଆପଣଙ୍କର ପୂର୍ବରୁ କୌଣସି ପୁରୁଣା ରୋଗ ହୋଇଛି କି — ମଧୁମେହ, ହାଇ ବିପି, ହୃଦରୋଗ, କିଡନୀ ରୋଗ ବା ଶ୍ୱାସ?",
            "ta-IN": "சர்க்கரை நோய், இரத்த அழுத்தம், இதய நோய் போன்ற நீண்டகால நோய்கள் உள்ளதா?"
        },
        "quick_picks": ["Diabetes Mellitus", "Hypertension (High BP)", "Coronary Heart Disease", "Asthma / Bronchitis", "None / No known conditions"]
    },
    {
        "id": "psh.prior_surgeries",
        "priority": PRIORITY_P2,
        "category": "past_surgical",
        "state_key": "past_surgical",
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
        "state_key": "medications",
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
        "state_key": "allergies",
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

# ==============================================================================
# AYURVEDA CLINICAL CASE-TAKING PATHWAY (SIH PS 26047)
# ==============================================================================
AYURVEDA_PATHWAY: List[Dict[str, Any]] = [
    {
        "id": "ayush.prakriti",
        "priority": PRIORITY_P1,
        "state_key": "prakriti",
        "section": "Ayurvedic Prakriti",
        "category": "ayurveda",
        "why_asking": "Determines constitutional Dosha dominance (Vata, Pitta, Kapha) to individualize diagnosis.",
        "text": {
            "en-IN": "Regarding your natural constitution (Prakriti): Do you naturally have dry skin and light build (Vata), feel warm easily with sharp digestion (Pitta), or have a solid build and calm nature (Kapha)?",
            "hi-IN": "आपकी शारीरिक प्रकृति के अनुसार — क्या आपकी त्वचा रूखी और शरीर हल्का है (वात), जल्दी गर्मी लगती है और तीखी भूख होती है (पित्त), या भारी शरीर और शांत स्वभाव है (कफ)?",
            "te-IN": "మీ సహజ శరీర తత్వం (ప్రకృతి) గురించి — పొడి చర్మం (వాతం), ఎక్కువ వేడి/తీవ్ర ఆకలి (పిత్తం), లేదా దృఢమైన శరీరం/ప్రశాంతత (కఫం) కలిగి ఉన్నారా?",
            "or-IN": "ଆପଣଙ୍କ ପ୍ରକୃତି କିପରି — ଶୁଖିଲା ଚର୍ମ (ବାତ), ଶୀଘ୍ର ଗରମ ହେବା (ପିତ୍ତ), ନା ଭାରୀ ଶରୀର ଓ ଶାନ୍ତ ସ୍ୱଭାବ (କଫ)?",
            "ta-IN": "உங்கள் உடல் இயல்பு எப்படி — வாதம், பித்தம் அல்லது கபமா?"
        },
        "quick_picks": [
            "Vata dominant (Light build, dry skin, sensitive to cold)",
            "Pitta dominant (Medium build, warm body, sharp appetite)",
            "Kapha dominant (Solid build, calm, slow metabolism)",
            "Vata-Pitta mixed",
            "Tridoshic (Balanced)"
        ]
    },
    {
        "id": "ayush.agni_ahara",
        "priority": PRIORITY_P1,
        "state_key": "agni",
        "section": "Agni & Ahara Shakti",
        "category": "ayurveda",
        "why_asking": "Assesses digestive fire (Agni) and metabolic power (Ahara Shakti) which govern pathogenesis.",
        "text": {
            "en-IN": "How is your digestive fire (Agni)? Do you have intense sharp hunger (Tikshnagni), sluggish digestion with heaviness (Mandagni), irregular appetite (Vishamagni), or normal appetite (Samagni)?",
            "hi-IN": "आपकी पाचन शक्ति (अग्नि) कैसी है — बहुत तेज भूख लगना (तीक्ष्णाग्नि), खाना खाने के बाद भारीपन व सुस्त पाचन (मंदाग्नि), कभी भूख लगना कभी नहीं (विषमाग्नि), या सामान्य पाचन (समाग्नि)?",
            "te-IN": "మీ జీర్ణశక్తి (అగ్ని) ఎలా ఉంది — ఎక్కువ ఆకలా, తిన్నాక బరువుగా మందకొడిగా ఉంటుందా, లేదా సమతుల్యంగా ఉందా?",
            "or-IN": "ଆପଣଙ୍କ ହଜମ ଶକ୍ତି କିପରି — ବହୁତ ଜୋର୍ ଭୋକ, ଖାଇବା ପରେ ଭାରୀ ଲାଗିବା, ନା ନିୟମିତ ଭୋକ?",
            "ta-IN": "உங்கள் செரிமான சக்தி எப்படி உள்ளது?"
        },
        "quick_picks": [
            "Samagni (Balanced, timely appetite & comfortable digestion)",
            "Tikshnagni (Excessive intense hunger, burning acidity)",
            "Mandagni (Poor appetite, post-meal heaviness, coating on tongue)",
            "Vishamagni (Irregular, unpredictable hunger)"
        ]
    },
    {
        "id": "ayush.koshtha",
        "priority": PRIORITY_P2,
        "state_key": "koshtha",
        "section": "Koshtha (Bowel Habit)",
        "category": "ayurveda",
        "why_asking": "Identifies bowel sensitivity and laxative response (Krura, Madhyama, Mridu Koshtha).",
        "text": {
            "en-IN": "How are your bowel movements (Koshtha)? Do you suffer from hard dry stools (Krura Koshtha), loose stools from mild milk or fruit intake (Mridu Koshtha), or regular clear motions (Madhyama)?",
            "hi-IN": "आपका पेट साफ कैसा होता है (कोष्ठ) — क्या कड़ा मल और कब्ज रहता है (क्रूर कोष्ठ), हल्का दूध या फल लेने पर भी दस्त हो जाते हैं (मृदु कोष्ठ), या सामान्य रोज साफ होता है (मध्यम)?",
            "te-IN": "మీ మలవిసర్జన ఎలా ఉంటుంది — మలబద్ధకమా, సులభంగా విరేచనమవుతుందా, లేదా సాధారణమా?",
            "or-IN": "ପେଟ ସଫା କିପରି ହୁଏ — କଠିନ ଝାଡ଼ା (କ୍ରୂର), କ୍ଷୀର ଖାଇଲେ ପତଳା ଝାଡ଼ା (ମୃଦୁ), ନା ପ୍ରତିଦିନ ସ୍ୱାଭାବିକ ସଫା?",
            "ta-IN": "மலச்சிக்கல் உள்ளதா அல்லது எளிதாக மலம் கழிகிறதா?"
        },
        "quick_picks": [
            "Krura Koshtha (Hard dry stools, tendency to constipation)",
            "Mridu Koshtha (Very soft/loose bowels, easily purged by warm milk)",
            "Madhyama Koshtha (Regular once-daily comfortable motion)"
        ]
    },
    {
        "id": "ayush.nidra_manas",
        "priority": PRIORITY_P2,
        "state_key": "nidra",
        "section": "Nidra & Manasika Bhava",
        "category": "ayurveda",
        "why_asking": "Evaluates sleep quality (Nidra) and mental state (Satva/Manas) for holistic formulation.",
        "text": {
            "en-IN": "How is your sleep (Nidra) and mental state? Do you sleep deeply, have disturbed sleep with excessive thoughts, or feel anxious and restless?",
            "hi-IN": "आपकी नींद (निद्रा) और मानसिक स्थिति कैसी है — क्या गहरी नींद आती है, बार-बार नींद टूटती है, या चिंता और बेचैनी रहती है?",
            "te-IN": "మీ నిద్ర మరియు మానసిక స్థితి ఎలా ఉంది — గాఢనిద్రా, లేదా ఆందోళనతో కూడిన మెలకువలా?",
            "or-IN": "ଆପଣଙ୍କ ନିଦ ଓ ମାନସିକ ସ୍ଥିତି କିପରି — ଗାଢ଼ ନିଦ ହୁଏ, ନିଦ ଭାଙ୍ଗିଯାଏ, ନା ଚିନ୍ତା ଓ ଅଶାନ୍ତି ଲାଗି ରହେ?",
            "ta-IN": "தூக்கம் நன்றாக வருகிறதா அல்லது பதற்றமாக உள்ளதா?"
        },
        "quick_picks": [
            "Sound restorative sleep (6-8 hours)",
            "Disturbed sleep / Difficulty falling asleep (Anidra)",
            "Excessive daytime sleepiness / Lethargy (Atinidra)",
            "Restless mind with worry or tension"
        ]
    }
]

# ==============================================================================
# HOMEOPATHY CLINICAL CASE-TAKING PATHWAY (SIH PS 26047)
# ==============================================================================
HOMEOPATHY_PATHWAY: List[Dict[str, Any]] = [
    {
        "id": "homeo.modalities",
        "priority": PRIORITY_P1,
        "state_key": "modalities",
        "section": "Homeopathic Modalities",
        "category": "homeopathy",
        "why_asking": "Aggravating and relieving triggers (Modalities) are the core foundation of homeopathic symptom differentiation.",
        "text": {
            "en-IN": "What specific conditions make your symptoms better or worse (Modalities)? For example: warmth, cold, open air, resting, moving, pressure, or a particular time of day?",
            "hi-IN": "किन चीजों से आपकी तकलीफ बढ़ती या घटती है — जैसे ठंड, गर्मी, खुली हवा, आराम करना, चलना, दबाना या दिन/रात का कोई समय?",
            "te-IN": "ఏ పరిస్థితులలో మీ లక్షణాలు పెరుగుతాయి లేదా తగ్గుతాయి — వేడి, చలి, గాలి, విశ్రాంతి, నడక వల్లనా?",
            "or-IN": "କେଉଁ କାରଣରୁ ଯନ୍ତ୍ରଣା ବଢ଼ୁଛି ବା କମୁଛି — ଥଣ୍ଡା, ଗରମ, ଚାଲିବା, ବିଶ୍ରାମ ବା ଦବାଇବା?",
            "ta-IN": "எந்த நேரத்தில் அல்லது சூழ்நிலையில் உங்கள் வலி கூடுகிறது அல்லது குறைகிறது?"
        },
        "quick_picks": [
            "Worse from cold, better from warmth",
            "Worse from heat, better in cool open air",
            "Worse from first movement, better with continued motion",
            "Better with firm pressure or lying on painful side",
            "Worse in early morning (3-5 AM)",
            "Worse at night or lying down"
        ]
    },
    {
        "id": "homeo.generals_thermal_thirst",
        "priority": PRIORITY_P2,
        "state_key": "thermal_and_thirst",
        "section": "Homeopathic Generals",
        "category": "homeopathy",
        "why_asking": "Constitutional generals (thermal reaction and thirst) help understand overall systemic reactivity.",
        "text": {
            "en-IN": "In general, are you a person who feels cold easily (chilly) or one who cannot tolerate heat? How is your thirst for water?",
            "hi-IN": "सामान्यतः, क्या आपको ठंड जल्दी लगती है या गर्मी बिल्कुल बर्दाश्त नहीं होती? आपको प्यास कैसी लगती है?",
            "te-IN": "సాధారణంగా మీకు చలి ఎక్కువ వేస్తుందా లేదా వేడి తట్టుకోలేరా? దాహం ఎలా ఉంటుంది?",
            "or-IN": "ସାଧାରଣତଃ ଆପଣଙ୍କୁ ଥଣ୍ଡା ଶୀଘ୍ର ଲାଗେ ନା ଗରମ ସହ୍ୟ ହୁଏନାହିଁ? ପାଣି ପିଇବା ତୃଷ୍ଣା କିପରି?",
            "ta-IN": "உங்களுக்கு குளிர் ஒத்துக்கொள்ளாதா அல்லது வெப்பம் ஒத்துக்கொள்ளாதா? தாகம் எப்படி?"
        },
        "quick_picks": [
            "Chilly person (Sensitive to cold, drafts, wants warm clothes)",
            "Hot person (Cannot tolerate heat/warm rooms, wants cool air)",
            "Very thirsty for large quantities of cold water",
            "Thirstless / rarely feels thirsty",
            "Thirsty for small sips frequently"
        ]
    },
    {
        "id": "homeo.cravings_aversions",
        "priority": PRIORITY_P2,
        "state_key": "cravings_aversions",
        "section": "Food Desires & Aversions",
        "category": "homeopathy",
        "why_asking": "Documents systemic dietary affinities and sensitivities for homeopathic repertorization.",
        "text": {
            "en-IN": "Do you have any strong food cravings, aversions, or foods that clearly disagree with you (e.g. sweets, salt, spicy, fatty foods, sour items)?",
            "hi-IN": "क्या आपको किसी विशेष खाने की तीव्र इच्छा या अरुचि है — जैसे मीठा, नमकीन, तीखा, वसायुक्त भोजन या खट्टा?",
            "te-IN": "మీకు ప్రత్యేకంగా ఇష్టమైన లేదా నచ్చని ఆహారాలు ఏవైనా ఉన్నాయా — తీపి, ఉప్పు, కారం లేదా పులుపు?",
            "or-IN": "କୌଣସି ଖାଦ୍ୟ ପ୍ରତି ଅଧିକ ଇଚ୍ଛା ବା ଅରୁଚି ଅଛି କି — ମିଠା, ଲୁଣିଆ, ରାଗ ବା ତେଲିଆ ଖାଦ୍ୟ?",
            "ta-IN": "உங்களுக்கு ஏதேனும் உணவு மீது அதிக விருப்பம் அல்லது வெறுப்பு உள்ளதா?"
        },
        "quick_picks": [
            "Strong craving for sweets and sugar",
            "Strong desire for salty foods",
            "Desire for spicy and pungent food",
            "Aversion to fatty or greasy foods",
            "Milk or dairy causes digestive upset",
            "No specific food cravings"
        ]
    },
    {
        "id": "homeo.mental_emotional",
        "priority": PRIORITY_P2,
        "state_key": "mental_emotional",
        "section": "Mental & Emotional History",
        "category": "homeopathy",
        "why_asking": "Assists the clinician in understanding the mental-emotional plane in relation to physical complaints.",
        "text": {
            "en-IN": "How has your mental and emotional state been alongside this complaint — are you feeling anxious, irritable, restless, weepy, or needing quiet solitude?",
            "hi-IN": "इस तकलीफ के दौरान आपकी मानसिक और भावनात्मक स्थिति कैसी है — क्या चिंता, चिड़चिड़ापन, बेचैनी या उदासी महसूस होती है?",
            "te-IN": "ఈ సమస్యతో పాటు మీ మానసిక స్థితి ఎలా ఉంది — ఆందోళన, కోపం, నిరాశ లేదా ఒంటరిగా ఉండాలనే భావన ఉందా?",
            "or-IN": "ଏହି ଅସୁବିଧା ସହିତ ମାନସିକ ସ୍ଥିତି କିପରି ଅଛି — ଚିନ୍ତା, ବିରକ୍ତିଭାବ, ଅଶାନ୍ତି ବା ଏକୁଟିଆ ରହିବାର ଇଚ୍ଛା?",
            "ta-IN": "உங்கள் மனநிலை மற்றும் உணர்ச்சி நிலை எப்படி உள்ளது?"
        },
        "quick_picks": [
            "Anxious & worried about health",
            "Restless (Constantly moving, unable to stay calm)",
            "Irritable and easily angered",
            "Mild, emotional, comforted by consolation",
            "Calm and composed baseline"
        ]
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

def get_ayurveda_pathway() -> List[Dict[str, Any]]:
    """Returns the structured Ayurveda clinical pathway."""
    return AYURVEDA_PATHWAY

def get_homeopathy_pathway() -> List[Dict[str, Any]]:
    """Returns the structured Homeopathy clinical pathway."""
    return HOMEOPATHY_PATHWAY
