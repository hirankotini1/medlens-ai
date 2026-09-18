/**
 * MEDLENS AI — Multilingual Voice Service
 * Provider-agnostic client-side voice abstraction for patient case-taking.
 *
 * Architecture (layered fallback):
 *   TTS: Backend API → Browser SpeechSynthesis → Visual text display
 *   STT: Backend API → Browser Web Speech API → Manual text input
 *
 * IMPORTANT:
 * - Existing app.js report/symptom TTS functions are NOT touched.
 * - This module is used exclusively by the voice case-taking interface.
 * - Reusable utilities (speakText, stopSpeaking) can be called from anywhere.
 *
 * @version 1.0.0 — SIH PS 26047
 */

/* ============================================================================
   LANGUAGE REGISTRY — 23 supported languages with BCP-47 codes
   ============================================================================ */
const VOICE_LANGUAGES = [
    { code: 'en-IN', name: 'English', nativeName: 'English', flag: '🇬🇧', ttsLang: 'en-IN', sttLang: 'en-IN' },
    { code: 'hi-IN', name: 'Hindi', nativeName: 'हिन्दी', flag: '🇮🇳', ttsLang: 'hi-IN', sttLang: 'hi-IN' },
    { code: 'te-IN', name: 'Telugu', nativeName: 'తెలుగు', flag: '🇮🇳', ttsLang: 'te-IN', sttLang: 'te-IN' },
    { code: 'or-IN', name: 'Odia', nativeName: 'ଓଡ଼ିଆ', flag: '🇮🇳', ttsLang: 'or-IN', sttLang: 'or-IN' },
    { code: 'ta-IN', name: 'Tamil', nativeName: 'தமிழ்', flag: '🇮🇳', ttsLang: 'ta-IN', sttLang: 'ta-IN' },
    { code: 'kn-IN', name: 'Kannada', nativeName: 'ಕನ್ನಡ', flag: '🇮🇳', ttsLang: 'kn-IN', sttLang: 'kn-IN' },
    { code: 'ml-IN', name: 'Malayalam', nativeName: 'മലയാളം', flag: '🇮🇳', ttsLang: 'ml-IN', sttLang: 'ml-IN' },
    { code: 'bn-IN', name: 'Bengali', nativeName: 'বাংলা', flag: '🇮🇳', ttsLang: 'bn-IN', sttLang: 'bn-IN' },
    { code: 'mr-IN', name: 'Marathi', nativeName: 'मराठी', flag: '🇮🇳', ttsLang: 'mr-IN', sttLang: 'mr-IN' },
    { code: 'gu-IN', name: 'Gujarati', nativeName: 'ગુજરાતી', flag: '🇮🇳', ttsLang: 'gu-IN', sttLang: 'gu-IN' },
    { code: 'pa-IN', name: 'Punjabi', nativeName: 'ਪੰਜਾਬੀ', flag: '🇮🇳', ttsLang: 'pa-IN', sttLang: 'pa-IN' },
    { code: 'ur-IN', name: 'Urdu', nativeName: 'اردو', flag: '🇮🇳', ttsLang: 'ur-IN', sttLang: 'ur-PK' },
    { code: 'as-IN', name: 'Assamese', nativeName: 'অসমীয়া', flag: '🇮🇳', ttsLang: 'as-IN', sttLang: 'as-IN' },
    { code: 'ks-IN', name: 'Kashmiri', nativeName: 'कश्मीरी', flag: '🇮🇳', ttsLang: 'ks-IN', sttLang: 'hi-IN' },
    { code: 'ne-IN', name: 'Nepali', nativeName: 'नेपाली', flag: '🇮🇳', ttsLang: 'ne-IN', sttLang: 'ne-NP' },
    { code: 'kok-IN', name: 'Konkani', nativeName: 'कोंकणी', flag: '🇮🇳', ttsLang: 'kok-IN', sttLang: 'mr-IN' },
    { code: 'mai-IN', name: 'Maithili', nativeName: 'मैथिली', flag: '🇮🇳', ttsLang: 'mai-IN', sttLang: 'hi-IN' },
    { code: 'mni-IN', name: 'Manipuri', nativeName: 'মৈতৈলোন্', flag: '🇮🇳', ttsLang: 'mni-IN', sttLang: 'bn-IN' },
    { code: 'brx-IN', name: 'Bodo', nativeName: 'बड़ो', flag: '🇮🇳', ttsLang: 'brx-IN', sttLang: 'as-IN' },
    { code: 'doi-IN', name: 'Dogri', nativeName: 'डोगरी', flag: '🇮🇳', ttsLang: 'doi-IN', sttLang: 'hi-IN' },
    { code: 'sat-IN', name: 'Santali', nativeName: 'ᱥᱟᱱᱛᱟᱲᱤ', flag: '🇮🇳', ttsLang: 'sat-IN', sttLang: 'bn-IN' },
    { code: 'sd-IN', name: 'Sindhi', nativeName: 'سنڌي', flag: '🇮🇳', ttsLang: 'sd-IN', sttLang: 'ur-IN' },
    { code: 'sa-IN', name: 'Sanskrit', nativeName: 'संस्कृत', flag: '🇮🇳', ttsLang: 'sa-IN', sttLang: 'hi-IN' },
];

