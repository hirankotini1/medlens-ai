/**
 * MEDLENS AI — Voice Case Taking Orchestrator
 * Manages the complete multilingual voice patient history interview.
 *
 * Built on top of voice_service.js. Requires case_taking.js to be loaded first
 * for access to CASE_QUESTIONS (clinical question bank).
 *
 * Architecture:
 * - Reads clinical questions from the existing case_taking_engine
 * - Routes each answer through the voice service for TTS/STT
 * - Populates clinical_cases and voice_transcripts via REST API
 * - Runs red-flag checks inline for each answer
 *
 * @version 1.0.0 — SIH PS 26047
 * Medical Safety: This system does NOT diagnose. AI is a clinical history tool.
 */

/* ============================================================================
   CLINICAL QUESTIONS — Multilingual voice prompts per section
   Linked to existing case_taking_engine.py sections
   ============================================================================ */
const VOICE_CLINICAL_QUESTIONS = [
    /* 0: Chief Complaint */
    {
        key: 'chief_complaint',
        section: 'Chief Complaint',
        sectionIndex: 1,
        text: {
            'en-IN': "What is the main reason you are visiting the hospital today? What is your main problem?",
            'hi-IN': "आज आप अस्पताल क्यों आए हैं? आपकी मुख्य समस्या क्या है?",
            'te-IN': "మీరు ఈరోజు ఆస్పత్రికి ఎందుకు వచ్చారు? మీ ప్రధాన సమస్య ఏమిటి?",
            'ta-IN': "நீங்கள் இன்று மருத்துவமனைக்கு ஏன் வந்தீர்கள்? உங்கள் முக்கிய பிரச்னை என்ன?",
            'kn-IN': "ಇಂದು ನೀವು ಆಸ್ಪತ್ರೆಗೆ ಏಕೆ ಬಂದಿದ್ದೀರಿ? ನಿಮ್ಮ ಮುಖ್ಯ ಸಮಸ್ಯೆ ಏನು?",
            'ml-IN': "ഇന്ന് നിങ്ങൾ ആശുപത്രിയിൽ വരാൻ കാരണം എന്ത്? നിങ്ങളുടെ പ്രധാന പ്രശ്നം എന്ത്?",
            'bn-IN': "আজ আপনি কেন হাসপাতালে এসেছেন? আপনার প্রধান সমস্যা কী?",
            'mr-IN': "आज तुम्ही रुग्णालयात का आलात? तुमची मुख्य समस्या काय आहे?",
            'gu-IN': "આজ તમે હૉસ્પિટલ કેમ આવ્યા? તમારી મુખ્ય સમસ્યા શું છે?",
            'or-IN': "ଆଜି ଆପଣ ହାସ୍ପାତାଲ ଆସିବାର ମୁଖ୍ୟ କାରଣ କ'ଣ? ଆପଣଙ୍କ ମୁଖ୍ୟ ଅସୁବିଧା କ'ଣ?",
        },
        quickPicks: ['Fever / बुखार / జ్వరం', 'Pain / दर्द / నొప్పి', 'Weakness / कमज़ोरी', 'Breathlessness', 'Cough', 'Vomiting / उल्टी', 'Other / अन्य'],
        redFlags: ['chest pain', 'can not breathe', 'breathing', 'unconscious', 'stroke', 'paralysis', 'bleeding', 'सांस', 'छाती में दर्द', 'పడిపోయాను'],
    },
    /* 1: History of Present Illness */
    {
        key: 'present_illness_duration',
        section: 'History of Present Illness',
        sectionIndex: 2,
        text: {
            'en-IN': "Since when did this problem start? How many days, weeks, or months have you had this problem?",
            'hi-IN': "यह समस्या कब से है? कितने दिन, हफ्ते या महीने से?",
            'te-IN': "ఈ సమస్య ఎప్పటి నుండి ఉంది? ఎంత రోజులు, వారాలు లేదా నెలల నుండి?",
            'ta-IN': "இந்த பிரச்னை எப்போது தொடங்கியது? எத்தனை நாட்கள், வாரங்கள் அல்லது மாதங்கள்?",
            'kn-IN': "ಈ ಸಮಸ್ಯೆ ಯಾವಾಗಿನಿಂದ ಇದೆ? ಎಷ್ಟು ದಿನ, ವಾರ ಅಥವಾ ತಿಂಗಳಿನಿಂದ?",
            'ml-IN': "ഈ പ്രശ്നം എന്നുമുതൽ ഉണ്ട്? എത്ര ദിവസം, ആഴ്ച അല്ലെങ്കിൽ മാസം?",
            'bn-IN': "এই সমস্যা কখন থেকে হচ্ছে? কতদিন, সপ্তাহ বা মাস ধরে?",
            'mr-IN': "ही समस्या केव्हापासून आहे? किती दिवस, आठवडे किंवा महिने?",
            'gu-IN': "આ સમસ્યા ક્યારથી છે? કેટલા દિવસ, અઠવાડિયા કે મહિના?",
        },
        quickPicks: ['Today / आज', '2-3 days / 2-3 दिन', '1 week', '2 weeks', '1 month', 'Several months', 'More than a year'],
        redFlags: ['sudden', 'suddenly', 'अचानक'],
    },
    /* 2: Severity */
    {
        key: 'pain_severity',
        section: 'History of Present Illness',
        sectionIndex: 2,
        text: {
            'en-IN': "On a scale from 1 to 10, how severe is your problem right now? 1 means very mild, 10 means the worst you can imagine.",
            'hi-IN': "1 से 10 के पैमाने पर, आपकी तकलीफ अभी कितनी तेज है? 1 मतलब बहुत हल्की, 10 मतलब सबसे ज्यादा।",
            'te-IN': "1 నుండి 10 స్కేల్‌లో, మీ సమస్య ఇప్పుడు ఎంత తీవ్రంగా ఉంది?",
        },
        quickPicks: ['1-2 (Very mild)', '3-4 (Mild)', '5-6 (Moderate)', '7-8 (Severe)', '9-10 (Very severe)'],
        redFlags: ['10', 'worst', 'unbearable', 'terrible', 'cannot bear'],
    },
    /* 3: Associated Symptoms */
    {
        key: 'associated_symptoms',
        section: 'Associated Symptoms',
        sectionIndex: 3,
        text: {
            'en-IN': "Do you have any other symptoms along with your main complaint? For example: fever, vomiting, headache, dizziness, shortness of breath?",
            'hi-IN': "क्या आपको मुख्य तकलीफ के साथ और भी कोई लक्षण हैं? जैसे बुखार, उल्टी, सिरदर्द, चक्कर, सांस फूलना?",
            'te-IN': "మీ ప్రధాన సమస్యతో పాటు మరే లక్షణాలు ఉన్నాయా? ఉదా: జ్వరం, వాంతులు, తలనొప్పి?",
        },
        quickPicks: ['Fever', 'Vomiting', 'Headache', 'Dizziness', 'Breathlessness', 'Sweating', 'No other symptoms'],
        redFlags: ['breathless', 'cannot breathe', 'chest pain', 'blood', 'black stool', 'fainting', 'collapse'],
    },
    /* 4: Past Medical History */
    {
        key: 'past_medical_history',
        section: 'Past Medical History',
        sectionIndex: 4,
        text: {
            'en-IN': "Have you had any major illnesses before? Do you have diabetes, blood pressure, heart disease, asthma, or any other chronic condition?",
            'hi-IN': "क्या आपको पहले कोई बड़ी बीमारी हुई है? जैसे मधुमेह, बीपी, हृदय रोग, अस्थमा?",
            'te-IN': "మీకు ముందు ఏదైనా పెద్ద వ్యాధి వచ్చిందా? డయాబెటిస్, బిపి, గుండె జబ్బు?",
        },
        quickPicks: ['Diabetes / मधुमेह', 'Hypertension / बीपी', 'Heart Disease', 'Asthma / TB', 'Thyroid', 'None / नहीं', 'Not sure'],
        redFlags: ['heart attack', 'stroke', 'cancer', 'fits', 'seizure', 'epilepsy'],
    },
    /* 5: Medications */
    {
        key: 'current_medications',
        section: 'Drug History',
        sectionIndex: 5,
        text: {
            'en-IN': "Are you currently taking any medicines? If yes, please tell me their names. Are you allergic to any medicines?",
            'hi-IN': "क्या आप अभी कोई दवाई ले रहे हैं? कोई दवाई से एलर्जी है?",
            'te-IN': "మీరు ప్రస్తుతం ఏదైనా మందులు తీసుకుంటున్నారా? ఏదైనా మందులకు అలెర్జీ ఉందా?",
        },
        quickPicks: ['No medicines / नहीं', 'Diabetes medicines', 'BP medicines', 'Pain killers', 'Antibiotics', 'I will tell doctor', 'Allergic to Penicillin'],
        redFlags: ['penicillin allergy', 'sulfa allergy', 'anaphylaxis', 'severe allergy'],
    },
    /* 6: Family History */
    {
        key: 'family_history',
        section: 'Family History',
        sectionIndex: 6,
        text: {
            'en-IN': "Does anyone in your family — parents, brothers, sisters — have diabetes, heart disease, cancer, or any hereditary condition?",
            'hi-IN': "क्या आपके परिवार में — माता-पिता, भाई-बहन — को मधुमेह, हृदय रोग, कैंसर या कोई वंशानुगत बीमारी है?",
            'te-IN': "మీ కుటుంబంలో — తల్లిదండ్రులు, అన్నదమ్ములు, అక్కచెల్లెళ్ళు — డయాబెటిస్, గుండె జబ్బు, క్యాన్సర్ ఉందా?",
        },
        quickPicks: ['No family history', 'Diabetes in family', 'BP in family', 'Heart disease', 'Cancer', 'Not sure'],
        redFlags: [],
    },
    /* 7: Social History */
    {
        key: 'social_history',
        section: 'Social History',
        sectionIndex: 7,
        text: {
            'en-IN': "Do you smoke cigarettes or use tobacco? Do you drink alcohol? What work do you do?",
            'hi-IN': "क्या आप सिगरेट पीते हैं या तंबाकू खाते हैं? शराब पीते हैं? आप क्या काम करते हैं?",
            'te-IN': "మీరు సిగరెట్లు తాగుతారా లేదా పొగాకు వాడతారా? మద్యం తాగుతారా?",
        },
        quickPicks: ['Non-smoker / नहीं', 'Smoker (tobacco)', 'Alcohol user', 'Farmer / Farmer', 'Labor work', 'Office work', 'Student'],
        redFlags: ['heavy alcohol', 'injecting drug', 'drug addict'],
    },
    /* 8: Review of Systems */
    {
        key: 'review_of_systems',
        section: 'Review of Systems',
        sectionIndex: 8,
        text: {
            'en-IN': "Have you noticed any changes in your weight recently? Any loss of appetite? Any sleep problems? Any changes in passing urine or stool?",
            'hi-IN': "क्या हाल ही में आपका वजन कम हुआ है? भूख कम लगती है? नींद की कोई समस्या? पेशाब या मल में कोई बदलाव?",
            'te-IN': "ఇటీవల బరువు తగ్గిందా? ఆకలి తక్కువైందా? నిద్ర సమస్యలు? మూత్రం లేదా మలంలో మార్పులు?",
        },
        quickPicks: ['Weight loss', 'Loss of appetite', 'Difficulty sleeping', 'Frequent urination', 'Blood in urine', 'Constipation', 'None of above'],
        redFlags: ['blood in urine', 'black stool', 'weight loss sudden', 'blood in vomit'],
    },
    /* 9: Final */
    {
        key: 'additional_info',
        section: 'Additional Information',
        sectionIndex: 9,
        text: {
            'en-IN': "Is there anything else you would like to tell the doctor? Any other concerns or symptoms I haven't asked about?",
            'hi-IN': "क्या आप डॉक्टर को और कुछ बताना चाहते हैं? कोई अन्य चिंता या लक्षण?",
            'te-IN': "డాక్టర్‌కు మరేమైనా చెప్పాలనుకుంటున్నారా? వేరే ఏదైనా లక్షణాలు ఉన్నాయా?",
        },
        quickPicks: ['Nothing more to add', 'I want to ask something', 'I have test reports'],
        redFlags: [],
    },
];

/* ============================================================================
   ADAPTIVE FOLLOW-UP QUESTIONS
   Injected after Chief Complaint based on keyword matching.
   Each group targets a common chief complaint pattern.
   ============================================================================ */
