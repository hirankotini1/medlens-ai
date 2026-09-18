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
   SPEECH-TO-TEXT — DUAL ENGINE (Browser Web Speech API + Server Fallback)
   ============================================================================ */
let _currentOnFinal = null;
let _currentOnInterim = null;
let _currentOnError = null;
let _currentOnEnd = null;
let _currentOnStatus = null;
let _currentOnVolume = null;
let _currentLanguageCode = 'en-IN';
let _accumulatedFinalText = '';
let _latestLiveTranscript = '';
let _recognitionSilenceTimer = null;

/**
 * Detects whether browser supports STT natively.
 */
function detectBrowserSTTSupport() {
    if (window.SpeechRecognition) return 'full';
    if (window.webkitSpeechRecognition) return 'webkit';
    return 'server'; // Supported via server-side Google Speech STT
}

/**
 * Starts dual-engine voice recognition.
 * Prioritizes native browser Web Speech API (Chrome/Edge/Safari/Android) for instant zero-latency recognition.
 * Falls back to audio recorder + server transcribe only when SpeechRecognition is not available.
 */
async function voiceStartListening(languageCode, onInterim, onFinal, onError, onEnd, onStatus, onVolume) {
    if (_voiceIsListening) {
        await voiceStopListening();
    }

    languageCode = languageCode || _voiceCurrentLanguage || 'en-IN';
    _currentLanguageCode = languageCode;
    _currentOnInterim = onInterim;
    _currentOnFinal = onFinal;
    _currentOnError = onError;
    _currentOnEnd = onEnd;
    _currentOnStatus = onStatus;
    _currentOnVolume = onVolume;
    _accumulatedFinalText = '';
    _latestLiveTranscript = '';
    _voiceIsListening = true;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (SpeechRecognition) {
        try {
            const recognition = new SpeechRecognition();
            const langConfig = voiceGetLanguageByCode(languageCode);
            const sttCode = langConfig ? langConfig.sttLang : 'en-IN';

            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.maxAlternatives = 1;
            recognition.lang = sttCode;

            const resetAutoStopTimer = () => {
                if (_recognitionSilenceTimer) clearTimeout(_recognitionSilenceTimer);
                _recognitionSilenceTimer = setTimeout(() => {
                    if (_voiceIsListening && (_latestLiveTranscript || _accumulatedFinalText)) {
                        console.info('[VoiceService] Auto-finalizing after pause in speech...');
                        voiceStopListening();
                    }
                }, 2200);
            };

            recognition.onstart = () => {
                _voiceIsListening = true;
                if (_currentOnStatus) _currentOnStatus('listening', '🔴 Listening... Speak clearly into your mic');
            };

            recognition.onresult = (event) => {
                // IMPORTANT: Loop ALL results from i=0 (not event.resultIndex) and SET (not +=)
                // _accumulatedFinalText to avoid duplicates when Chrome resets resultIndex.
                let finalText = '';
                let interim = '';
                for (let i = 0; i < event.results.length; i++) {
                    const res = event.results[i];
                    if (res.isFinal) {
                        finalText += (res[0].transcript || '') + ' ';
                    } else {
                        interim += (res[0].transcript || '');
                    }
                }
                _accumulatedFinalText = finalText;
                _latestLiveTranscript = (finalText + interim).trim();
                if (_latestLiveTranscript) {
                    if (_currentOnInterim) _currentOnInterim(_latestLiveTranscript);
                    resetAutoStopTimer();
                }
            };

            recognition.onerror = (event) => {
                console.warn('[VoiceService] Browser STT notice:', event.error);
                if (event.error === 'not-allowed') {
                    if (_currentOnError) _currentOnError('not-allowed', 'Microphone permission denied. Please click the lock or microphone icon in your browser address bar and select "Allow".');
                    voiceStopListening();
                } else if (event.error === 'no-speech') {
                    // benign interim event - do not abort
                } else if (event.error === 'audio-capture') {
                    if (_currentOnError) _currentOnError('audio-capture', 'No microphone detected or audio input is busy.');
                    voiceStopListening();
                }
            };

            recognition.onend = () => {
                if (_recognitionSilenceTimer) {
                    clearTimeout(_recognitionSilenceTimer);
                    _recognitionSilenceTimer = null;
                }
                // If browser recognition ended while still marked listening, cleanly finalize!
                if (_voiceIsListening) {
                    voiceStopListening();
                }
            };

            recognition.start();
            _voiceActiveRecognition = recognition;
            return true;
        } catch (e) {
            console.warn('[VoiceService] Browser SpeechRecognition start error, attempting audio recorder fallback:', e);
        }
    }

    // Fallback for browsers without native SpeechRecognition (e.g. Firefox desktop)
    if (_currentOnStatus) _currentOnStatus('listening', '🔴 Recording audio for server transcription...');
    await _startAudioRecording();
    return true;
}

/**
 * Stops voice listening and converts audio to text.
 */
async function voiceStopListening() {
    if (!_voiceIsListening) return;
    _voiceIsListening = false;

    if (_recognitionSilenceTimer) {
        clearTimeout(_recognitionSilenceTimer);
        _recognitionSilenceTimer = null;
    }

    // Stop browser recognition
    if (_voiceActiveRecognition) {
        try {
            _voiceActiveRecognition.onresult = null;
            _voiceActiveRecognition.onerror = null;
            _voiceActiveRecognition.onend = null;
            _voiceActiveRecognition.stop();
        } catch (e) {}
        _voiceActiveRecognition = null;
    }

    if (_currentOnStatus) _currentOnStatus('converting', '⏳ Converting voice to text...');

    // PRIORITY 1: Deliver whatever text was captured by the browser engine!
    // Check BOTH _latestLiveTranscript and _accumulatedFinalText so interim words are NEVER LOST!
    const capturedText = (_latestLiveTranscript || _accumulatedFinalText || '').trim();
    if (capturedText && capturedText.length > 0) {
        if (_currentOnStatus) _currentOnStatus('done', `✅ Voice converted: "${capturedText}"`);
        if (_currentOnFinal) _currentOnFinal(capturedText, 0.95);
        if (_currentOnEnd) _currentOnEnd();
        _latestLiveTranscript = '';
        _accumulatedFinalText = '';
        return;
    }

    // PRIORITY 2: If browser engine didn't capture text (e.g. fallback mode in Firefox), check audio blob
    const wavBlob = _stopAudioRecording();
    if (wavBlob && wavBlob.size >= 1000) {
        const result = await _transcribeAudioWithServer(wavBlob, _currentLanguageCode);
        if (result.transcript && result.transcript.trim()) {
            const tr = result.transcript.trim();
            if (_currentOnStatus) _currentOnStatus('done', `✅ Voice converted: "${tr}"`);
            if (_currentOnFinal) _currentOnFinal(tr, 0.92);
            if (_currentOnEnd) _currentOnEnd();
            _latestLiveTranscript = '';
            _accumulatedFinalText = '';
            return;
        }
    }

    // If genuine silence was heard
    if (_currentOnStatus) _currentOnStatus('idle', '⚠️ No speech detected. Tap microphone and speak clearly, or type below.');
    if (_currentOnError) _currentOnError('no_speech', 'No clear speech detected. Please speak closer to your microphone or type your answer.');
    if (_currentOnEnd) _currentOnEnd();
    _latestLiveTranscript = '';
    _accumulatedFinalText = '';
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