/* ============================================================================
   INTERNAL STATE
   ============================================================================ */
let _voiceCurrentLanguage = 'en-IN';
let _voiceSpeechSpeed = 1.0;
let _voiceAutoPlay = true;
let _voiceActiveSpeech = null;       // Active SpeechSynthesisUtterance
let _voiceActiveRecognition = null;  // Active SpeechRecognition
let _voiceIsListening = false;
let _voiceIsSpeaking = false;

/* ============================================================================
   PUBLIC API — getSupportedLanguages()
   ============================================================================ */
function voiceGetSupportedLanguages() {
    return VOICE_LANGUAGES;
}

function voiceGetLanguageByCode(code) {
    if (!code) return VOICE_LANGUAGES[0];
    const c = String(code).trim().toLowerCase();
    return VOICE_LANGUAGES.find(l => 
        l.code.toLowerCase() === c || 
        l.name.toLowerCase() === c || 
        l.code.toLowerCase().startsWith(c) ||
        c.startsWith(l.code.toLowerCase().slice(0, 2))
    ) || VOICE_LANGUAGES[0];
}

function voiceSetLanguage(code) {
    _voiceCurrentLanguage = code;
    window._selectedLanguage = code; // Keep existing global in sync
}

function voiceGetCurrentLanguage() {
    return _voiceCurrentLanguage;
}

/* ============================================================================
   TEXT-TO-SPEECH — speakText(text, languageCode, speed)
   Layered: Backend API → Browser SpeechSynthesis → Visual text display
   ============================================================================ */
async function speakText(text, languageCode, speed) {
    if (!text || !text.trim()) return;
    languageCode = languageCode || _voiceCurrentLanguage || 'en-IN';
    speed = speed || _voiceSpeechSpeed || 1.0;

    // Stop any current speech first
    stopSpeaking();

    // Try backend TTS first (server-side providers)
    const backendAudio = await _tryBackendTTS(text, languageCode);
    if (backendAudio) {
        _playAudioBuffer(backendAudio);
        return;
    }

    // Fallback: Browser SpeechSynthesis
    _browserSpeak(text, languageCode, speed);
}

async function _tryBackendTTS(text, languageCode) {
    try {
        const res = await fetch(apiUrl('/api/voice/speak'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, language_code: languageCode, speed: _voiceSpeechSpeed }),
            signal: AbortSignal.timeout(5000),
        });

        if (!res.ok) return null;
        const contentType = res.headers.get('content-type') || '';

        if (contentType.includes('audio')) {
            // Server returned actual audio bytes
            const arrayBuffer = await res.arrayBuffer();
            return arrayBuffer;
        } else {
            // Server returned fallback instruction — use browser TTS
            return null;
        }
    } catch (e) {
        // Backend unavailable — silent fallback to browser
        return null;
    }
}

function _playAudioBuffer(arrayBuffer) {
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        audioContext.decodeAudioData(arrayBuffer, (buffer) => {
            const source = audioContext.createBufferSource();
            source.buffer = buffer;
            source.connect(audioContext.destination);
            source.start(0);
            _voiceIsSpeaking = true;
            source.onended = () => { _voiceIsSpeaking = false; };
        });
    } catch (e) {
        console.warn('[VoiceService] Could not play audio buffer:', e);
    }
}