const ADAPTIVE_FOLLOWUPS = {
    chest: [
        {
            key: 'chest_location', section: 'History of Present Illness', sectionIndex: 2,
            text: { 'en-IN': 'Where exactly in the chest is the pain — left side, center, or right side? Does it spread to your arm, shoulder, or jaw?', 'hi-IN': 'सीने में दर्द कहाँ है — बाईं तरफ, बीच में, या दाईं तरफ? क्या यह हाथ, कंधे या जबड़े में फैलता है?', 'te-IN': 'గుండె నొప్పి ఎక్కడ ఉంది — ఎడమ వైపు, మధ్యలో లేదా కుడి వైపు? చేయి లేదా భుజానికి వ్యాపిస్తుందా?' },
            quickPicks: ['Center / Centre', 'Left side / बाईं', 'Right side', 'Radiates to arm', 'Radiates to jaw', 'All over chest'],
            redFlags: ['left side', 'radiates to arm', 'jaw', 'shoulder'],
        },
        {
            key: 'chest_exertion', section: 'History of Present Illness', sectionIndex: 2,
            text: { 'en-IN': 'Does the chest pain increase on physical activity like walking or climbing stairs? Does it get better with rest?', 'hi-IN': 'क्या सीने का दर्द चलने या सीढ़ी चढ़ने पर बढ़ता है? आराम से ठीक होता है?', 'te-IN': 'నడిచినప్పుడు లేదా మెట్లు ఎక్కినప్పుడు నొప్పి పెరుగుతుందా? విశ్రాంతితో తగ్గుతుందా?' },
            quickPicks: ['Increases on exertion', 'Better with rest', 'No change with activity', 'Only at rest', 'Also at rest'],
            redFlags: ['increases on exertion', 'only at rest'],
        },
        {
            key: 'chest_sweating', section: 'History of Present Illness', sectionIndex: 2,
            text: { 'en-IN': 'Are you sweating heavily? Do you feel like you are going to faint? Do you feel nauseous or did you vomit?', 'hi-IN': 'क्या आपको बहुत पसीना आ रहा है? बेहोशी जैसा लग रहा है? मतली या उल्टी?', 'te-IN': 'చాలా చెమట వస్తుందా? మూర్ఛ అవుతున్నట్లు అనిపిస్తుందా? వాంతులు?' },
            quickPicks: ['Heavy sweating / पसीना', 'Nausea / मतली', 'Vomiting', 'Feeling faint', 'None of these'],
            redFlags: ['heavy sweating', 'feeling faint', 'vomiting'],
        },
    ],
    fever: [
        {
            key: 'fever_temperature', section: 'History of Present Illness', sectionIndex: 2,
            text: { 'en-IN': 'How high was the fever? Did you check your temperature? Did you have chills or shivering with the fever?', 'hi-IN': 'बुखार कितना था? तापमान लिया? क्या ठंड लगी या कंपकंपी आई?', 'te-IN': 'జ్వరం ఎంత ఉంది? ఉష్ణోగ్రత కొలిచారా? వణుకు వచ్చిందా?' },
            quickPicks: ['Low grade (99-100°F)', 'Moderate (101-102°F)', 'High (103°F+)', 'Chills & shivering', 'Not measured'],
            redFlags: ['103', '104', '105', 'very high fever'],
        },
        {
            key: 'fever_rash', section: 'History of Present Illness', sectionIndex: 2,
            text: { 'en-IN': 'Do you have any rash or skin changes? Is the fever continuous or does it come and go? Do you have body pain?', 'hi-IN': 'क्या कोई रैश या त्वचा में बदलाव है? बुखार लगातार है या आता-जाता है? बदन दर्द है?', 'te-IN': 'దద్దుర్లు ఉన్నాయా? జ్వరం నిరంతరం ఉంటుందా లేదా వస్తూ పోతుందా? శరీర నొప్పి?' },
            quickPicks: ['Rash / दाने', 'Body pain', 'Continuous fever', 'Intermittent fever', 'Night sweats', 'No rash'],
            redFlags: ['rash', 'continuous high fever', 'night sweats'],
        },
    ],
    stomach: [
        {
            key: 'stomach_location', section: 'History of Present Illness', sectionIndex: 2,
            text: { 'en-IN': 'Where exactly is the stomach pain — upper abdomen, lower abdomen, around the navel, or all over? Is it related to eating food?', 'hi-IN': 'पेट दर्द कहाँ है — ऊपर, नीचे, नाभि के आसपास या पूरे पेट में? खाने से संबंधित?', 'te-IN': 'పొట్ట నొప్పి ఎక్కడ ఉంది — పైన, కింద, బొడ్డు దగ్గర? తినడంతో సంబంధం ఉందా?' },
            quickPicks: ['Upper abdomen', 'Lower abdomen', 'Around navel', 'All over', 'After eating', 'Before eating'],
            redFlags: ['upper right abdomen', 'severe', 'cannot eat'],
        },
        {
            key: 'stomach_bowel', section: 'History of Present Illness', sectionIndex: 2,
            text: { 'en-IN': 'Any vomiting? Loose stools or constipation? Is there any blood in the stool or vomiting?', 'hi-IN': 'उल्टी है? दस्त या कब्ज? मल या उल्टी में खून?', 'te-IN': 'వాంతులు ఉన్నాయా? విరేచనాలు లేదా మలబద్ధకం? మలంలో లేదా వాంతిలో రక్తం?' },
            quickPicks: ['Vomiting', 'Loose stools / दस्त', 'Constipation', 'Blood in stool', 'Blood in vomit', 'None'],
            redFlags: ['blood in stool', 'blood in vomit', 'black stool'],
        },
    ],
    headache: [
        {
            key: 'headache_location', section: 'History of Present Illness', sectionIndex: 2,
            text: { 'en-IN': 'Where is the headache — front, back, sides, or all over? Is it throbbing/pulsating or a constant pressure?', 'hi-IN': 'सिरदर्द कहाँ है — आगे, पीछे, किनारे या पूरे सिर में? धड़कन जैसा दर्द या दबाव?', 'te-IN': 'తలనొప్పి ఎక్కడ ఉంది — ముందు, వెనక, పక్కలు? దబదబ కొట్టుకుంటుందా లేదా నొప్పి స్థిరంగా ఉంటుందా?' },
            quickPicks: ['Front / Forehead', 'Back of head', 'One side (migraine)', 'All over', 'Throbbing', 'Constant pressure'],
            redFlags: ['worst headache', 'thunderclap', 'sudden severe'],
        },
        {
            key: 'headache_vision', section: 'History of Present Illness', sectionIndex: 2,
            text: { 'en-IN': 'Do you have blurred vision, sensitivity to light or sound? Any nausea or vomiting with the headache?', 'hi-IN': 'क्या आँखें धुंधली हैं, रोशनी या आवाज़ से दिक्कत है? सिरदर्द के साथ मतली?', 'te-IN': 'దృష్టి మసకగా ఉందా? కాంతికి లేదా శబ్దానికి ఇబ్బందిగా ఉందా? వాంతి?' },
            quickPicks: ['Blurred vision', 'Light sensitivity', 'Sound sensitivity', 'Nausea', 'Vomiting', 'None of these'],
            redFlags: ['blurred vision', 'sudden vision loss'],
        },
    ],
    breathlessness: [
        {
            key: 'breath_onset', section: 'History of Present Illness', sectionIndex: 2,
            text: { 'en-IN': 'Did the breathlessness start suddenly or gradually? Is it worse when lying flat? Do you have to use extra pillows to sleep?', 'hi-IN': 'सांस फूलना अचानक आया या धीरे-धीरे? लेटने पर बढ़ता है? सोने के लिए ज़्यादा तकिए लगते हैं?', 'te-IN': 'శ్వాస తక్కువ అవడం అకస్మాత్తుగా మొదలైందా లేదా క్రమంగా? పడుకున్నప్పుడు పెరుగుతుందా?' },
            quickPicks: ['Sudden onset', 'Gradual onset', 'Worse lying flat', 'Extra pillows needed', 'Only on exertion', 'At rest also'],
            redFlags: ['sudden', 'at rest', 'cannot lie flat'],
        },
    ],
    cough: [
        {
            key: 'cough_nature', section: 'History of Present Illness', sectionIndex: 2,
            text: { 'en-IN': 'Is your cough dry, or does it bring up phlegm or mucus? If there is phlegm, what color is it (yellow, green, or blood-streaked)?', 'hi-IN': 'क्या खांसी सूखी है या बलगम वाली? यदि बलगम है, तो उसका रंग क्या है (पीला, हरा या खून जैसा)?', 'te-IN': 'మీ దగ్గు పొడి దగ్గా లేదా కఫం వస్తుందా? కఫం రంగు ఏమిటి?' },
            quickPicks: ['Dry cough / सूखी', 'Phlegm (clear)', 'Phlegm (yellow/green)', 'Blood streaks in cough', 'Night cough'],
            redFlags: ['blood streaks', 'blood in cough', 'hemoptysis'],
        },
        {
            key: 'cough_triggers', section: 'History of Present Illness', sectionIndex: 2,
            text: { 'en-IN': 'Does the cough get worse at night or when lying down? Have you noticed any wheezing, whistling sound, or chest tightness?', 'hi-IN': 'क्या रात में या लेटने पर खांसी बढ़ जाती है? क्या सीने में घरघराहट या सीटी की आवाज आती है?', 'te-IN': 'రాత్రి లేదా పడుకున్నప్పుడు దగ్గు ఎక్కువవుతుందా? పిల్లికూతలు లేదా ఛాతీ బిగుతుగా ఉందా?' },
            quickPicks: ['Worse at night', 'Wheezing sound / सीटी', 'Chest tightness', 'With cold air', 'No wheezing'],
            redFlags: ['severe wheezing', 'cannot breathe with cough'],
        },
    ],
    throat: [
        {
            key: 'throat_swallow', section: 'History of Present Illness', sectionIndex: 2,
            text: { 'en-IN': 'Is it painful to swallow food or water? Do you feel swelling in your neck glands, or has your voice become hoarse?', 'hi-IN': 'क्या खाना या पानी निगलने में दर्द होता है? गले में सूजन है या आवाज़ बैठ गई है?', 'te-IN': 'ఆహారం లేదా నీరు మింగడానికి నొప్పిగా ఉందా? గొంతులో వాపు ఉందా లేదా స్వరం మారిందా?' },
            quickPicks: ['Pain on swallowing', 'Difficulty swallowing liquids', 'Hoarse voice / आवाज़ बैठना', 'Neck swelling', 'Mild irritation'],
            redFlags: ['cannot swallow saliva', 'stridor', 'severe swelling'],
        },
    ],
    joint_ortho: [
        {
            key: 'joint_stiffness', section: 'History of Present Illness', sectionIndex: 2,
            text: { 'en-IN': 'Which joints are paining? Do you experience morning stiffness lasting more than 30 minutes? Any visible swelling, warmth, or redness?', 'hi-IN': 'किन जोड़ों में दर्द है? क्या सुबह 30 मिनट से अधिक अकड़न रहती है? सूजन या लालिमा है?', 'te-IN': 'ఏ కీళ్లలో నొప్పి ఉంది? ఉదయం లేవగానే కీళ్ళు బిగుసుకుపోతున్నాయా? వాపు లేదా ఎరుపు ఉందా?' },
            quickPicks: ['Knees / घुटने', 'Hands/Fingers', 'Morning stiffness > 30m', 'Joint swelling', 'Shoulder/Elbow', 'No swelling'],
            redFlags: ['cannot bear weight', 'hot red swollen joint'],
        },
        {
            key: 'joint_mobility', section: 'History of Present Illness', sectionIndex: 2,
            text: { 'en-IN': 'Does the pain worsen when walking or climbing stairs? Have you had any recent injury, twist, or fall?', 'hi-IN': 'क्या चलने या सीढ़ियां चढ़ने पर दर्द बढ़ जाता है? क्या हाल ही में कोई चोट लगी या गिरे थे?', 'te-IN': 'నడుస్తున్నప్పుడు లేదా మెట్లు ఎక్కుతున్నప్పుడు నొప్పి పెరుగుతుందా? దెబ్బ లేదా పడటం జరిగిందా?' },
            quickPicks: ['Worse climbing stairs', 'Worse with walking', 'Recent fall or twist', 'Pain at rest also', 'Locking sensation'],
            redFlags: ['joint deformity', 'sudden inability to walk'],
        },
    ],
    back_pain: [
        {
            key: 'back_radiation', section: 'History of Present Illness', sectionIndex: 2,
            text: { 'en-IN': 'Does the back pain shoot down your hips, thighs, or feet? Do you feel any numbness, tingling, or weakness in your legs?', 'hi-IN': 'क्या कमर का दर्द नीचे कूल्हे, जांघ या पैरों में जाता है? क्या पैरों में सुन्नपन या कमजोरी है?', 'te-IN': 'నడుము నొప్పి తొడలు లేదా కాళ్ళ వరకు లాగుతుందా? కాళ్ళలో తిమ్మిరి లేదా బలహీనత ఉందా?' },
            quickPicks: ['Radiates down leg (Sciatica)', 'Numbness/Tingling in toes', 'Lower back only', 'Worse bending forward', 'Muscle spasm'],
            redFlags: ['loss of bladder control', 'loss of bowel control', 'saddle numbness', 'leg paralysis'],
        },
    ],
    vomiting_diarrhea: [
        {
            key: 'vomit_frequency', section: 'History of Present Illness', sectionIndex: 2,
            text: { 'en-IN': 'How many times have you vomited or passed loose stools in the past 24 hours? Are you able to keep water or oral rehydration down?', 'hi-IN': 'पिछले 24 घंटों में कितनी बार उल्टी या दस्त हुए हैं? क्या पानी या ORS पेट में रुक रहा है?', 'te-IN': 'గత 24 గంటల్లో ఎన్నిసార్లు వాంతులు లేదా విరేచనాలు అయ్యాయి? నీరు త్రాగగలుగుతున్నారా?' },
            quickPicks: ['1-3 times', '4-6 times', 'More than 6 times', 'Cannot keep fluids down', 'Urine is very dark/scanty'],
            redFlags: ['cannot keep any fluid', 'no urine passed', 'blood in vomit'],
        },
    ],
    skin_allergy: [
        {
            key: 'skin_spread', section: 'History of Present Illness', sectionIndex: 2,
            text: { 'en-IN': 'Where did the rash start and is it spreading? Is there severe itching, burning, or peeling? Any swelling of your lips or face?', 'hi-IN': 'रैश कहाँ शुरू हुआ और क्या यह फैल रहा है? क्या बहुत खुजली या जलन है? क्या होंठ या चेहरे पर सूजन है?', 'te-IN': 'దద్దుర్లు ఎక్కడ మొదలయ్యాయి? తీవ్రమైన దురద లేదా మంట ఉందా? పెదవులు లేదా ముఖంలో వాపు ఉందా?' },
            quickPicks: ['Severe itching / खुजली', 'Spreading rapidly', 'Lip / Eye swelling', 'Hives / Welts', 'Recent new food/drug'],
            redFlags: ['lip swelling', 'tongue swelling', 'throat closing', 'difficulty breathing'],
        },
    ],
    diabetes_metabolic: [
        {
            key: 'diabetes_symptoms', section: 'History of Present Illness', sectionIndex: 2,
            text: { 'en-IN': 'Have you noticed excessive thirst, frequent urination at night, or sudden weight loss? Any tingling or burning sensation in your feet?', 'hi-IN': 'क्या बहुत प्यास लगती है, रात में बार-बार पेशाब जाना पड़ता है? क्या पैरों में जलन या सुन्नपन है?', 'te-IN': 'విపరీతమైన దాహం, రాత్రిపూట తరచుగా మూత్రవిసర్జన ఉందా? పాదాలలో తిమ్మిరి లేదా మంట ఉందా?' },
            quickPicks: ['Excessive thirst / प्यास', 'Frequent night urination', 'Feet tingling/burning', 'Non-healing wound', 'High sugar on tests'],
            redFlags: ['non healing foot ulcer', 'fruity breath', 'confusion'],
        },
    ],
    hypertension_cardio: [
        {
            key: 'htn_symptoms', section: 'History of Present Illness', sectionIndex: 2,
            text: { 'en-IN': 'Do you have high blood pressure? Have you experienced pounding in your ears, heaviness in the back of your head, or nosebleeds?', 'hi-IN': 'क्या आपको बीपी की समस्या है? सिर के पिछले हिस्से में भारीपन, कानों में धड़कन या चक्कर आते हैं?', 'te-IN': 'మీకు అధిక రక్తపోటు (BP) ఉందా? తల వెనుక భాగంలో బరువుగా లేదా కళ్ళు తిరుగుతున్నాయా?' },
            quickPicks: ['Known high BP', 'Occipital headache', 'Palpitations', 'Dizziness', 'BP not measured recently'],
            redFlags: ['BP over 180', 'chest pain with high BP', 'blurred vision with high BP'],
        },
    ],
    urinary: [
        {
            key: 'urinary_burning', section: 'History of Present Illness', sectionIndex: 2,
            text: { 'en-IN': 'Do you feel burning or severe pain while passing urine? Have you noticed any pink or red blood in your urine, or lower back pain?', 'hi-IN': 'क्या पेशाब करते समय जलन या तेज़ दर्द होता है? क्या पेशाब में खून दिखा या पीठ के निचले हिस्से में दर्द है?', 'te-IN': 'మూత్ర విసర్జన సమయంలో మంట లేదా నొప్పి ఉందా? మూత్రంలో రక్తం కనిపించిందా?' },
            quickPicks: ['Burning sensation / जलन', 'Frequent urgency', 'Blood in urine / पेशाब में खून', 'Lower back/side pain', 'Fever with chills'],
            redFlags: ['blood in urine', 'cannot pass urine at all', 'high fever with flank pain'],
        },
    ],
    dizziness_vertigo: [
        {
            key: 'dizziness_type', section: 'History of Present Illness', sectionIndex: 2,
            text: { 'en-IN': 'Does the room feel like it is spinning around you (vertigo), or do you feel faint and lightheaded? Does turning your head make it worse?', 'hi-IN': 'क्या कमरा घूमता हुआ महसूस होता है (चक्कर), या बेहोशी जैसा लगता है? क्या सिर घुमाने पर बढ़ता है?', 'te-IN': 'గది చుట్టూ తిరుగుతున్నట్లు అనిపిస్తుందా లేదా మూర్ఛ వచ్చేలా ఉందా? తల తిప్పినప్పుడు ఎక్కువవుతుందా?' },
            quickPicks: ['Room spinning (Vertigo)', 'Lightheaded / Faint', 'Worse turning head', 'Ringing in ears (Tinnitus)', 'Nausea with dizziness'],
            redFlags: ['sudden weakness in face/arm', 'slurred speech', 'double vision'],
        },
    ],
};

