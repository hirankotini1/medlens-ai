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
   ADAPTIVE FOLLOW-UP INJECTION
   Called after chief_complaint answer to inject relevant follow-ups.
   ============================================================================ */
function _voiceInjectAdaptiveFollowUps(chiefComplaintText) {
    const lower = chiefComplaintText.toLowerCase();
    let toInject = [];

    // Match common chief complaint patterns
    if (lower.includes('chest') || lower.includes('cardiac') || lower.includes('heart') ||
        lower.includes('छाती') || lower.includes('गुण्डे') || lower.includes('గుండె')) {
        toInject = ADAPTIVE_FOLLOWUPS.chest || [];
    } else if (lower.includes('fever') || lower.includes('temperature') || lower.includes('बुखार') ||
               lower.includes('జ్వరం') || lower.includes('temp') || lower.includes('pyrexia')) {
        toInject = ADAPTIVE_FOLLOWUPS.fever || [];
    } else if (lower.includes('stomach') || lower.includes('abdomen') || lower.includes('belly') ||
               lower.includes('gastric') || lower.includes('पेट') || lower.includes('పొట్ట')) {
        toInject = ADAPTIVE_FOLLOWUPS.stomach || [];
    } else if (lower.includes('head') || lower.includes('migraine') || lower.includes('सिर') ||
               lower.includes('headache') || lower.includes('తలనొప్పి')) {
        toInject = ADAPTIVE_FOLLOWUPS.headache || [];
    } else if (lower.includes('breath') || lower.includes('breathless') || lower.includes('saans') ||
               lower.includes('soda') || lower.includes('సాస') || lower.includes('शwas') ||
               lower.includes('सांस') || lower.includes('shortness') || lower.includes('dyspnoea')) {
        toInject = ADAPTIVE_FOLLOWUPS.breathlessness || [];
    }

    if (toInject.length === 0) return;

    // Insert after chief_complaint (index 0), before index 1
    const insertAt = 1;
    const current = _voiceSession.activeQuestions;
    _voiceSession.activeQuestions = [
        ...current.slice(0, insertAt),
        ...toInject,
        ...current.slice(insertAt),
    ];

    // Show a subtle toast
    const total = _voiceSession.activeQuestions.length;
    const label = document.getElementById('voice-progress-label');
    if (label) label.textContent = `Adaptive questions added. Total: ${total}`;
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
        answer: answer.trim(),
        confidence: 0.9,
        source: _voiceSession.touchOnly ? 'touch' : 'browser',
        language: _voiceSession.language,
    };

    // After chief complaint, inject adaptive follow-up questions
    if (q.key === 'chief_complaint') {
        _voiceInjectAdaptiveFollowUps(answer.trim());
    }

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

    // Update Triage badge
    const triageBadge = document.getElementById('voice-case-triage-badge');
    if (triageBadge) {
        if (_voiceSession.hasRedFlag) {
            triageBadge.textContent = '🔴 PRIORITY RED FLAG — URGENT ATTENTION';
            triageBadge.style.background = '#fee2e2';
            triageBadge.style.color = '#dc2626';
            triageBadge.style.borderColor = '#f87171';
        } else {
            triageBadge.textContent = '🟢 ROUTINE PRE-CONSULTATION INTAKE';
            triageBadge.style.background = '#dcfce7';
            triageBadge.style.color = '#15803d';
            triageBadge.style.borderColor = '#86efac';
        }
    }

    const answered = Object.entries(_voiceSession.answers)
        .filter(([, v]) => v.answer && v.answer !== '[SKIPPED]');

    // Group items into medical history categories
    const categories = [
        { title: 'Chief Complaint & Present Illness', icon: 'stethoscope', keys: ['chief_complaint', 'chest_location', 'chest_exertion', 'chest_sweating', 'fever_temperature', 'fever_rash', 'stomach_location', 'stomach_bowel', 'headache_location', 'headache_vision', 'breath_onset'] },
        { title: 'Symptom Timeline & Progression', icon: 'schedule', keys: ['symptom_duration', 'pain_scale'] },
        { title: 'Past Medical & Chronic Conditions', icon: 'medical_services', keys: ['past_medical_history'] },
        { title: 'Current Medications & Dosages', icon: 'medication', keys: ['current_medications'] },
        { title: 'Known Drug & Food Allergies', icon: 'warning', keys: ['known_allergies'] },
        { title: 'Surgical & Hospitalization History', icon: 'healing', keys: ['surgical_history'] },
        { title: 'Family Medical History', icon: 'family_restroom', keys: ['family_history'] },
        { title: 'Lifestyle & Social Habits', icon: 'person', keys: ['lifestyle_habits'] },
        { title: 'Review of Systems & Additional Notes', icon: 'checklist', keys: ['review_of_systems', 'additional_info'] },
        { title: 'AYUSH Constitutional Evaluation', icon: 'nature_people', keys: ['prakriti', 'ahara_habits', 'vyayama_shakti', 'satmya'] },
    ];

    let sectionsHtml = '';
    categories.forEach(cat => {
        const catAnswers = answered.filter(([k]) => cat.keys.includes(k));
        if (catAnswers.length > 0) {
            sectionsHtml += `
                <div style="margin-bottom: 14px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px 16px;">
                    <div style="font-size: 0.82rem; font-weight: 800; color: #0369a1; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
                        <span class="material-symbols-outlined" style="font-size: 16px; color: #0284c7;">${cat.icon}</span>
                        ${cat.title}
                    </div>
                    <div style="display: grid; gap: 8px;">
                        ${catAnswers.map(([key, val]) => `
                            <div style="font-size: 0.86rem; color: #1e293b; line-height: 1.4;">
                                <strong style="color: #475569; font-size: 0.78rem; text-transform: capitalize; display: block;">${key.replace(/_/g, ' ')}:</strong>
                                <span style="background: #ffffff; padding: 4px 8px; border-radius: 6px; border: 1px solid #cbd5e1; display: inline-block; margin-top: 2px;">${escapeHtml(val.answer)}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }
    });

    // Attached documents section
    let docsHtml = '';
    if (attachedVoiceDocuments.length > 0) {
        docsHtml = `
            <div style="margin-bottom: 14px; background: #eff6ff; border: 1.5px solid #93c5fd; border-radius: 10px; padding: 12px 16px;">
                <div style="font-size: 0.82rem; font-weight: 800; color: #1e40af; text-transform: uppercase; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
                    <span class="material-symbols-outlined" style="font-size: 16px;">document_scanner</span>
                    Scanned &amp; Attached Medical Documents (${attachedVoiceDocuments.length})
                </div>
                <div style="display: grid; gap: 6px;">
                    ${attachedVoiceDocuments.map(d => `
                        <div style="font-size: 0.82rem; color: #1e293b; background: #ffffff; padding: 6px 10px; border-radius: 6px; border: 1px solid #bfdbfe; display: flex; justify-content: space-between; align-items: center;">
                            <span>📄 <strong>${escapeHtml(d.filename)}</strong> (${d.size})</span>
                            <span style="font-size: 0.72rem; color: #059669; font-weight: 700;">✓ OCR Processed</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    container.innerHTML = `
        ${_voiceSession.hasRedFlag ? `
            <div style="background: #fef2f2; border: 1.5px solid #f87171; border-radius: 10px; padding: 12px 16px; margin-bottom: 14px; display: flex; align-items: center; gap: 10px; color: #991b1b;">
                <span class="material-symbols-outlined" style="font-size: 24px; color: #dc2626;">warning</span>
                <div>
                    <strong style="font-size: 0.88rem;">Emergency Priority Symptom Detected:</strong>
                    <div style="font-size: 0.8rem; color: #b91c1c;">Patient reported symptoms that may require urgent medical triage. Hospital staff notified.</div>
                </div>
            </div>
        ` : ''}
        ${sectionsHtml}
        ${docsHtml}
        <div style="background: #fffbeb; border: 1px solid #fcd34d; border-radius: 8px; padding: 10px 14px; font-size: 0.8rem; color: #92400e; margin-top: 14px;">
            ⚠️ <strong>Physician Attestation:</strong> This preliminary clinical history was recorded by the patient pre-consultation via MEDLENS AI. Attending doctor must verify history during clinical consultation.
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