function _browserSpeak(text, languageCode, speed) {
    if (!window.speechSynthesis) {
        // Visual-only fallback — text is always displayed in UI
        console.info('[VoiceService] Browser TTS unavailable. Text displayed visually.');
        return;
    }

    const langConfig = voiceGetLanguageByCode(languageCode);
    const targetLang = langConfig ? langConfig.ttsLang : 'en-IN';

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = speed || 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    // Select best matching voice
    const bestVoice = _selectBestVoice(targetLang);
    if (bestVoice) utterance.voice = bestVoice;
    utterance.lang = targetLang;

    utterance.onstart = () => { _voiceIsSpeaking = true; };
    utterance.onend = () => { _voiceIsSpeaking = false; _voiceActiveSpeech = null; };
    utterance.onerror = (e) => {
        _voiceIsSpeaking = false;
        console.warn('[VoiceService] Browser TTS error:', e.error);
    };

    _voiceActiveSpeech = utterance;
    window.speechSynthesis.speak(utterance);
}

function _selectBestVoice(targetLang) {
    const voices = window.speechSynthesis ? window.speechSynthesis.getVoices() : [];
    if (!voices.length) return null;

    const langCode = targetLang.toLowerCase();
    const baseLang = langCode.split('-')[0];

    // 1. Exact locale match (e.g., hi-IN)
    let match = voices.find(v => v.lang.toLowerCase() === langCode);
    if (match) return match;

    // 2. Base language match (e.g., hi)
    match = voices.find(v => v.lang.toLowerCase().startsWith(baseLang));
    if (match) return match;

    // 3. Prefer Indian English fallback
    match = voices.find(v => v.lang.toLowerCase().includes('in'));
    if (match) return match;

    return null; // Browser picks default
}

function stopSpeaking() {
    if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
    }
    _voiceIsSpeaking = false;
    _voiceActiveSpeech = null;
}

function isSpeaking() {
    return _voiceIsSpeaking || (window.speechSynthesis && window.speechSynthesis.speaking);
}

function getAvailableVoices() {
    if (!window.speechSynthesis) return [];
    return window.speechSynthesis.getVoices();
}

/* ============================================================================
   AUDIO RECORDER (16kHz 16-BIT MONO PCM WAV) FOR GUARANTEED MULTILINGUAL STT
   ============================================================================ */
let _activeAudioStream = null;
let _activeAudioContext = null;
let _activeAudioInput = null;
let _activeProcessor = null;
let _activeMuteNode = null;
let _recordedAudioBuffers = [];
let _recordedSampleRate = 16000;
let _speechDetected = false;
let _lastSpeechTime = 0;
let _recordingStartTime = 0;
let _vadInterval = null;