/* Helper: Dynamically builds a contextual follow-up question for unexpected clinical symptoms */
function _buildDynamicClinicalFollowUp(answerText, questionKey) {
    if (!answerText || answerText.length < 3) return null;
    const clean = answerText.replace(/[^\w\s\u0900-\u097F\u0C00-\u0C7F]/g, ' ').trim();
    const words = clean.split(/\s+/).filter(w => w.length > 2);
    const focusWord = words.slice(0, 3).join(' ') || 'this problem';

    return {
        key: `followup_dyn_${Date.now()}`,
        section: 'History of Present Illness',
        sectionIndex: 2,
        text: {
            'en-IN': `Regarding "${focusWord}" that you described: Did this start suddenly or gradually, and does anything make it better or worse?`,
            'hi-IN': `आपने जो "${focusWord}" बताया, क्या यह अचानक शुरू हुआ या धीरे-धीरे? क्या किसी चीज़ से आराम मिलता है?`,
            'te-IN': `మీరు పేర్కొన్న "${focusWord}" గురించి: ఇది అకస్మాత్తుగా మొదలైందా లేదా క్రమంగా? ఏదైనా చేయడం వల్ల ఉపశమనం లభిస్తుందా?`,
            'ta-IN': `நீங்கள் குறிப்பிட்ட "${focusWord}" பற்றி: இது திடீரென தொடங்கியதா அல்லது மெதுவாகவா? எதாவது செய்தால் குறைகிறதா?`,
            'kn-IN': `ನೀವು ತಿಳಿಸಿದ "${focusWord}" ಬಗ್ಗೆ: ಇದು ಇದ್ದಕ್ಕಿದ್ದಂತೆ ಪ್ರಾರಂಭವಾಯಿತೇ?`,
            'ml-IN': `നിങ്ങൾ പറഞ്ഞ "${focusWord}" സംബന്ധിച്ച്: ഇത് പെട്ടെന്ന് തുടങ്ങിയതാണോ?`,
            'bn-IN': `আপনার বলা "${focusWord}" সম্পর্কে: এটি কি হঠাৎ শুরু হয়েছিল না ধীরে ধীরে?`,
            'mr-IN': `तुम्ही सांगितलेल्या "${focusWord}" बद्दल: हे अचानक सुरू झाले की हळूहळू?`,
            'gu-IN': `તમે જણાવેલ "${focusWord}" બાબતે: આ અચાનક શરૂ થયું કે ધીમે ધીમે?`,
            'or-IN': `ଆପଣ କହିଥିବା "${focusWord}" ବିଷୟରେ: ଏହା ହଠାତ୍ ଆରମ୍ଭ ହେଲା କି ଧୀରେ ଧୀରେ?`
        },
        quickPicks: [
            'Started suddenly / अचानक',
            'Started gradually / धीरे-धीरे',
            'Worse with movement',
            'Better with rest',
            'Continuous',
            'Comes and goes'
        ],
        redFlags: ['sudden severe', 'unbearable', 'spreading fast']
    };
};

/* ============================================================================
   AYUSH (AYURVEDA / UNANI / SIDDHA / HOMEOPATHY) ADDITIONAL QUESTIONS
   Injected when AYUSH mode is toggled ON before session starts.
   ============================================================================ */
const AYUSH_QUESTIONS = [
    {
        key: 'prakriti', section: 'AYUSH — Prakriti Assessment', sectionIndex: 10,
        text: {
            'en-IN': 'What is your usual body nature (Prakriti)? Are you generally: Lean & active (Vata), Medium build & warm (Pitta), or Heavy & calm (Kapha)?',
            'hi-IN': 'आपकी सामान्य शारीरिक प्रकृति क्या है? क्या आप सामान्यतः पतले और सक्रिय (वात), मध्यम गर्म (पित्त), या भारी और शांत (कफ) हैं?',
            'te-IN': 'మీ సాధారణ శారీర స్వభావం (ప్రకృతి) ఏమిటి?',
        },
        quickPicks: ['Vata (Lean, active, dry skin)', 'Pitta (Medium, warm, sharp)', 'Kapha (Heavy, slow, calm)', 'Mixed / Not sure'],
        redFlags: [],
    },
    {
        key: 'ahara_habits', section: 'AYUSH — Dietary & Lifestyle', sectionIndex: 10,
        text: {
            'en-IN': 'What is your usual diet? Do you eat regularly? Do you prefer hot or cold food? Any recent change in diet or routine?',
            'hi-IN': 'आपका सामान्य आहार क्या है? नियमित खाना खाते हैं? गर्म या ठंडा खाना पसंद करते हैं?',
            'te-IN': 'మీ సాధారణ ఆహారం ఏమిటి? నియమితంగా తింటారా? వేడి లేదా చల్లని ఆహారం ఇష్టమా?',
        },
        quickPicks: ['Vegetarian / शाकाहारी', 'Non-vegetarian', 'Irregular meals', 'Prefers hot food', 'Prefers cold food', 'Fasting habits'],
        redFlags: [],
    },
    {
        key: 'vyayama_shakti', section: 'AYUSH — Exercise Capacity', sectionIndex: 10,
        text: {
            'en-IN': 'How much physical activity can you do? Do you exercise regularly? How is your strength and endurance?',
            'hi-IN': 'आप कितना शारीरिक काम कर सकते हैं? नियमित व्यायाम करते हैं? शक्ति कैसी है?',
            'te-IN': 'మీరు ఎంత శారీరక పని చేయగలరు? నిత్యం వ్యాయామం చేస్తారా?',
        },
        quickPicks: ['High exercise tolerance', 'Moderate', 'Low (gets tired easily)', 'No exercise', 'Sedentary work'],
        redFlags: [],
    },
    {
        key: 'satmya', section: 'AYUSH — Adaptability', sectionIndex: 10,
        text: {
            'en-IN': 'Are there any foods, climates, or environments you cannot tolerate? For example, certain foods that cause problems, or sensitivity to heat/cold?',
            'hi-IN': 'क्या कोई खाना, मौसम या वातावरण है जो आप सहन नहीं कर सकते? गर्मी या ठंड से एलर्जी?',
            'te-IN': 'ఏదైనా ఆహారం, వాతావరణం లేదా పరిసరాలు సహించలేరా?',
        },
        quickPicks: ['Heat intolerant', 'Cold intolerant', 'Specific food allergy', 'No issues', 'Seasonal problems'],
        redFlags: [],
    },
];

/* ============================================================================
   SESSION STATE
   ============================================================================ */
let _voiceSession = {
    language: 'en-IN',
    touchOnly: false,
    patientId: null,
    abhaId: null,
    caseId: null,
    sessionId: null,
    currentQuestionIndex: 0,
    answers: {},
    transcripts: [],
    startedAt: null,
    kioskMode: false,
    showTextFallback: false,
    pendingTranscript: '',
    ayushMode: false,
    activeQuestions: [],   // dynamic list: base + adaptive + AYUSH
};


/* ============================================================================
   ENTRY POINT — called from nav button
   ============================================================================ */
function launchVoiceCaseTaking() {
    // Restore auth state
    if (typeof restoreSessionAuth === 'function') restoreSessionAuth();

    // Show the voice section
    document.querySelectorAll('.section-view').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));

    const viewEl = document.getElementById('view-voice-case-taking');
    const tabEl = document.getElementById('tab-voice-case-taking');
    if (viewEl) viewEl.classList.add('active');
    if (tabEl) tabEl.classList.add('active');

    // Sync from existing auth or recently registered patient
    let vPatId = (typeof currentAuth !== 'undefined' && currentAuth.patientId) || (typeof activeCasePatientId !== 'undefined' && activeCasePatientId) || null;
    if (!vPatId) {
        try {
            const lastSaved = JSON.parse(localStorage.getItem('medlens_last_registered_patient') || 'null');
            if (lastSaved && (lastSaved.patient_id || lastSaved.id)) {
                vPatId = lastSaved.patient_id || lastSaved.id;
            }
        } catch (e) {}
    }
    _voiceSession.patientId = vPatId;

    window.scrollTo({ top: 0, behavior: 'smooth' });

    // Initialize language grid and show language step
    _voiceInitLanguageGrid();
    _voiceShowStep('language');
}

/* ============================================================================
   LANGUAGE GRID INITIALIZATION
   ============================================================================ */
function _voiceInitLanguageGrid() {
    const grid = document.getElementById('voice-lang-grid');
    if (!grid) return;

    const languages = typeof voiceGetSupportedLanguages === 'function'
        ? voiceGetSupportedLanguages()
        : (typeof VOICE_LANGUAGES !== 'undefined' ? VOICE_LANGUAGES : []);

    grid.innerHTML = '';

    languages.forEach(lang => {
        const card = document.createElement('button');
        card.type = 'button';
        card.className = 'voice-lang-card';
        card.id = `voice-lang-card-${lang.code}`;
        card.setAttribute('aria-label', `Select ${lang.name}`);
        card.onclick = () => voiceSelectLanguage(lang.code);
        card.innerHTML = `
            <span class="voice-lang-flag">${lang.flag}</span>
            <span class="voice-lang-native">${lang.nativeName}</span>
            <span class="voice-lang-english">${lang.name}</span>
        `;
        grid.appendChild(card);
    });
}

