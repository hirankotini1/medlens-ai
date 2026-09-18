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
   SESSION STATE
   ============================================================================ */
let _voiceSession = {
    language: 'en-IN',
    touchOnly: false,
    patientId: null,
    caseId: null,
    sessionId: null,
    currentQuestionIndex: 0,
    answers: {},         // { questionKey: { answer, confidence, source } }
    transcripts: [],
    startedAt: null,
    kioskMode: false,
    showTextFallback: false,
    pendingTranscript: '',
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
   STEP NAVIGATION
   ============================================================================ */
function voiceProceedToConsent() {
    if (!_voiceSession.language) {
        alert('Please select a language to continue.');
        return;
    }
    _voiceShowStep('consent');
}

function voiceProceedToSession(touchOnly = false) {
    _voiceSession.touchOnly = touchOnly;
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
window.voiceProceedToConsent = voiceProceedToConsent;
window.voiceProceedToSession = voiceProceedToSession;
window.voiceProceedToInterview = voiceProceedToInterview;
window.voiceGoBackToLanguage = voiceGoBackToLanguage;
window.showVoiceSettings = showVoiceSettings;
window.hideVoiceSettings = hideVoiceSettings;

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

    // Update language display badge
    const langDisplay = document.getElementById('voice-session-lang-display');
    const langConfig = typeof voiceGetLanguageByCode === 'function'
        ? voiceGetLanguageByCode(_voiceSession.language)
        : null;
    if (langDisplay && langConfig) {
        langDisplay.innerHTML = `${langConfig.flag} ${langConfig.nativeName}`;
    }

    // Populate settings language select
    _populateSettingsLanguageSelect();

    // Load first question
    _voiceLoadQuestion(0);
}

/* ============================================================================
   QUESTION LOADING AND DISPLAY
   ============================================================================ */
function _voiceLoadQuestion(index) {
    if (index >= VOICE_CLINICAL_QUESTIONS.length) {
        _voiceComplete();
        return;
    }

    _voiceSession.currentQuestionIndex = index;
    const q = VOICE_CLINICAL_QUESTIONS[index];

    // Update progress
    const pct = Math.round(((index + 1) / VOICE_CLINICAL_QUESTIONS.length) * 100);
    const fillEl = document.getElementById('voice-progress-fill');
    const labelEl = document.getElementById('voice-progress-label');
    if (fillEl) fillEl.style.width = `${pct}%`;
    if (labelEl) labelEl.textContent = `Question ${index + 1} of ${VOICE_CLINICAL_QUESTIONS.length} (${q.section})`;

    // Get localized question text
    const lang = _voiceSession.language;
    const questionText = q.text[lang] || q.text['en-IN'];

    // Display question
    const questionEl = document.getElementById('voice-ai-question');
    if (questionEl) questionEl.textContent = questionText;

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
function voiceToggleListening() {
    if (typeof isListening === 'function' && isListening()) {
        if (typeof voiceStopListening === 'function') voiceStopListening();
        _voiceUpdateMicState('idle');
        return;
    }

    // Clear previous content
    _voiceResetTranscriptUI();
    _voiceUpdateMicState('listening');

    const lang = _voiceSession.language;
    const started = typeof voiceStartListening === 'function' && voiceStartListening(
        lang,
        // onInterim: display live words in real time
        (interimText) => {
            const el = document.getElementById('voice-transcript-text');
            if (el) el.textContent = interimText + '...';
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
        alert('Please speak or type your answer first.');
        return;
    }

    const q = VOICE_CLINICAL_QUESTIONS[_voiceSession.currentQuestionIndex];
    _voiceSession.answers[q.key] = {
        answer: answer.trim(),
        confidence: 0.9,
        source: _voiceSession.touchOnly ? 'touch' : 'browser',
        language: _voiceSession.language,
    };

    // Save transcript to backend (non-blocking)
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
    const q = VOICE_CLINICAL_QUESTIONS[_voiceSession.currentQuestionIndex];
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
    const q = VOICE_CLINICAL_QUESTIONS[_voiceSession.currentQuestionIndex];
    if (!q) return;
    const text = q.text[_voiceSession.language] || q.text['en-IN'];
    if (typeof speakText === 'function') speakText(text, _voiceSession.language);
}

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
    const q = VOICE_CLINICAL_QUESTIONS[_voiceSession.currentQuestionIndex];
    const qFlags = q ? (q.redFlags || []) : [];
    const allFlags = [...RED_FLAG_TERMS, ...qFlags];

    const triggered = allFlags.some(flag => lower.includes(flag.toLowerCase()));
    const banner = document.getElementById('voice-red-flag-banner');
    if (banner) {
        banner.style.display = triggered ? 'flex' : 'none';
    }
}

/* ============================================================================
   SESSION COMPLETION
   ============================================================================ */
async function _voiceComplete() {
    if (typeof stopSpeaking === 'function') stopSpeaking();

    // Build summary
    const summaryEl = document.getElementById('voice-summary-case-id');
    if (summaryEl && _voiceSession.sessionId) {
        summaryEl.textContent = `Session: ${_voiceSession.sessionId} | Language: ${_voiceSession.language}`;
    }

    // Try to create a case record from answers
    try {
        await _voiceSubmitCaseToBackend();
    } catch (e) {
        console.warn('[VoiceCT] Could not submit case to backend:', e);
    }

    // Show summary highlights
    _voiceRenderSummaryHighlights();

    // Speak completion message
    const lang = _voiceSession.language;
    const completionMsg = {
        'en-IN': 'Thank you. Your medical history has been recorded. The doctor will review it shortly.',
        'hi-IN': 'धन्यवाद। आपकी जानकारी दर्ज कर ली गई है। डॉक्टर जल्द समीक्षा करेंगे।',
        'te-IN': 'ధన్యవాదాలు. మీ వైద్య చరిత్ర నమోదు చేయబడింది. డాక్టర్ త్వరలో సమీక్షిస్తారు.',
    }[lang] || 'Thank you. Your information has been recorded.';

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

    // Use existing case-taking API endpoint if available
    if (_voiceSession.patientId && Object.keys(historyData).length > 0) {
        try {
            const payload = {
                patient_id: _voiceSession.patientId,
                language_code: _voiceSession.language,
                voice_session_id: _voiceSession.sessionId,
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
                _voiceSession.caseId = data.case_id;
            }
        } catch (e) {
            // Non-fatal — local session is preserved
        }
    }
}

function _voiceRenderSummaryHighlights() {
    const container = document.getElementById('voice-summary-highlights');
    if (!container) return;

    const answered = Object.entries(_voiceSession.answers)
        .filter(([, v]) => v.answer !== '[SKIPPED]');

    if (!answered.length) {
        container.innerHTML = '';
        return;
    }

    const html = answered.slice(0, 5).map(([key, val]) => `
        <div style="display:flex; gap:8px; align-items:flex-start; padding:10px 14px; border-left:3px solid #059669; background:#f0fdf4; border-radius:6px; margin-bottom:8px;">
            <span class="material-symbols-outlined" style="font-size:16px; color:#059669; margin-top:2px;">check_circle</span>
            <div>
                <div style="font-size:0.78rem; font-weight:700; color:#064e3b; text-transform:uppercase;">${key.replace(/_/g, ' ')}</div>
                <div style="font-size:0.87rem; color:#1f2937;">${val.answer}</div>
            </div>
        </div>
    `).join('');

    container.innerHTML = `
        <div style="font-size:0.85rem; font-weight:700; color:#374151; margin-bottom:10px;">📋 Summary of Recorded Information:</div>
        ${html}
        <div style="background:#fffbeb; border:1px solid #fcd34d; border-radius:8px; padding:10px 14px; font-size:0.82rem; color:#92400e; margin-top:12px;">
            ⚠️ <strong>Clinical Disclaimer:</strong> This AI-collected history is a preliminary draft. A licensed physician must review, verify, and confirm all information before clinical use. This system does NOT diagnose medical conditions.
        </div>
    `;
}

function voiceStartNewSession() {
    _voiceSession = {
        language: 'en-IN',
        touchOnly: false,
        patientId: (typeof currentAuth !== 'undefined' && currentAuth.patientId) || (typeof activeCasePatientId !== 'undefined' && activeCasePatientId) || null,
        caseId: null,
        sessionId: null,
        currentQuestionIndex: 0,
        answers: {},
        transcripts: [],
        startedAt: null,
        kioskMode: false,
        showTextFallback: false,
        pendingTranscript: '',
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