async function _startAudioRecording() {
    _recordedAudioBuffers = [];
    _speechDetected = false;
    _recordingStartTime = Date.now();
    _lastSpeechTime = Date.now();

    try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            console.warn('[VoiceService] getUserMedia not available in this browser');
            return false;
        }

        _activeAudioStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
            }
        });

        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        _activeAudioContext = new AudioCtx();

        // Chrome autoplay policy: resume AudioContext
        if (_activeAudioContext.state === 'suspended') {
            await _activeAudioContext.resume();
        }

        _recordedSampleRate = _activeAudioContext.sampleRate || 44100;
        _activeAudioInput = _activeAudioContext.createMediaStreamSource(_activeAudioStream);

        // 4096 buffer size for capturing PCM
        _activeProcessor = _activeAudioContext.createScriptProcessor(4096, 1, 1);
        _activeProcessor.onaudioprocess = (e) => {
            if (!_voiceIsListening) return;
            const channelData = e.inputBuffer.getChannelData(0);
            _recordedAudioBuffers.push(new Float32Array(channelData));

            // Calculate live RMS volume
            let sum = 0;
            for (let i = 0; i < channelData.length; i++) {
                sum += channelData[i] * channelData[i];
            }
            const rms = Math.sqrt(sum / channelData.length);

            if (_currentOnVolume) {
                _currentOnVolume(rms);
            }

            // Voice Activity Detection (VAD)
            if (rms > 0.015) {
                _speechDetected = true;
                _lastSpeechTime = Date.now();
            }
        };

        // Create silent gain node so audio does not echo out of speakers
        _activeMuteNode = _activeAudioContext.createGain();
        _activeMuteNode.gain.value = 0;

        _activeAudioInput.connect(_activeProcessor);
        _activeProcessor.connect(_activeMuteNode);
        _activeMuteNode.connect(_activeAudioContext.destination);

        // Setup intelligent silence monitor (auto-stops when user finishes speaking)
        if (_vadInterval) clearInterval(_vadInterval);
        _vadInterval = setInterval(() => {
            if (!_voiceIsListening) {
                clearInterval(_vadInterval);
                _vadInterval = null;
                return;
            }

            const now = Date.now();
            // If speech was detected and followed by 2.2s of silence, automatically finalize
            if (_speechDetected && (now - _lastSpeechTime > 2200)) {
                console.info('[VoiceService] Silence detected after speech. Auto-finalizing transcript...');
                clearInterval(_vadInterval);
                _vadInterval = null;
                voiceStopListening();
                return;
            }

            // Maximum recording limit safety: 15 seconds
            if (now - _recordingStartTime > 15000) {
                console.info('[VoiceService] Maximum recording duration reached. Auto-stopping...');
                clearInterval(_vadInterval);
                _vadInterval = null;
                voiceStopListening();
            }
        }, 300);

        return true;
    } catch (e) {
        console.warn('[VoiceService] Could not initialize raw audio stream:', e);
        return false;
    }
}

function _stopAudioRecording() {
    if (_vadInterval) {
        clearInterval(_vadInterval);
        _vadInterval = null;
    }

    if (_activeProcessor) {
        try { _activeProcessor.disconnect(); } catch (e) {}
        _activeProcessor = null;
    }
    if (_activeMuteNode) {
        try { _activeMuteNode.disconnect(); } catch (e) {}
        _activeMuteNode = null;
    }
    if (_activeAudioInput) {
        try { _activeAudioInput.disconnect(); } catch (e) {}
        _activeAudioInput = null;
    }
    if (_activeAudioContext) {
        try { _activeAudioContext.close(); } catch (e) {}
        _activeAudioContext = null;
    }
    if (_activeAudioStream) {
        try {
            _activeAudioStream.getTracks().forEach(t => t.stop());
        } catch (e) {}
        _activeAudioStream = null;
    }

    return _buildWavBlob(_recordedAudioBuffers, _recordedSampleRate);
}

/**
 * Encodes Float32 PCM buffers downsampled to 16kHz 16-bit Mono RIFF WAV Blob.
 */
function _buildWavBlob(buffers, inputSampleRate) {
    let totalLength = 0;
    for (let i = 0; i < buffers.length; i++) {
        totalLength += buffers[i].length;
    }
    if (totalLength === 0) return null;

    const merged = new Float32Array(totalLength);
    let offset = 0;
    for (let i = 0; i < buffers.length; i++) {
        merged.set(buffers[i], offset);
        offset += buffers[i].length;
    }

    // Downsample to target 16kHz for speech recognition
    const targetSampleRate = 16000;
    let downsampled;
    if (inputSampleRate === targetSampleRate) {
        downsampled = merged;
    } else {
        const ratio = inputSampleRate / targetSampleRate;
        const newLen = Math.round(merged.length / ratio);
        downsampled = new Float32Array(newLen);
        for (let i = 0; i < newLen; i++) {
            const srcIdx = i * ratio;
            const idx1 = Math.floor(srcIdx);
            const idx2 = Math.min(idx1 + 1, merged.length - 1);
            const weight = srcIdx - idx1;
            downsampled[i] = merged[idx1] * (1 - weight) + merged[idx2] * weight;
        }
    }

    const byteLen = downsampled.length * 2;
    const buffer = new ArrayBuffer(44 + byteLen);
    const view = new DataView(buffer);

    // RIFF identifier
    _writeAscii(view, 0, 'RIFF');
    view.setUint32(4, 36 + byteLen, true);
    _writeAscii(view, 8, 'WAVE');

    // fmt sub-chunk
    _writeAscii(view, 12, 'fmt ');
    view.setUint32(16, 16, true);             // Subchunk1Size (16 for PCM)
    view.setUint16(20, 1, true);              // AudioFormat (1 = PCM)
    view.setUint16(22, 1, true);              // NumChannels (1 = Mono)
    view.setUint32(24, targetSampleRate, true);// SampleRate (16000)
    view.setUint32(28, targetSampleRate * 2, true); // ByteRate (SampleRate * NumChannels * BitsPerSample/8)
    view.setUint16(32, 2, true);              // BlockAlign (NumChannels * BitsPerSample/8)
    view.setUint16(34, 16, true);             // BitsPerSample (16 bits)

    // data sub-chunk
    _writeAscii(view, 36, 'data');
    view.setUint32(40, byteLen, true);

    // 16-bit PCM integer samples
    let pcmOffset = 44;
    for (let i = 0; i < downsampled.length; i++) {
        let s = Math.max(-1, Math.min(1, downsampled[i]));
        view.setInt16(pcmOffset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
        pcmOffset += 2;
    }

    return new Blob([view], { type: 'audio/wav' });
}

function _writeAscii(view, offset, string) {
    for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
    }
}