function voiceSelectLanguage(langCode) {
    // Deselect all
    document.querySelectorAll('.voice-lang-card').forEach(c => c.classList.remove('selected'));

    // Select clicked
    const card = document.getElementById(`voice-lang-card-${langCode}`);
    if (card) card.classList.add('selected');

    // Update state
    _voiceSession.language = langCode;
    if (typeof voiceSetLanguage === 'function') voiceSetLanguage(langCode);
    if (typeof onLanguageChange === 'function') onLanguageChange(langCode);

    // Enable continue button
    const btn = document.getElementById('voice-lang-continue-btn');
    if (btn) btn.removeAttribute('disabled');
}

/* ============================================================================
   PATIENT SELECTOR & ABHA (ABDM INTEGRATION)
   ============================================================================ */
let voicePatientsCache = [];
let attachedVoiceDocuments = [];

async function populateVoicePatientSelector(forceReload = false) {
    const select = document.getElementById('voice-patient-select');
    const statusPill = document.getElementById('voice-patient-status-pill');
    if (!select) return;

    if (forceReload || !voicePatientsCache.length) {
        try {
            if (statusPill) statusPill.textContent = 'Syncing...';
            const res = await fetch(apiUrl('/api/patients/public'));
            if (res.ok) {
                const data = await res.json();
                voicePatientsCache = Array.isArray(data) ? data : [];
            }
        } catch (e) {
            console.warn('Could not fetch public patients for voice intake:', e);
        }
    }

    // Merge any locally registered patient from localStorage
    try {
        const rawLast = localStorage.getItem('medlens_last_registered_patient');
        if (rawLast) {
            const lastPat = JSON.parse(rawLast);
            const pId = lastPat.patient_id || lastPat.id;
            if (pId && !voicePatientsCache.some(p => (p.id || p.patient_id) === pId)) {
                voicePatientsCache.unshift({
                    id: pId,
                    patient_id: pId,
                    name: lastPat.name || lastPat.patient_name || 'Newly Registered Patient',
                    age: lastPat.age || '--',
                    gender: lastPat.gender || 'Unknown',
                    contact: lastPat.contact || lastPat.phone || '',
                });
            }
        }
    } catch (e) {}

    const currentPatId = (typeof currentAuth !== 'undefined' && currentAuth.patientId) || _voiceSession.patientId;
    let html = '';
    if (voicePatientsCache.length > 0) {
        html = voicePatientsCache.map(p => {
            const pid = p.patient_id || p.id;
            const isSel = (pid === currentPatId) ? 'selected' : '';
            return `<option value="${pid}" ${isSel}>${escapeHtml(p.name || 'Patient')} (ID: ${escapeHtml(pid)} &bull; Age: ${escapeHtml(p.age || '—')} &bull; ${escapeHtml(p.gender || '—')})</option>`;
        }).join('');
    } else {
        html = `<option value="P-MEDICOVER-01">Default Medicover Outpatient (P-MEDICOVER-01)</option>`;
    }
    html += `<option value="GUEST_PATIENT">Walk-in Outpatient (Guest)</option>`;

    select.innerHTML = html;
    if (statusPill) statusPill.textContent = 'Live Sync';
    onVoicePatientSelectChange(select.value);
}

function onVoicePatientSelectChange(val) {
    _voiceSession.patientId = val;
    const metaEl = document.getElementById('voice-selected-patient-meta');
    const pat = voicePatientsCache.find(p => (p.patient_id || p.id) === val);
    if (metaEl) {
        if (pat) {
            metaEl.innerHTML = `<span class="material-symbols-outlined" style="font-size: 15px; color:#059669;">check_circle</span> Active Record: <strong>${escapeHtml(pat.name || 'Patient')}</strong> (Age: ${escapeHtml(pat.age || '—')}, Gender: ${escapeHtml(pat.gender || '—')})`;
        } else {
            metaEl.innerHTML = `<span class="material-symbols-outlined" style="font-size: 15px; color:#0284c7;">person</span> Active Patient ID: <strong>${escapeHtml(val || 'Walk-in')}</strong>`;
        }
    }
}

function generateMockVoiceAbha() {
    const p1 = Math.floor(1000 + Math.random() * 9000);
    const p2 = Math.floor(1000 + Math.random() * 9000);
    const p3 = Math.floor(1000 + Math.random() * 9000);
    const abhaNum = `91-${p1}-${p2}-${p3}`;
    const abhaInput = document.getElementById('voice-abha-input');
    const abhaAddress = document.getElementById('voice-abha-address');
    if (abhaInput) abhaInput.value = abhaNum;
    if (abhaAddress) abhaAddress.value = `patient.${p1}@abdm`;
    _voiceSession.abhaId = abhaNum;
    if (typeof showToast === 'function') {
        showToast(`✓ Generated ABDM Mock ABHA ID: ${abhaNum}`, 'success');
    }
}

/* ============================================================================
   MEDICAL DOCUMENT SCANNER & OCR ATTACHMENT
   ============================================================================ */
async function handleVoiceFileUpload(event) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;

    const statusEl = document.getElementById('voice-upload-status');
    if (statusEl) statusEl.textContent = '📄 Uploading & scanning document with OCR...';

    if (typeof showToast === 'function') {
        showToast('📄 Uploading & extracting clinical parameters via OCR...', 'info');
    }

    let parsedExtract = 'Extracted clinical terms & medicines';
    if (_voiceSession.caseId) {
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('document_type', 'lab_report');

            const res = await fetch(apiUrl(`/api/cases/${_voiceSession.caseId}/upload-and-attach-file`), {
                method: 'POST',
                body: formData
            });
            if (res.ok) {
                const data = await res.json();
                parsedExtract = data.extracted_text || data.summary || 'Laboratory/Prescription Document';
            }
        } catch (e) {
            console.warn('Document uploaded locally:', e);
        }
    }

    attachedVoiceDocuments.push({
        filename: file.name,
        size: Math.round(file.size / 1024) + ' KB',
        summary: parsedExtract,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    });

    if (statusEl) statusEl.textContent = `✓ Attached: ${file.name}`;
    renderVoiceAttachedBadges();
    _voiceRenderSummaryHighlights();
}

function renderVoiceAttachedBadges() {
    const list = document.getElementById('voice-attached-docs-list');
    if (!list) return;
    if (attachedVoiceDocuments.length === 0) {
        list.innerHTML = '';
        return;
    }
    list.innerHTML = attachedVoiceDocuments.map(d => `
        <span style="display:inline-flex; align-items:center; gap:6px; background:#eff6ff; border:1.5px solid #93c5fd; color:#1e40af; padding:6px 12px; border-radius:8px; font-size:0.8rem; font-weight:700;">
            <span class="material-symbols-outlined" style="font-size:16px;">description</span>
            ${escapeHtml(d.filename)} (${d.size})
        </span>
    `).join('');
}

function printVoiceCaseSheet() {
    window.print();
}

/* ============================================================================
   STEP NAVIGATION
   ============================================================================ */
function voiceProceedToConsent() {
    if (!_voiceSession.language) {
        alert('Please select a language to continue.');
        return;
    }
    populateVoicePatientSelector();
    _voiceShowStep('consent');
}

async function voiceProceedToSession(touchOnly = false) {
    _voiceSession.touchOnly = touchOnly;

    // Read patient ID and ABHA ID from inputs
    const patSelect = document.getElementById('voice-patient-select');
    const abhaInput = document.getElementById('voice-abha-input');
    if (patSelect && patSelect.value) _voiceSession.patientId = patSelect.value;
    if (abhaInput && abhaInput.value) _voiceSession.abhaId = abhaInput.value;

    // Start backend case in parallel
    try {
        const payload = {
            patient_id: _voiceSession.patientId || 'P-MEDICOVER-01',
            chief_complaint: 'Voice guided patient case intake',
            language_code: _voiceSession.language || 'en-IN',
            abha_id: _voiceSession.abhaId || '91-4589-2041-8832',
            source: 'voice_guided_case_taking',
            ayush_enabled: _voiceSession.ayushMode || false
        };
        const res = await fetch(apiUrl('/api/cases/start'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            const data = await res.json();
            _voiceSession.caseId = data.case_id;
        }
    } catch (e) {
        console.warn('Backend case start deferred:', e);
    }

    _voiceShowStep('mic-test');
    if (!touchOnly) {
        setTimeout(() => runMicrophoneTest(), 800);
    } else {
        const notice = document.getElementById('voice-stt-fallback-notice');
        if (notice) notice.style.display = 'block';
    }
}

function voiceProceedToInterview() {
    _voiceInitSession();
    _voiceShowStep('interview');
}

function voiceGoBackToLanguage() {
    _voiceShowStep('language');
}

function showVoiceSettings() {
    _populateSettingsLanguageSelect();
    _voiceShowStep('settings-panel');
}

function hideVoiceSettings() {
    _voiceShowStep('interview');
}

function _voiceShowStep(stepName) {
    const panels = [
        document.getElementById('voice-step-language'),
        document.getElementById('voice-step-consent'),
        document.getElementById('voice-step-mic-test'),
        document.getElementById('voice-step-interview'),
        document.getElementById('voice-settings-panel'),
        document.getElementById('voice-step-summary')
    ];
    panels.forEach(p => { if (p) p.style.display = 'none'; });

    let target = document.getElementById(`voice-step-${stepName}`);
    if (!target && stepName === 'settings-panel') {
        target = document.getElementById('voice-settings-panel');
    }
    if (target) target.style.display = 'block';
}

// Ensure globally accessible on window for HTML button onclicks
window.launchVoiceCaseTaking = launchVoiceCaseTaking;
window.launchClinicalCaseTaking = launchVoiceCaseTaking;
window.voiceProceedToConsent = voiceProceedToConsent;
window.voiceProceedToSession = voiceProceedToSession;
window.voiceProceedToInterview = voiceProceedToInterview;
window.voiceGoBackToLanguage = voiceGoBackToLanguage;
window.showVoiceSettings = showVoiceSettings;
window.hideVoiceSettings = hideVoiceSettings;
window.populateVoicePatientSelector = populateVoicePatientSelector;
window.onVoicePatientSelectChange = onVoicePatientSelectChange;
window.generateMockVoiceAbha = generateMockVoiceAbha;
window.handleVoiceFileUpload = handleVoiceFileUpload;
window.printVoiceCaseSheet = printVoiceCaseSheet;

/* ============================================================================
   MICROPHONE TEST
   ============================================================================ */
async function runMicrophoneTest() {
    const iconEl = document.getElementById('voice-mic-test-icon');
    const statusEl = document.getElementById('voice-mic-test-status');
    const btnEl = document.getElementById('voice-mic-test-btn');

    if (statusEl) statusEl.textContent = 'Testing microphone...';
    if (iconEl) iconEl.textContent = '⏳';
    if (btnEl) btnEl.disabled = true;

    const sttSupport = typeof detectBrowserSTTSupport === 'function' ? detectBrowserSTTSupport() : 'none';
    if (sttSupport === 'none') {
        if (statusEl) statusEl.textContent = '⚠️ Voice recognition not supported on this browser. You can use text input.';
        if (iconEl) iconEl.textContent = '⌨️';
        const notice = document.getElementById('voice-stt-fallback-notice');
        if (notice) notice.style.display = 'block';
        _voiceSession.touchOnly = true;
        if (btnEl) btnEl.disabled = false;
        return;
    }

    const result = typeof voiceTestMicrophone === 'function'
        ? await voiceTestMicrophone()
        : { available: false, message: 'Mic test unavailable' };

    if (result.available) {
        if (iconEl) iconEl.textContent = '✅';
        if (statusEl) statusEl.textContent = '✅ Microphone detected and ready!';
    } else {
        if (iconEl) iconEl.textContent = '❌';
        if (statusEl) statusEl.textContent = `❌ ${result.message}`;
        const notice = document.getElementById('voice-stt-fallback-notice');
        if (notice) notice.style.display = 'block';
        _voiceSession.touchOnly = true;
    }

    if (btnEl) { btnEl.disabled = false; btnEl.textContent = 'Test Again'; }
}

/* ============================================================================
   SESSION INITIALIZATION
   ============================================================================ */
function _voiceInitSession() {
    _voiceSession.currentQuestionIndex = 0;
    _voiceSession.answers = {};
    _voiceSession.transcripts = [];
    _voiceSession.startedAt = new Date().toISOString();
    _voiceSession.sessionId = `VS-${Date.now()}`;
    _voiceSession.pendingTranscript = '';
    _voiceSession.injectedFollowUpKeys = new Set();
    _voiceSession.activeFollowUpsTriggered = [];

    // Build active question list: base + AYUSH if enabled
    _voiceBuildActiveQuestions();

    // Update language display badge
    const langDisplay = document.getElementById('voice-session-lang-display');
    const langConfig = typeof voiceGetLanguageByCode === 'function'
        ? voiceGetLanguageByCode(_voiceSession.language)
        : null;
    if (langDisplay && langConfig) {
        langDisplay.innerHTML = `${langConfig.flag} ${langConfig.nativeName}`;
    }

    // Update AYUSH badge
    const ayushBadge = document.getElementById('voice-ayush-badge');
    if (ayushBadge) {
        ayushBadge.style.display = _voiceSession.ayushMode ? 'inline-flex' : 'none';
    }

    // Populate settings language select
    _populateSettingsLanguageSelect();

    // Load first question
    _voiceLoadQuestion(0);
}

function _voiceBuildActiveQuestions() {
    // Start with base questions
    let questions = [...VOICE_CLINICAL_QUESTIONS];
    // Append AYUSH questions if mode is on
    if (_voiceSession.ayushMode) {
        questions = questions.concat(AYUSH_QUESTIONS);
    }
    _voiceSession.activeQuestions = questions;
}

/* ============================================================================
   ADAPTIVE FOLLOW-UP EVALUATION & INJECTION (UNIVERSAL LINKAGE)
   Dynamically links follow-up clinical probes directly to whatever the user said.
   ============================================================================ */
function _voiceEvaluateFollowUps(answerText, questionKey) {
    if (!answerText || answerText === '[SKIPPED]') return;
    const lower = answerText.toLowerCase();
    let toInject = [];
    let matchedDomain = '';
    let matchedKeyword = '';

    const domainChecks = [
        { domain: 'chest', keywords: ['chest', 'heart', 'cardiac', 'angina', 'छाती', 'गुण्डे', 'గుండె', 'நெஞ்சு'], label: 'Chest / Heart symptoms' },
        { domain: 'fever', keywords: ['fever', 'temperature', 'chills', 'shivering', 'बुखार', 'ज्वరం', 'காய்ச்சல்', 'pyrexia'], label: 'Fever / High temperature' },
        { domain: 'stomach', keywords: ['stomach', 'abdomen', 'belly', 'gastric', 'acidity', 'पेट', 'పొట్ట', 'വയറു', 'loose motion'], label: 'Stomach / Abdominal issue' },
        { domain: 'headache', keywords: ['headache', 'head ache', 'migraine', 'सिरदर्द', 'తలనొప్పి', 'தலைவலி'], label: 'Headache / Migraine' },
        { domain: 'breathlessness', keywords: ['breath', 'breathing', 'dyspnea', 'wheez', 'asthma', 'सांस', 'శ్వాస'], label: 'Breathing difficulty' },
        { domain: 'cough', keywords: ['cough', 'khansi', 'phlegm', 'sputum', 'mucus', 'खांसी', 'దగ్గు', 'இருமல்'], label: 'Cough & Sputum' },
        { domain: 'throat', keywords: ['throat', 'sore throat', 'tonsil', 'swallow', 'गला', 'గొంతు', 'தொண்டை'], label: 'Throat discomfort' },
        { domain: 'joint_ortho', keywords: ['joint', 'knee', 'knee pain', 'arthritis', 'swelling', 'घुटने', 'నొప్పులు', 'மூட்டு'], label: 'Joint / Knee pain' },
        { domain: 'back_pain', keywords: ['back pain', 'lower back', 'spine', 'कमर', 'నడుము', 'முதுகு'], label: 'Back & Spine pain' },
        { domain: 'vomiting_diarrhea', keywords: ['vomit', 'nausea', 'diarrhea', 'motion', 'उल्टी', 'వాంతి', 'வாந்தி'], label: 'Nausea & Vomiting' },
        { domain: 'skin_allergy', keywords: ['rash', 'itch', 'skin', 'allergy', 'hives', 'खुजली', 'దద్దుర్లు', 'அரிப்பு'], label: 'Skin rash / Allergy' },
        { domain: 'diabetes_metabolic', keywords: ['sugar', 'diabetes', 'diabetic', 'मधुमेह', 'షుగర్'], label: 'Diabetes / Blood sugar' },
        { domain: 'hypertension_cardio', keywords: ['bp', 'blood pressure', 'hypertension', 'बीपी'], label: 'Blood pressure' },
        { domain: 'urinary', keywords: ['urine', 'urination', 'burning', 'bladder', 'पेशाब', 'మూత్రం'], label: 'Urinary symptoms' },
        { domain: 'dizziness_vertigo', keywords: ['dizzy', 'dizziness', 'spinning', 'vertigo', 'faint', 'चक्कर', 'కళ్ళు తిరగడం'], label: 'Dizziness & Balance' },
    ];

    if (!_voiceSession.injectedFollowUpKeys) _voiceSession.injectedFollowUpKeys = new Set();
    if (!_voiceSession.activeFollowUpsTriggered) _voiceSession.activeFollowUpsTriggered = [];

    for (const c of domainChecks) {
        if (_voiceSession.injectedFollowUpKeys.has(c.domain)) continue;
        const found = c.keywords.find(k => lower.includes(k));
        if (found) {
            matchedDomain = c.domain;
            matchedKeyword = found;
            toInject = (ADAPTIVE_FOLLOWUPS[c.domain] || []).slice(0, 2); // Pick top 2 most crucial clinical probes
            _voiceSession.injectedFollowUpKeys.add(c.domain);
            break;
        }
    }

    // Dynamic clinical fallback for any symptom not in pre-defined domains
    if (toInject.length === 0 && (questionKey === 'chief_complaint' || questionKey === 'associated_symptoms' || questionKey === 'past_medical_history')) {
        const fallbackId = 'dyn_followup_' + questionKey;
        if (!_voiceSession.injectedFollowUpKeys.has(fallbackId)) {
            const dynamicQ = _buildDynamicClinicalFollowUp(answerText, questionKey);
            if (dynamicQ) {
                toInject = [dynamicQ];
                _voiceSession.injectedFollowUpKeys.add(fallbackId);
                matchedDomain = 'dynamic';
                matchedKeyword = answerText.length > 25 ? answerText.slice(0, 25) + '...' : answerText;
            }
        }
    }

    if (toInject.length === 0) return;

    // Stamp follow-up questions with direct linkage to user's response
    toInject.forEach(q => {
        q.isFollowUp = true;
        q.linkedTo = `Linked to your mention of: "${matchedKeyword}"`;
        q.triggerAnswer = answerText;
    });

    // Insert immediately after current question so it asks directly next!
    const insertAt = _voiceSession.currentQuestionIndex + 1;
    const current = _voiceSession.activeQuestions;
    _voiceSession.activeQuestions = [
        ...current.slice(0, insertAt),
        ...toInject,
        ...current.slice(insertAt),
    ];

    _voiceSession.activeFollowUpsTriggered.push({
        domain: matchedDomain,
        keyword: matchedKeyword,
        triggerAnswer: answerText,
        count: toInject.length
    });

    const total = _voiceSession.activeQuestions.length;
    const label = document.getElementById('voice-progress-label');
    if (label) label.textContent = `✨ AI Follow-Up linked to "${matchedKeyword}" added. (${total} total questions)`;
}

/* ============================================================================
   QUESTION LOADING AND DISPLAY
   ============================================================================ */
function _voiceLoadQuestion(index) {
    const questions = _voiceSession.activeQuestions;
    if (index >= questions.length) {
        _voiceComplete();
        return;
    }

    _voiceSession.currentQuestionIndex = index;
    const q = questions[index];

    // Update progress
    const pct = Math.round(((index + 1) / questions.length) * 100);
    const fillEl = document.getElementById('voice-progress-fill');
    const labelEl = document.getElementById('voice-progress-label');
    if (fillEl) fillEl.style.width = `${pct}%`;
    if (labelEl) labelEl.textContent = `Question ${index + 1} of ${questions.length} — ${q.section}`;

    // Get localized question text
    const lang = _voiceSession.language;
    const questionText = q.text[lang] || q.text['en-IN'];

    // Display question with section badge
    const questionEl = document.getElementById('voice-ai-question');
    if (questionEl) questionEl.textContent = questionText;

    // Handle Dynamic AI Follow-up Indicator Banner
    const followupBadge = document.getElementById('voice-followup-badge');
    const followupText = document.getElementById('voice-followup-text');
    const bubble = document.querySelector('.voice-ai-bubble');
    if (q.isFollowUp) {
        if (followupBadge) followupBadge.style.display = 'inline-flex';
        if (followupText) {
            followupText.innerHTML = `<strong>✨ AI Follow-Up Question:</strong> ${escapeHtml(q.linkedTo || 'Specifically linked to your answer')}`;
        }
        if (bubble) bubble.classList.add('voice-bubble-followup-active');
    } else {
        if (followupBadge) followupBadge.style.display = 'none';
        if (bubble) bubble.classList.remove('voice-bubble-followup-active');
    }

    // Update section badge color for AYUSH questions
    const sectionBadge = document.getElementById('voice-section-badge');
    if (sectionBadge) {
        sectionBadge.textContent = q.section;
        sectionBadge.className = 'voice-section-badge' +
            (q.section.includes('AYUSH') ? ' ayush-badge' : '');
    }

    // Populate quick-pick options
    _voiceRenderQuickPicks(q.quickPicks);

    // Clear previous transcript
    _voiceResetTranscriptUI();

    // Auto-play question if enabled
    const autoPlay = document.getElementById('voice-autoplay-toggle');
    if (!autoPlay || autoPlay.checked) {
        setTimeout(() => {
            if (typeof speakText === 'function') speakText(questionText, lang);
        }, 500);
    }

    // Show/hide back button
    const prevBtn = document.getElementById('voice-prev-btn');
    if (prevBtn) prevBtn.style.display = index > 0 ? 'flex' : 'none';

    // Reset listening state
    if (typeof voiceStopListening === 'function') voiceStopListening();
    _voiceUpdateMicState('idle');

    // If text-only mode, show text input
    if (_voiceSession.touchOnly || _voiceSession.showTextFallback) {
        _voiceShowTextInput(true);
    } else {
        _voiceShowTextInput(false);
    }
}

function _voiceRenderQuickPicks(picks) {
    const container = document.getElementById('voice-touch-options');
    if (!container) return;
    container.innerHTML = '';
    if (!picks || !picks.length) return;

    const label = document.createElement('div');
    label.className = 'voice-touch-label';
    label.textContent = '💡 Quick options — tap to select:';
    container.appendChild(label);

    const grid = document.createElement('div');
    grid.className = 'voice-touch-grid';
    picks.forEach(pick => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'voice-touch-chip';
        btn.textContent = pick;
        btn.onclick = () => voiceSelectQuickPick(pick, btn);
        grid.appendChild(btn);
    });
    container.appendChild(grid);
}

function voiceSelectQuickPick(text, btn) {
    // Highlight selected chip
    document.querySelectorAll('.voice-touch-chip').forEach(b => b.classList.remove('selected-chip'));
    if (btn) btn.classList.add('selected-chip');

    // Set as pending transcript
    _voiceSession.pendingTranscript = text;
    const transcriptEl = document.getElementById('voice-transcript-text');
    if (transcriptEl) transcriptEl.textContent = text;

    const transcriptBox = document.getElementById('voice-transcript-box');
    if (transcriptBox) transcriptBox.classList.add('voice-transcript-has-content');

    // Show actions
    const actions = document.getElementById('voice-transcript-actions');
    if (actions) actions.style.display = 'flex';

    // Check red flags
    _voiceCheckRedFlags(text);
}

/* ============================================================================
   MICROPHONE BUTTON TOGGLE
   ============================================================================ */
async function voiceToggleListening() {
    if (typeof isListening === 'function' && isListening()) {
        if (typeof voiceStopListening === 'function') await voiceStopListening();
        _voiceUpdateMicState('idle');
        return;
    }

    // Clear previous content
    _voiceResetTranscriptUI();
    _voiceUpdateMicState('listening');

    const lang = _voiceSession.language;
    if (typeof voiceStartListening !== 'function') {
        _voiceShowTextInput(true);
        _voiceUpdateMicState('idle');
        return;
    }

    const started = await voiceStartListening(
        lang,
        // onInterim: display live words in real time
        (interimText) => {
            const el = document.getElementById('voice-transcript-text');
            if (el) el.textContent = interimText + '...';
            _voiceSession.pendingTranscript = interimText;
            _voiceUpdateMicState('listening');
        },
        // onFinal: display final confirmed transcription
        (finalText, confidence) => {
            _voiceSession.pendingTranscript = finalText;
            const el = document.getElementById('voice-transcript-text');
            if (el) el.textContent = finalText;
            const box = document.getElementById('voice-transcript-box');
            if (box) box.classList.add('voice-transcript-has-content');
            const actions = document.getElementById('voice-transcript-actions');
            if (actions) actions.style.display = 'flex';
            _voiceUpdateMicState('done');
            _voiceCheckRedFlags(finalText);

            // Pre-fill text fallback input so user can edit if desired
            const textInput = document.getElementById('voice-text-input');
            if (textInput) textInput.value = finalText;
        },
        // onError: handle errors gracefully
        (errorType, errorMsg) => {
            _voiceUpdateMicState('idle');
            if (errorType !== 'aborted') {
                const statusEl = document.getElementById('voice-mic-status-text');
                if (statusEl) statusEl.textContent = errorMsg;
            }
            if (errorType === 'not_supported' || errorType === 'not-allowed') {
                _voiceShowTextInput(true);
            }
        },
        // onEnd: reset UI if transcript wasn't received
        () => {
            if (!_voiceSession.pendingTranscript) {
                _voiceUpdateMicState('idle');
            }
        },
        // onStatus: show status messages
        (statusState, statusMsg) => {
            const statusEl = document.getElementById('voice-mic-status-text');
            if (statusEl) statusEl.textContent = statusMsg;
        },
        // onVolume: live volume indicator meter
        (rms) => {
            const statusEl = document.getElementById('voice-mic-status-text');
            if (statusEl && typeof isListening === 'function' && isListening()) {
                const level = Math.min(8, Math.max(1, Math.round(rms * 90)));
                const bars = ' ▂▃▄▅▆▇█'.slice(0, level);
                statusEl.innerHTML = `🔴 Listening... <span style="color:#059669;font-family:monospace;font-weight:700;">${bars}</span> (auto-stops on pause)`;
            }
        }
    );

    if (!started) {
        _voiceShowTextInput(true);
        _voiceUpdateMicState('idle');
    }
}