async function _transcribeAudioWithServer(wavBlob, languageCode) {
    if (!wavBlob || wavBlob.size < 600) {
        return { transcript: '', error: 'Audio recording too short' };
    }
    try {
        const formData = new FormData();
        formData.append('audio', wavBlob, 'recording.wav');
        formData.append('language_code', languageCode || 'en-IN');

        const res = await fetch(apiUrl('/api/voice/transcribe'), {
            method: 'POST',
            body: formData,
            signal: AbortSignal.timeout(20000),
        });

        if (!res.ok) {
            return { transcript: '', error: `Server error ${res.status}` };
        }

        const data = await res.json();
        return {
            transcript: (data.transcript || '').trim(),
            provider: data.provider || 'server',
            noSpeech: !!data.no_speech
        };
    } catch (e) {
        console.warn('[VoiceService] Server transcribe error:', e);
        return { transcript: '', error: e.message };
    }
}

/* ============================================================================
   SPEECH-TO-TEXT — Clean Browser Web Speech API Implementation
   Uses continuous=false for predictable single-delivery behavior.
   All session state lives inside the closure — no global race conditions.
   ============================================================================ */
let _currentOnFinal = null;
let _currentOnInterim = null;
let _currentOnError = null;
let _currentOnEnd = null;
let _currentOnStatus = null;
let _currentOnVolume = null;
let _currentLanguageCode = 'en-IN';
// Note: _voiceActiveRecognition is declared in INTERNAL STATE above (line 53)

function detectBrowserSTTSupport() {
    if (window.SpeechRecognition) return 'full';
    if (window.webkitSpeechRecognition) return 'webkit';
    return 'server';
}

/**
 * Starts voice recognition.
 * Uses browser Web Speech API with continuous=false for clean, single-delivery behavior.
 * Falls back to server transcription if Web Speech API is unavailable (Firefox).
 */