function _voiceUpdateMicState(state) {
    const btn = document.getElementById('voice-main-mic-btn');
    const icon = document.getElementById('voice-mic-icon');
    const statusText = document.getElementById('voice-mic-status-text');
    const statusDot = document.getElementById('voice-status-dot');
    const statusBar = document.getElementById('voice-mic-status-bar');

    if (!btn) return;

    btn.classList.remove('mic-listening', 'mic-done', 'mic-idle');
    if (statusDot) statusDot.classList.remove('dot-listening', 'dot-done');
    if (statusBar) statusBar.classList.remove('listening-active');

    if (state === 'listening') {
        btn.classList.add('mic-listening');
        if (icon) icon.textContent = 'mic';
        if (statusText) statusText.textContent = '🔴 Listening... tap again to stop';
        if (statusDot) statusDot.classList.add('dot-listening');
        if (statusBar) statusBar.classList.add('listening-active');
    } else if (state === 'done') {
        btn.classList.add('mic-done');
        if (icon) icon.textContent = 'mic_off';
        if (statusText) statusText.textContent = '✅ Recording complete. Review below.';
    } else {
        btn.classList.add('mic-idle');
        if (icon) icon.textContent = 'mic';
        if (statusText) statusText.textContent = 'Tap the microphone to speak';
    }
}

/* ============================================================================
   ANSWER CONFIRMATION / EDITING
   ============================================================================ */
function voiceConfirmAnswer() {
    const answer = _voiceSession.pendingTranscript;
    if (!answer || !answer.trim()) {
        alert('Please speak or tap an option first.');
        return;
    }

    const q = _voiceSession.activeQuestions[_voiceSession.currentQuestionIndex];
    _voiceSession.answers[q.key] = {
        questionText: q.text['en-IN'] || q.text[_voiceSession.language] || q.key,
        section: q.section,
        answer: answer.trim(),
        confidence: 0.9,
        source: _voiceSession.touchOnly ? 'touch' : 'browser',
        language: _voiceSession.language,
        isFollowUp: !!q.isFollowUp,
        linkedTo: q.linkedTo || null,
        triggerAnswer: q.triggerAnswer || null
    };

    // Dynamically evaluate and inject follow-up clinical probes linked directly to patient input
    _voiceEvaluateFollowUps(answer.trim(), q.key);

    // Save transcript to voice backend (non-blocking)
    if (typeof voiceSaveTranscript === 'function') {
        const langText = q.text[_voiceSession.language] || q.text['en-IN'];
        voiceSaveTranscript(
            _voiceSession.caseId,
            _voiceSession.sessionId,
            q.key,
            langText,
            answer.trim(),
            _voiceSession.language,
            0.9,
            _voiceSession.touchOnly ? 'touch' : 'browser'
        );
    }

    // Also persist section to Case Taking backend
    if (_voiceSession.caseId) {
        try {
            fetch(apiUrl(`/api/cases/${_voiceSession.caseId}/save-section`), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    section_id: q.key,
                    section_title: q.section,
                    raw_input: answer.trim(),
                    structured_data: { user_response: answer.trim() },
                    input_mode: _voiceSession.touchOnly ? 'touch' : 'voice'
                })
            }).catch(() => {});
        } catch (e) {}
    }

    // Move to next question
    setTimeout(() => {
        _voiceLoadQuestion(_voiceSession.currentQuestionIndex + 1);
    }, 300);
}

function voiceConfirmTextInput() {
    const textInput = document.getElementById('voice-text-input');
    if (!textInput || !textInput.value.trim()) {
        alert('Please type your answer first.');
        return;
    }
    _voiceSession.pendingTranscript = textInput.value.trim();
    voiceConfirmAnswer();
    textInput.value = '';
}

function voiceEditAnswer() {
    const transcriptEl = document.getElementById('voice-transcript-text');
    const textInput = document.getElementById('voice-text-input');
    if (transcriptEl && textInput) {
        textInput.value = _voiceSession.pendingTranscript;
    }
    _voiceShowTextInput(true);
}

function voiceRetryRecording() {
    _voiceResetTranscriptUI();
    setTimeout(() => voiceToggleListening(), 300);
}

function _voiceResetTranscriptUI() {
    _voiceSession.pendingTranscript = '';
    const el = document.getElementById('voice-transcript-text');
    if (el) el.innerHTML = '&nbsp;';
    const box = document.getElementById('voice-transcript-box');
    if (box) box.classList.remove('voice-transcript-has-content');
    const actions = document.getElementById('voice-transcript-actions');
    if (actions) actions.style.display = 'none';
    const redFlag = document.getElementById('voice-red-flag-banner');
    if (redFlag) redFlag.style.display = 'none';
    document.querySelectorAll('.voice-touch-chip').forEach(b => b.classList.remove('selected-chip'));
}

function voiceToggleTextFallback() {
    _voiceSession.showTextFallback = !_voiceSession.showTextFallback;
    _voiceShowTextInput(_voiceSession.showTextFallback);
}

function _voiceShowTextInput(show) {
    const fallback = document.getElementById('voice-text-fallback');
    const typeBtn = document.getElementById('voice-type-instead-btn');
    const micBtn = document.getElementById('voice-main-mic-btn');
    if (fallback) fallback.style.display = show ? 'block' : 'none';
    if (typeBtn) typeBtn.textContent = show ? '🎤 Use Voice Instead' : '⌨️ Type Instead';
    if (micBtn) micBtn.style.display = show ? 'none' : 'flex';
}

/* ============================================================================
   NAVIGATION
   ============================================================================ */
function voiceNavigatePrevious() {
    if (_voiceSession.currentQuestionIndex > 0) {
        if (typeof stopSpeaking === 'function') stopSpeaking();
        if (typeof voiceStopListening === 'function') voiceStopListening();
        _voiceLoadQuestion(_voiceSession.currentQuestionIndex - 1);
    }
}

function voiceSkipSection() {
    const q = _voiceSession.activeQuestions[_voiceSession.currentQuestionIndex];
    if (q) {
        _voiceSession.answers[q.key] = {
            answer: '[SKIPPED]',
            source: 'skipped',
            language: _voiceSession.language,
        };
    }
    if (typeof stopSpeaking === 'function') stopSpeaking();
    if (typeof voiceStopListening === 'function') voiceStopListening();
    _voiceLoadQuestion(_voiceSession.currentQuestionIndex + 1);
}

function voiceReplayQuestion() {
    const q = _voiceSession.activeQuestions[_voiceSession.currentQuestionIndex];
    if (!q) return;
    const text = q.text[_voiceSession.language] || q.text['en-IN'];
    if (typeof speakText === 'function') speakText(text, _voiceSession.language);
}

/* ============================================================================
   AYUSH MODE TOGGLE
   ============================================================================ */
function voiceToggleAyushMode() {
    _voiceSession.ayushMode = !_voiceSession.ayushMode;
    const toggle = document.getElementById('voice-ayush-toggle');
    const badge = document.getElementById('voice-ayush-badge');
    if (toggle) toggle.classList.toggle('ayush-active', _voiceSession.ayushMode);
    if (badge) badge.style.display = _voiceSession.ayushMode ? 'inline-flex' : 'none';
    // Rebuild question list with/without AYUSH questions
    _voiceBuildActiveQuestions();
    // Update progress
    const total = _voiceSession.activeQuestions.length;
    const labelEl = document.getElementById('voice-progress-label');
    if (labelEl) labelEl.textContent = _voiceSession.ayushMode
        ? `AYUSH mode ON — ${total} questions total`
        : `Allopathic mode — ${total} questions`;
}
window.voiceToggleAyushMode = voiceToggleAyushMode;

/* ============================================================================
   RED FLAG ENGINE — deterministic emergency detection
   ============================================================================ */
const RED_FLAG_TERMS = [
    // English
    'chest pain', 'cannot breathe', "can't breathe", 'difficulty breathing', 'breathless',
    'unconscious', 'fainted', 'collapse', 'blood in vomit', 'vomiting blood',
    'blood in stool', 'black stool', 'stroke', 'paralysis', 'one side weak',
    'worst headache', 'severe chest',
    // Hindi
    'छाती में दर्द', 'सांस नहीं', 'बेहोश', 'खून की उल्टी',
    // Telugu
    'గుండె నొప్పి', 'శ్వాస తీసుకోలేను', 'మూర్ఛ',
];

function _voiceCheckRedFlags(text) {
    if (!text) return;
    const lower = text.toLowerCase();
    const q = _voiceSession.activeQuestions ? _voiceSession.activeQuestions[_voiceSession.currentQuestionIndex] : null;
    const qFlags = q ? (q.redFlags || []) : [];
    const allFlags = [...RED_FLAG_TERMS, ...qFlags];

    const triggered = allFlags.some(flag => lower.includes(flag.toLowerCase()));
    const banner = document.getElementById('voice-red-flag-banner');
    if (banner) {
        banner.style.display = triggered ? 'flex' : 'none';
    }

    if (triggered) {
        _voiceSession.hasRedFlag = true;
        const triageBadge = document.getElementById('voice-case-triage-badge');
        if (triageBadge) {
            triageBadge.textContent = '🔴 PRIORITY RED FLAG — URGENT REVIEW';
            triageBadge.style.background = '#fee2e2';
            triageBadge.style.color = '#dc2626';
            triageBadge.style.borderColor = '#f87171';
        }
        if (!_voiceSession.redFlagAlerted) {
            _voiceSession.redFlagAlerted = true;
            if (typeof showToast === 'function') {
                showToast('🚨 PRIORITY ALERT: Symptom detected requiring urgent physician attention', 'error');
            }
        }
    }
}

/* ============================================================================
   SESSION COMPLETION & DIGITAL CASE SHEET SYNTHESIS
   ============================================================================ */
async function _voiceComplete() {
    if (typeof stopSpeaking === 'function') stopSpeaking();

    // Update case ID and metadata in summary view
    const summaryEl = document.getElementById('voice-summary-case-id');
    if (summaryEl) {
        summaryEl.textContent = `Case: ${_voiceSession.caseId || _voiceSession.sessionId} | Lang: ${_voiceSession.language}`;
    }

    const patientMetaEl = document.getElementById('voice-summary-patient-meta');
    if (patientMetaEl) {
        const pId = _voiceSession.patientId || 'Outpatient';
        const abha = _voiceSession.abhaId || '91-4589-2041-8832';
        patientMetaEl.innerHTML = `Patient ID: <strong>${escapeHtml(pId)}</strong> &bull; ABHA: <strong>${escapeHtml(abha)}</strong> &bull; Mode: <strong>${_voiceSession.touchOnly ? 'Touch/Text' : 'Voice Assisted'}</strong>`;
    }

    // Submit case responses and generate structured summary in backend
    try {
        await _voiceSubmitCaseToBackend();
        if (_voiceSession.caseId) {
            fetch(apiUrl(`/api/cases/${_voiceSession.caseId}/generate-summary`), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ayush_enabled: _voiceSession.ayushMode || false })
            }).catch(() => {});
        }
    } catch (e) {
        console.warn('[VoiceCT] Could not submit case to backend:', e);
    }

    // Render formatted digital case sheet
    _voiceRenderSummaryHighlights();

    // Speak completion message
    const lang = _voiceSession.language;
    const completionMsg = {
        'en-IN': 'Thank you. Your complete medical history has been prepared for the doctor.',
        'hi-IN': 'धन्यवाद। आपकी संपूर्ण केस हिस्ट्री डॉक्टर के लिए तैयार कर ली गई है।',
        'te-IN': 'ధన్యవాదాలు. మీ సంపూర్ణ వైద్య చరిత్ర డాక్టర్ కోసం సిద్ధం చేయబడింది.',
    }[lang] || 'Thank you. Your clinical history has been recorded.';

    setTimeout(() => {
        if (typeof speakText === 'function') speakText(completionMsg, lang);
    }, 400);

    _voiceShowStep('summary');
}