async function voiceStartListening(languageCode, onInterim, onFinal, onError, onEnd, onStatus, onVolume) {
    // Stop any previous session cleanly
    if (_voiceIsListening || _voiceActiveRecognition) {
        await voiceStopListening();
    }

    languageCode = languageCode || _voiceCurrentLanguage || 'en-IN';
    _currentLanguageCode = languageCode;
    _currentOnFinal = onFinal;
    _currentOnInterim = onInterim;
    _currentOnError = onError;
    _currentOnEnd = onEnd;
    _currentOnStatus = onStatus;
    _currentOnVolume = onVolume;
    _voiceIsListening = true;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (SpeechRecognition) {
        try {
            const recognition = new SpeechRecognition();
            const langConfig = voiceGetLanguageByCode(languageCode);
            const sttCode = langConfig ? langConfig.sttLang : 'en-IN';

            // continuous=false: fires exactly ONE onend after one utterance.
            // This is the key to preventing duplicate text — no complex multi-onend handling needed.
            recognition.continuous = false;
            recognition.interimResults = true;
            recognition.maxAlternatives = 1;
            recognition.lang = sttCode;

            // All session state lives HERE inside the closure — no global pollution.
            let _sessionTranscript = '';
            let _delivered = false;   // Ensures onFinal fires exactly once
            let _silenceTimer = null;

            const _clearSilenceTimer = () => {
                if (_silenceTimer) { clearTimeout(_silenceTimer); _silenceTimer = null; }
            };

            recognition.onstart = () => {
                if (onStatus) onStatus('listening', '🔴 Listening... Speak clearly into your mic');
            };

            recognition.onresult = (event) => {
                // Build the complete transcript from scratch each time (never +=)
                let transcript = '';
                for (let i = 0; i < event.results.length; i++) {
                    transcript += event.results[i][0].transcript;
                }
                _sessionTranscript = transcript.trim();
                if (_sessionTranscript && onInterim) {
                    onInterim(_sessionTranscript);
                }
                // Auto-stop after 2s of silence so text gets delivered
                _clearSilenceTimer();
                _silenceTimer = setTimeout(() => {
                    if (_voiceIsListening) recognition.stop();
                }, 2000);
            };

            recognition.onerror = (event) => {
                _clearSilenceTimer();
                if (event.error === 'no-speech') return; // Ignore — onend handles delivery
                if (event.error === 'not-allowed') {
                    _delivered = true;
                    _voiceIsListening = false;
                    _voiceActiveRecognition = null;
                    if (onError) onError('not-allowed', 'Microphone permission denied. Tap the lock icon in your browser address bar and select "Allow".');
                    if (onEnd) onEnd();
                } else if (event.error === 'audio-capture') {
                    _delivered = true;
                    _voiceIsListening = false;
                    _voiceActiveRecognition = null;
                    if (onError) onError('audio-capture', 'No microphone found or it is in use by another app.');
                    if (onEnd) onEnd();
                }
            };

            // onend fires ONCE when recognition stops (either naturally or via .stop())
            // This is the single, guaranteed delivery point.
            recognition.onend = () => {
                _clearSilenceTimer();
                _voiceIsListening = false;
                _voiceActiveRecognition = null;

                if (_delivered) return; // Already delivered (e.g. from onerror)
                _delivered = true;

                const text = _sessionTranscript.trim();
                if (text) {
                    if (onStatus) onStatus('done', `✅ Captured: "${text}"`);
                    if (onFinal) onFinal(text, 0.95);
                } else {
                    if (onStatus) onStatus('idle', '⚠️ No speech heard. Tap mic and speak, or type below.');
                    if (onError) onError('no_speech', 'No speech was captured. Please speak clearly into the microphone.');
                }
                if (onEnd) onEnd();
            };

            recognition.start();
            _voiceActiveRecognition = recognition;
            if (onStatus) onStatus('listening', '🔴 Listening... Speak clearly into your mic');
            return true;
        } catch (e) {
            console.warn('[VoiceService] Browser SpeechRecognition unavailable, falling back to server:', e);
        }
    }

    // Fallback: server-side transcription (Firefox desktop, older browsers)
    if (onStatus) onStatus('listening', '🔴 Recording audio for server transcription...');
    await _startAudioRecording();
    return true;
}

/**
 * Stops voice listening. The recognition.onend callback handles the actual text delivery.
 */
async function voiceStopListening() {
    _voiceIsListening = false;
    if (_voiceActiveRecognition) {
        try {
            _voiceActiveRecognition.stop(); // Triggers onend → text delivered there
        } catch (e) {}
        // Don't null _voiceActiveRecognition here — onend does it
    } else {
        // Server fallback path: build wav and transcribe
        const wavBlob = _stopAudioRecording();
        if (wavBlob && wavBlob.size >= 1000) {
            if (_currentOnStatus) _currentOnStatus('converting', '⏳ Transcribing...');
            const result = await _transcribeAudioWithServer(wavBlob, _currentLanguageCode);
            if (result.transcript && result.transcript.trim()) {
                const tr = result.transcript.trim();
                if (_currentOnStatus) _currentOnStatus('done', `✅ Voice converted: "${tr}"`);
                if (_currentOnFinal) _currentOnFinal(tr, 0.92);
                if (_currentOnEnd) _currentOnEnd();
                return;
            }
        }
        if (_currentOnStatus) _currentOnStatus('idle', '⚠️ No speech detected.');
        if (_currentOnError) _currentOnError('no_speech', 'No speech detected. Please try again.');
        if (_currentOnEnd) _currentOnEnd();
    }
}

function isListening() {
    return _voiceIsListening;
}

// Global window bindings
window.voiceStartListening = voiceStartListening;
window.voiceStopListening = voiceStopListening;
window.isListening = isListening;
window.voiceGetSupportedLanguages = voiceGetSupportedLanguages;
window.voiceGetLanguageByCode = voiceGetLanguageByCode;

/* ============================================================================
   MICROPHONE PERMISSION TEST
   ============================================================================ */
async function voiceTestMicrophone() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        stream.getTracks().forEach(track => track.stop()); // Release immediately
        return { available: true, message: 'Microphone detected ✓' };
    } catch (e) {
        if (e.name === 'NotAllowedError') {
            return { available: false, message: 'Microphone permission denied. Please allow in browser settings.' };
        } else if (e.name === 'NotFoundError') {
            return { available: false, message: 'No microphone found on this device.' };
        } else {
            return { available: false, message: `Microphone unavailable: ${e.message}` };
        }
    }
}

/* ============================================================================
   VOICE SETTINGS
   ============================================================================ */
function voiceSetSpeed(speed) {
    _voiceSpeechSpeed = Math.max(0.5, Math.min(2.0, parseFloat(speed) || 1.0));
}

function voiceSetAutoPlay(value) {
    _voiceAutoPlay = !!value;
}

function voiceGetSettings() {
    return {
        language: _voiceCurrentLanguage,
        speed: _voiceSpeechSpeed,
        autoPlay: _voiceAutoPlay,
        sttSupport: detectBrowserSTTSupport(),
        ttsSupport: !!window.speechSynthesis,
    };
}

/* ============================================================================
   LANGUAGE CHANGE HANDLER — called when user changes language
   ============================================================================ */
function onLanguageChange(langCode) {
    // Stop any active speech/recognition
    stopSpeaking();
    voiceStopListening();

    // Update language
    voiceSetLanguage(langCode);
    window._selectedLanguage = langCode;

    // Update the global language selector in the navbar if it exists
    const globalSelect = document.getElementById('global-lang-select');
    if (globalSelect && globalSelect.value !== langCode) {
        // Only update if the value is in the selector
        const opt = globalSelect.querySelector(`option[value="${langCode}"]`);
        if (opt) globalSelect.value = langCode;
    }

    // Notify voice UI if active
    const voiceLangDisplay = document.getElementById('voice-session-lang-display');
    if (voiceLangDisplay) {
        const langConfig = voiceGetLanguageByCode(langCode);
        voiceLangDisplay.innerHTML = langConfig
            ? `${langConfig.flag} ${langConfig.nativeName}`
            : langCode;
    }
}

/* ============================================================================
   VOICE TRANSCRIPT — save to backend
   ============================================================================ */
async function voiceSaveTranscript(caseId, sessionId, questionKey, questionText, answerOriginal, languageCode, confidence, source) {
    try {
        await fetch(apiUrl('/api/voice/save-transcript'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                case_id: caseId,
                session_id: sessionId,
                question_key: questionKey,
                question_text: questionText,
                answer_original: answerOriginal,
                language_code: languageCode,
                confidence: confidence,
                source: source || 'browser',
            }),
        });
    } catch (e) {
        console.warn('[VoiceService] Could not save transcript to backend:', e);
        // Non-fatal — transcript is preserved in the UI
    }
}

/* ============================================================================
   INITIALIZATION — load voices when browser is ready
   ============================================================================ */
if (window.speechSynthesis) {
    // Chrome loads voices asynchronously
    window.speechSynthesis.onvoiceschanged = () => {
        const voices = window.speechSynthesis.getVoices();
        console.info(`[VoiceService] ${voices.length} browser TTS voices loaded.`);
    };
}

// Expose as global for backward compatibility with any existing calls
window.speakText = speakText;
window.stopSpeaking = stopSpeaking;
window.isSpeaking = isSpeaking;
window.getAvailableVoices = getAvailableVoices;
window.onLanguageChange = onLanguageChange;

console.info('[VoiceService] MEDLENS Multilingual Voice Service initialized.');