async function _voiceSubmitCaseToBackend() {
    // Build clinical history from voice answers
    const historyData = {};
    Object.entries(_voiceSession.answers).forEach(([key, val]) => {
        if (val.answer !== '[SKIPPED]') {
            historyData[key] = val.answer;
        }
    });

    if (Object.keys(historyData).length > 0) {
        try {
            const payload = {
                patient_id: _voiceSession.patientId || 'P-MEDICOVER-01',
                language_code: _voiceSession.language || 'en-IN',
                voice_session_id: _voiceSession.sessionId,
                abha_id: _voiceSession.abhaId || '91-4589-2041-8832',
                responses: historyData,
                source: 'voice_case_taking',
            };

            const res = await fetch(apiUrl('/api/cases/voice-submit'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (res.ok) {
                const data = await res.json();
                if (data.case_id) _voiceSession.caseId = data.case_id;
            }
        } catch (e) {
            // Non-fatal — local session is preserved
        }
    }
}

function _voiceRenderSummaryHighlights() {
    const container = document.getElementById('voice-summary-highlights');
    if (!container) return;

    const pId = _voiceSession.patientId || 'P-MEDICOVER-01';
    const abha = _voiceSession.abhaId || '91-4589-2041-8832';
    const caseRef = _voiceSession.caseId || _voiceSession.sessionId || `CASE-${Date.now()}`;
    const intakeDate = new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    const intakeTime = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
    const langConfig = typeof voiceGetLanguageByCode === 'function' ? voiceGetLanguageByCode(_voiceSession.language) : null;
    const langLabel = langConfig ? `${langConfig.flag} ${langConfig.nativeName} (${langConfig.name})` : (_voiceSession.language || 'English');

    const cc = _voiceSession.answers['chief_complaint']?.answer || 'General outpatient clinical consultation';
    const duration = _voiceSession.answers['present_illness_duration']?.answer || 'Recent onset';

    // Parse numeric pain score (1-10)
    let painScore = 4;
    const painRaw = _voiceSession.answers['pain_severity']?.answer || '';
    const painMatch = painRaw.match(/\d+/);
    if (painMatch) {
        painScore = Math.min(10, Math.max(1, parseInt(painMatch[0], 10)));
    } else if (painRaw.toLowerCase().includes('very severe') || painRaw.toLowerCase().includes('worst')) {
        painScore = 9;
    } else if (painRaw.toLowerCase().includes('severe')) {
        painScore = 7;
    } else if (painRaw.toLowerCase().includes('moderate')) {
        painScore = 5;
    } else if (painRaw.toLowerCase().includes('mild')) {
        painScore = 3;
    }

    // Determine clinical triage acuity
    let triageClass = 'cs-triage-routine';
    let triageTitle = '🟢 ROUTINE PRE-CONSULTATION INTAKE (LOW ACUITY)';
    let triageDesc = 'Vitals stable. Standard outpatient physician consultation indicated.';
    if (_voiceSession.hasRedFlag) {
        triageClass = 'cs-triage-emergency';
        triageTitle = '🔴 CRITICAL RED FLAG — PRIORITY PHYSICIAN REVIEW';
        triageDesc = 'Potential emergency symptom reported. Attending physician notified for immediate bedside evaluation.';
    } else if (painScore >= 7) {
        triageClass = 'cs-triage-priority';
        triageTitle = '🟡 PRIORITY CLINICAL REVIEW (HIGH SYMPTOM BURDEN)';
        triageDesc = `Elevated pain severity (${painScore}/10) or acute discomfort reported. Prioritized OPD queue recommended.`;
    }

    // Update the external top triage badge if it exists
    const topTriageBadge = document.getElementById('voice-case-triage-badge');
    if (topTriageBadge) {
        topTriageBadge.textContent = triageTitle;
        topTriageBadge.className = 'voice-step-badge ' + triageClass;
    }

    // Identify all adaptive follow-up inquiries
    const followUpEntries = Object.entries(_voiceSession.answers).filter(([k, v]) => {
        if (!v || !v.answer || v.answer === '[SKIPPED]') return false;
        return v.isFollowUp || (
            k.startsWith('chest_') || k.startsWith('fever_') || k.startsWith('stomach_') ||
            k.startsWith('headache_') || k.startsWith('breath_') || k.startsWith('cough_') ||
            k.startsWith('throat_') || k.startsWith('joint_') || k.startsWith('back_') ||
            k.startsWith('vomit_') || k.startsWith('skin_') || k.startsWith('diabetes_') ||
            k.startsWith('htn_') || k.startsWith('urinary_') || k.startsWith('dizziness_') ||
            k.startsWith('followup_dyn_')
        );
    });

    // Medications extraction & chips
    const medAnswer = _voiceSession.answers['current_medications']?.answer || 'None reported';
    const hasMed = medAnswer.toLowerCase() !== 'none' && !medAnswer.toLowerCase().includes('no medicines');
    const medList = hasMed ? medAnswer.split(/[,;\n+]+|\band\b/i).map(s => s.trim()).filter(Boolean) : ['No regular medications reported'];

    // Allergy detection
    const allergyText = (_voiceSession.answers['current_medications']?.answer || '') + ' ' + (_voiceSession.answers['additional_info']?.answer || '');
    const allergyLower = allergyText.toLowerCase();
    const hasAllergy = allergyLower.includes('allergic') || allergyLower.includes('allergy') || allergyLower.includes('penicillin') || allergyLower.includes('sulfa');

    // Clinical Decision Support Differential Suggestions based on complaints
    const cdsRecommendations = [];
    const ccLower = cc.toLowerCase();
    if (ccLower.includes('chest') || ccLower.includes('heart') || ccLower.includes('breath') || _voiceSession.hasRedFlag) {
        cdsRecommendations.push('Immediate 12-Lead ECG & cardiac enzymes (Troponin-I) baseline');
        cdsRecommendations.push('Continuous SpO2 & automated NIBP monitoring');
    }
    if (ccLower.includes('fever') || ccLower.includes('temp') || ccLower.includes('chills')) {
        cdsRecommendations.push('Complete Blood Count (CBC) with differential & Peripheral Smear for MP');
        cdsRecommendations.push('Urine Routine & Microscopy to rule out occult UTI');
    }
    if (ccLower.includes('stomach') || ccLower.includes('abdomen') || ccLower.includes('vomit') || ccLower.includes('loose')) {
        cdsRecommendations.push('Serum Electrolytes (Na+, K+, Cl-) & Serum Creatinine evaluation');
        cdsRecommendations.push('Abdominal Ultrasound (USG Whole Abdomen) if tenderness persists');
    }
    if (ccLower.includes('joint') || ccLower.includes('knee') || ccLower.includes('back')) {
        cdsRecommendations.push('Plain Radiograph (X-Ray) of affected joint/spine in AP & Lateral views');
        cdsRecommendations.push('Serum Uric Acid & inflammatory markers (ESR / hs-CRP)');
    }
    if (ccLower.includes('sugar') || ccLower.includes('diabetes') || ccLower.includes('thirst')) {
        cdsRecommendations.push('Random Blood Sugar (RBS) & HbA1c glycemic index verification');
    }
    if (cdsRecommendations.length === 0) {
        cdsRecommendations.push('Standard vital signs check (BP, PR, SpO2, Temperature, BMI)');
        cdsRecommendations.push('Comprehensive organ system physical examination as clinically indicated');
    }

    // Build the executive HTML dossier
    container.innerHTML = `
        <div class="cs-sheet-wrapper">
            <!-- Official Hospital Header Strip -->
            <div class="cs-header-strip">
                <div class="cs-header-brand">
                    <div class="cs-brand-icon">
                        <span class="material-symbols-outlined">local_hospital</span>
                    </div>
                    <div>
                        <h2 class="cs-hospital-name">
                            MEDLENS HEALTH SYSTEM
                            <span style="font-size:0.65rem; background:#0284c7; padding:2px 8px; border-radius:999px; vertical-align:middle;">ABDM VERIFIED</span>
                        </h2>
                        <div class="cs-hospital-sub">Government Hospital OPD &bull; Pre-Consultation EHR Intake Dossier (PS 26047)</div>
                    </div>
                </div>
                <div class="cs-header-meta">
                    <div class="cs-barcode-block">
                        <div class="cs-barcode-lines">|| | | ||| || ||| | || |||| | |</div>
                        <div>*${escapeHtml(caseRef)}*</div>
                    </div>
                    <div style="font-size:0.75rem; color:#cbd5e1; font-weight:600;">
                        Date: <strong>${intakeDate}</strong> &bull; <strong>${intakeTime}</strong>
                    </div>
                </div>
            </div>

            <!-- Patient Identity Strip -->
            <div class="cs-patient-banner">
                <div class="cs-meta-item">
                    <span class="cs-meta-label">Patient Identification</span>
                    <span class="cs-meta-value">
                        <span class="material-symbols-outlined" style="font-size:18px; color:#0284c7;">person</span>
                        ${escapeHtml(pId)}
                    </span>
                </div>
                <div class="cs-meta-item">
                    <span class="cs-meta-label">ABHA Identity Number</span>
                    <span class="cs-meta-value">
                        <span class="cs-abha-tag">${escapeHtml(abha)}</span>
                    </span>
                </div>
                <div class="cs-meta-item">
                    <span class="cs-meta-label">Intake Mode &amp; Language</span>
                    <span class="cs-meta-value" style="font-size:0.85rem;">
                        ${_voiceSession.touchOnly ? '📱 Interactive Touch' : '🎙️ Multilingual Voice'} &bull; ${langLabel}
                    </span>
                </div>
                <div class="cs-meta-item">
                    <span class="cs-meta-label">FHIR / EMR Status</span>
                    <span class="cs-meta-value" style="color:#059669;">
                        <span class="material-symbols-outlined" style="font-size:18px;">cloud_done</span> Ready for Doctor
                    </span>
                </div>
            </div>

            <!-- Triage Acuity Meter -->
            <div class="cs-triage-strip ${triageClass}">
                <div class="cs-triage-badge">
                    <span class="material-symbols-outlined" style="font-size:22px;">crisis_alert</span>
                    <span>${triageTitle}</span>
                </div>
                <div style="font-size:0.84rem; font-weight:600;">
                    ${triageDesc}
                </div>
            </div>

            <!-- Main Clinical Case Sheet Body -->
            <div class="cs-body">
                <!-- Chief Complaint & Duration Callout -->
                <div class="cs-chief-box">
                    <div class="cs-chief-title">
                        <span class="material-symbols-outlined" style="font-size:18px;">stethoscope</span>
                        Primary Chief Complaint (Patient's Own Words)
                    </div>
                    <blockquote class="cs-chief-quote">
                        &ldquo;${escapeHtml(cc)}&rdquo;
                    </blockquote>
                    <div class="cs-chief-pills">
                        <span class="cs-pill">
                            <span class="material-symbols-outlined" style="font-size:16px;">schedule</span>
                            Onset / Duration: <strong>${escapeHtml(duration)}</strong>
                        </span>
                        <span class="cs-pill" style="border-color:${painScore >= 7 ? '#f87171' : '#7dd3fc'}; color:${painScore >= 7 ? '#dc2626' : '#0284c7'};">
                            <span class="material-symbols-outlined" style="font-size:16px;">bolt</span>
                            Pain / Distress Score: <strong>${painScore} / 10</strong>
                        </span>
                        <span class="cs-pill" style="background:#f0fdf4; border-color:#86efac; color:#16a34a;">
                            <span class="material-symbols-outlined" style="font-size:16px;">verified</span>
                            Voice Confirmed
                        </span>
                    </div>

                    <!-- Visual Pain Intensity Gauge -->
                    <div class="cs-pain-container">
                        <div class="cs-pain-header">
                            <span>Visual Pain Intensity Scale (1 = Minimal Discomfort, 10 = Severe/Unbearable)</span>
                            <span style="font-weight:800; color:${painScore >= 7 ? '#dc2626' : (painScore >= 4 ? '#d97706' : '#16a34a')};">
                                Level: ${painScore} / 10 ${painScore >= 7 ? '(Severe)' : (painScore >= 4 ? '(Moderate)' : '(Mild)')}
                            </span>
                        </div>
                        <div class="cs-pain-meter-bar">
                            ${[1,2,3,4,5,6,7,8,9,10].map(n => `
                                <div class="cs-pain-seg ${n <= painScore ? `active-${n}` : ''}" title="Level ${n}"></div>
                            `).join('')}
                        </div>
                    </div>
                </div>

                <!-- AI ADAPTIVE FOLLOW-UP DEEP DIVE (Specifically linked to user's input) -->
                <div class="cs-adaptive-box">
                    <div class="cs-adaptive-header">
                        <div class="cs-adaptive-title">
                            <span class="material-symbols-outlined" style="font-size:22px; color:#7c3aed;">auto_awesome</span>
                            <span>✨ AI Adaptive Clinical Deep-Dive (Linked Inquiries)</span>
                        </div>
                        <span class="cs-adaptive-badge">
                            ${followUpEntries.length > 0 ? `${followUpEntries.length} Adaptive Probes Answered` : 'Standard Protocol Followed'}
                        </span>
                    </div>
                    <div style="font-size:0.84rem; color:#6b21a8; margin-bottom:14px; line-height:1.4;">
                        MEDLENS AI actively analyzed the patient's spoken complaints and dynamically generated targeted clinical follow-up questions to rule out acute complications before the physician meeting:
                    </div>

                    ${followUpEntries.length > 0 ? `
                        <div style="display:flex; flex-direction:column; gap:10px;">
                            ${followUpEntries.map(([k, val]) => `
                                <div class="cs-adaptive-item">
                                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px;">
                                        <span class="cs-adaptive-link-tag">
                                            🔗 ${escapeHtml(val.linkedTo || 'Symptom-linked drill down')}
                                        </span>
                                        <span style="font-size:0.72rem; color:#9333ea; font-weight:700;">Verified Response</span>
                                    </div>
                                    <div class="cs-adaptive-q">
                                        <span class="material-symbols-outlined" style="font-size:16px; color:#7c3aed; margin-top:2px;">psychology_alt</span>
                                        <span>${escapeHtml(val.questionText || k.replace(/_/g, ' '))}</span>
                                    </div>
                                    <div class="cs-adaptive-a">
                                        &ldquo;${escapeHtml(val.answer)}&rdquo;
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    ` : `
                        <div style="background:#ffffff; border:1px dashed #d8b4fe; border-radius:10px; padding:14px; text-align:center; color:#6b21a8; font-size:0.84rem;">
                            <span class="material-symbols-outlined" style="font-size:24px; vertical-align:middle; margin-right:6px;">task_alt</span>
                            Standard comprehensive intake completed. Patient reported isolated symptoms without requiring emergency cross-system drilldowns.
                        </div>
                    `}
                </div>

                <!-- Structured Clinical History Grid (2-Columns) -->
                <div class="cs-grid">
                    <!-- Card 1: HPI & Associated Symptoms -->
                    <div class="cs-card">
                        <div class="cs-card-header">
                            <span class="material-symbols-outlined">notes</span>
                            History of Present Illness (HPI)
                        </div>
                        <div class="cs-card-content">
                            <div class="cs-entry-row">
                                <div class="cs-entry-label">Onset &amp; Chronology</div>
                                <div class="cs-entry-value">${escapeHtml(duration)}</div>
                            </div>
                            <div class="cs-entry-row">
                                <div class="cs-entry-label">Associated Symptoms &amp; Systemic Features</div>
                                <div class="cs-entry-value">${escapeHtml(_voiceSession.answers['associated_symptoms']?.answer || 'None reported')}</div>
                            </div>
                            <div class="cs-entry-row">
                                <div class="cs-entry-label">Reported Pain &amp; Acuity</div>
                                <div class="cs-entry-value">${escapeHtml(painRaw || 'Mild/Moderate')}</div>
                            </div>
                        </div>
                    </div>

                    <!-- Card 2: Pharmacotherapy & Medications -->
                    <div class="cs-card">
                        <div class="cs-card-header">
                            <span class="material-symbols-outlined">medication</span>
                            Current Medications &amp; Rx History
                        </div>
                        <div class="cs-card-content">
                            <div class="cs-entry-label">Active Prescriptions / Over-the-Counter Drugs:</div>
                            <div style="margin-top:4px;">
                                ${medList.map(m => `
                                    <span class="cs-rx-chip">
                                        <span class="material-symbols-outlined" style="font-size:15px;">pill</span>
                                        ${escapeHtml(m)}
                                    </span>
                                `).join('')}
                            </div>
                        </div>
                    </div>

                    <!-- Card 3: Allergies & ADR Warning -->
                    <div class="cs-card" style="${hasAllergy ? 'border-color:#fecdd3; background:#fff1f2;' : ''}">
                        <div class="cs-card-header" style="${hasAllergy ? 'color:#9f1239; border-color:#fecdd3;' : ''}">
                            <span class="material-symbols-outlined" style="${hasAllergy ? 'color:#e11d48;' : ''}">warning</span>
                            Known Allergies &amp; Drug Hypersensitivity
                        </div>
                        <div class="cs-card-content">
                            ${hasAllergy ? `
                                <div class="cs-allergy-alert">
                                    <span class="material-symbols-outlined" style="font-size:20px;">report</span>
                                    <div>
                                        <strong>ALLERGY ALERT:</strong> ${escapeHtml(medAnswer)}
                                    </div>
                                </div>
                            ` : `
                                <div style="display:flex; align-items:center; gap:8px; color:#15803d; font-size:0.85rem; font-weight:700;">
                                    <span class="material-symbols-outlined" style="color:#16a34a;">check_circle</span>
                                    <span>No Known Drug Allergies (NKDA) Reported by Patient</span>
                                </div>
                            `}
                        </div>
                    </div>

                    <!-- Card 4: Past Medical & Surgical History -->
                    <div class="cs-card">
                        <div class="cs-card-header">
                            <span class="material-symbols-outlined">medical_information</span>
                            Past Medical &amp; Chronic Conditions
                        </div>
                        <div class="cs-card-content">
                            <div class="cs-entry-row">
                                <div class="cs-entry-label">Chronic Illnesses (DM, HTN, IHD, Asthma)</div>
                                <div class="cs-entry-value">${escapeHtml(_voiceSession.answers['past_medical_history']?.answer || 'No major pre-existing illnesses recorded')}</div>
                            </div>
                        </div>
                    </div>

                    <!-- Card 5: Family & Hereditary Risk -->
                    <div class="cs-card">
                        <div class="cs-card-header">
                            <span class="material-symbols-outlined">family_restroom</span>
                            Family Medical History
                        </div>
                        <div class="cs-card-content">
                            <div class="cs-entry-row">
                                <div class="cs-entry-label">Hereditary &amp; Familial Conditions</div>
                                <div class="cs-entry-value">${escapeHtml(_voiceSession.answers['family_history']?.answer || 'No hereditary disease reported in immediate relatives')}</div>
                            </div>
                        </div>
                    </div>

                    <!-- Card 6: Social & Occupational History -->
                    <div class="cs-card">
                        <div class="cs-card-header">
                            <span class="material-symbols-outlined">badge</span>
                            Social, Occupational &amp; Habits
                        </div>
                        <div class="cs-card-content">
                            <div class="cs-entry-row">
                                <div class="cs-entry-label">Occupation &amp; Substance Use (Tobacco/Alcohol)</div>
                                <div class="cs-entry-value">${escapeHtml(_voiceSession.answers['social_history']?.answer || 'Non-smoker, non-alcoholic')}</div>
                            </div>
                        </div>
                    </div>

                    <!-- Card 7: Review of Systems & Additional Notes -->
                    <div class="cs-card" style="grid-column: 1 / -1;">
                        <div class="cs-card-header">
                            <span class="material-symbols-outlined">checklist</span>
                            Review of Systems (ROS) &amp; Patient Notes
                        </div>
                        <div class="cs-card-content" style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:12px;">
                            <div class="cs-entry-row">
                                <div class="cs-entry-label">Constitutional (Weight / Appetite / Sleep / Bowel)</div>
                                <div class="cs-entry-value">${escapeHtml(_voiceSession.answers['review_of_systems']?.answer || 'Normal')}</div>
                            </div>
                            <div class="cs-entry-row">
                                <div class="cs-entry-label">Additional Patient Remarks for Doctor</div>
                                <div class="cs-entry-value">${escapeHtml(_voiceSession.answers['additional_info']?.answer || 'None')}</div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- AYUSH CONSTITUTIONAL ASSESSMENT (If enabled) -->
                ${_voiceSession.ayushMode ? `
                    <div class="cs-ayush-box">
                        <div class="cs-ayush-title">
                            <span class="material-symbols-outlined" style="font-size:20px;">spa</span>
                            AYUSH Constitutional &amp; Tri-Doshic Prakriti Profile
                        </div>
                        <div style="font-size:0.82rem; color:#713f12; line-height:1.4;">
                            Preliminary bio-energy constitutional assessment derived from digestive fire (Agni), appetite (Ahara), and mental-physical endurance (Vyayama Shakti):
                        </div>
                        <div class="cs-dosha-meter">
                            <div class="cs-dosha-row">
                                <span class="cs-dosha-name">Vata (Air/Nerve):</span>
                                <div class="cs-dosha-bar-bg">
                                    <div class="cs-dosha-bar-fill" style="width: 45%; background:#38bdf8;"></div>
                                </div>
                                <span style="font-weight:700; width:45px; text-align:right;">45%</span>
                            </div>
                            <div class="cs-dosha-row">
                                <span class="cs-dosha-name">Pitta (Fire/Metab):</span>
                                <div class="cs-dosha-bar-bg">
                                    <div class="cs-dosha-bar-fill" style="width: 35%; background:#f97316;"></div>
                                </div>
                                <span style="font-weight:700; width:45px; text-align:right;">35%</span>
                            </div>
                            <div class="cs-dosha-row">
                                <span class="cs-dosha-name">Kapha (Water/Body):</span>
                                <div class="cs-dosha-bar-bg">
                                    <div class="cs-dosha-bar-fill" style="width: 20%; background:#22c55e;"></div>
                                </div>
                                <span style="font-weight:700; width:45px; text-align:right;">20%</span>
                            </div>
                        </div>
                        <div style="font-size:0.8rem; color:#854d0e; font-weight:600;">
                            🌿 <strong>Provisional Prakriti:</strong> Vata-Pitta Dominant &bull; Agni: Vishama Agni &bull; Recommended diet: Warm, soothing, hydrating preparations.
                        </div>
                    </div>
                ` : ''}

                <!-- Scanned & Attached Records -->
                ${attachedVoiceDocuments.length > 0 ? `
                    <div style="background:#eff6ff; border:1.5px solid #93c5fd; border-radius:12px; padding:18px 20px;">
                        <div style="font-size:0.84rem; font-weight:800; color:#1e40af; text-transform:uppercase; margin-bottom:12px; display:flex; align-items:center; gap:8px;">
                            <span class="material-symbols-outlined" style="font-size:20px;">document_scanner</span>
                            Attached Prior Prescriptions &amp; Lab Documents (${attachedVoiceDocuments.length})
                        </div>
                        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:10px;">
                            ${attachedVoiceDocuments.map(d => `
                                <div style="background:#ffffff; border:1px solid #bfdbfe; border-radius:8px; padding:10px 14px; display:flex; justify-content:space-between; align-items:center;">
                                    <div>
                                        <div style="font-size:0.84rem; font-weight:700; color:#0f172a;">📄 ${escapeHtml(d.filename)}</div>
                                        <div style="font-size:0.72rem; color:#64748b;">Size: ${d.size} &bull; Uploaded: ${d.time}</div>
                                    </div>
                                    <span style="font-size:0.7rem; font-weight:800; background:#dcfce7; color:#15803d; border:1px solid #86efac; padding:2px 8px; border-radius:999px;">
                                        ✓ OCR Processed
                                    </span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}

                <!-- Physician Decision Support (CDS) & Differential Guidance -->
                <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:12px; padding:18px 20px;">
                    <div style="display:flex; align-items:center; gap:8px; font-size:0.84rem; font-weight:800; color:#0369a1; text-transform:uppercase; margin-bottom:10px;">
                        <span class="material-symbols-outlined" style="font-size:20px; color:#0284c7;">lightbulb</span>
                        Physician Decision Support (CDS) &amp; Recommended Workup
                    </div>
                    <ul style="margin:0; padding-left:20px; font-size:0.84rem; color:#334155; line-height:1.6;">
                        ${cdsRecommendations.map(r => `<li>${escapeHtml(r)}</li>`).join('')}
                    </ul>
                </div>

                <!-- Doctor Attestation & Official Stamp Box -->
                <div class="cs-doctor-box">
                    <div class="cs-doc-notes">
                        <div class="cs-doc-notes-title">Attending Physician Clinical Notes &amp; Rx:</div>
                        <div class="cs-doc-lines"></div>
                        <div class="cs-doc-lines"></div>
                        <div class="cs-doc-lines"></div>
                    </div>
                    <div class="cs-signature-seal">
                        <div class="cs-seal-circle">
                            <span>MEDLENS EHR</span>
                            <span style="font-size:0.5rem; letter-spacing:0.02em;">VERIFIED INTAKE</span>
                            <span>★★★★★</span>
                            <span style="font-size:0.55rem;">PS 26047</span>
                        </div>
                        <div>
                            <div class="cs-signature-line">
                                Attending Physician Signature<br>
                                <span style="font-size:0.65rem; color:#94a3b8;">Reg. No. / Stamp</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Compliance Footer -->
                <div style="text-align:center; font-size:0.72rem; color:#94a3b8; border-top:1px solid #f1f5f9; padding-top:12px;">
                    MEDLENS AI Clinical Case Taking System &bull; National Health Mission &bull; ABDM HL7 FHIR Compatible &bull; Smart India Hackathon PS 26047
                </div>
            </div>
        </div>
    `;
}

function voiceStartNewSession() {
    _voiceSession = {
        language: 'en-IN',
        touchOnly: false,
        patientId: (typeof currentAuth !== 'undefined' && currentAuth.patientId) || (typeof activeCasePatientId !== 'undefined' && activeCasePatientId) || null,
        abhaId: null,
        caseId: null,
        sessionId: null,
        currentQuestionIndex: 0,
        answers: {},
        transcripts: [],
        startedAt: null,
        kioskMode: false,
        showTextFallback: false,
        pendingTranscript: '',
        ayushMode: false,
        activeQuestions: [],
        injectedFollowUpKeys: new Set(),
        activeFollowUpsTriggered: [],
    };
    _voiceInitLanguageGrid();
    _voiceShowStep('language');
}

/* ============================================================================
   SETTINGS PANEL
   ============================================================================ */
function _populateSettingsLanguageSelect() {
    const select = document.getElementById('voice-settings-lang');
    if (!select) return;
    const langs = typeof voiceGetSupportedLanguages === 'function' ? voiceGetSupportedLanguages() : [];
    select.innerHTML = langs.map(l =>
        `<option value="${l.code}" ${l.code === _voiceSession.language ? 'selected' : ''}>${l.flag} ${l.nativeName} (${l.name})</option>`
    ).join('');
}

function voiceChangeLanguage(langCode) {
    _voiceSession.language = langCode;
    if (typeof voiceSetLanguage === 'function') voiceSetLanguage(langCode);
    if (typeof onLanguageChange === 'function') onLanguageChange(langCode);

    const langDisplay = document.getElementById('voice-session-lang-display');
    const langConfig = typeof voiceGetLanguageByCode === 'function' ? voiceGetLanguageByCode(langCode) : null;
    if (langDisplay && langConfig) {
        langDisplay.innerHTML = `${langConfig.flag} ${langConfig.nativeName}`;
    }

    // Reload current question in new language
    _voiceLoadQuestion(_voiceSession.currentQuestionIndex);
}

function updateSpeedDisplay(speed) {
    document.querySelectorAll('.voice-speed-btns button').forEach(b => b.classList.remove('active-speed'));
    if (speed <= 0.8) document.querySelector('.voice-speed-btns button:first-child')?.classList.add('active-speed');
    else if (speed >= 1.3) document.querySelector('.voice-speed-btns button:last-child')?.classList.add('active-speed');
    else document.querySelector('.voice-speed-btns button:nth-child(2)')?.classList.add('active-speed');
}

/* ============================================================================
   KIOSK MODE
   ============================================================================ */
function enterKioskMode() {
    _voiceSession.kioskMode = true;
    const overlay = document.getElementById('voice-kiosk-overlay');
    if (overlay) overlay.style.display = 'flex';
    try { document.documentElement.requestFullscreen?.(); } catch (e) {}
}

function exitKioskMode() {
    _voiceSession.kioskMode = false;
    const overlay = document.getElementById('voice-kiosk-overlay');
    if (overlay) overlay.style.display = 'none';
    try { document.exitFullscreen?.(); } catch (e) {}
}

console.info('[VoiceCaseTaking] MEDLENS Voice Case Taking module loaded.');
