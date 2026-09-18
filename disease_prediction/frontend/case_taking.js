/**
 * MEDLENS AI x Medicover — SIH Patient Case-Taking Software Controller
 * Provides:
 * 1. Patient Consent & Mock ABHA / ABDM Connector
 * 2. 10-Section Guided Case Taking Workflow
 * 3. Speech-to-Text Voice Recording Engine with Editable Fallback
 * 4. Adaptive Clinical Question Engine
 * 5. Medical Document & Laboratory Report Attachment
 * 6. Optional AYUSH Constitutional Evaluation
 * 7. Physician-Ready Structured Case Summary
 * 8. Doctor Console Review, Edit, & Sign-off Integration
 */

let activeCaseId = null;
let activeCasePatientId = null;
let currentSectionIndex = 0;
let clinicalSectionsData = [];
let activeSpeechRecognition = null;
let isRecordingVoice = false;
let recordedCaseAnswers = {};
let attachedCaseDocuments = [];

// ==============================================================================
// 1. INITIALIZATION & METADATA FETCH
// ==============================================================================
async function initCaseTakingModule() {
    try {
        const res = await fetch(apiUrl('/api/cases/sections'));
        if (res.ok) {
            const data = await res.json();
            clinicalSectionsData = data.sections || [];
        }
    } catch (e) {
        console.warn('Using offline clinical sections fallback:', e);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initCaseTakingModule();
});


// ==============================================================================
// 2. MOCK ABHA / ABDM GENERATOR
// ==============================================================================
function generateMockAbhaNumber() {
    const p1 = Math.floor(1000 + Math.random() * 9000);
    const p2 = Math.floor(1000 + Math.random() * 9000);
    const p3 = Math.floor(1000 + Math.random() * 9000);
    const abhaNum = `91-${p1}-${p2}-${p3}`;
    const abhaInput = document.getElementById('case-abha-input');
    const abhaAddress = document.getElementById('case-abha-address');
    if (abhaInput) abhaInput.value = abhaNum;
    if (abhaAddress) abhaAddress.value = `patient.${p1}@abdm`;
    showToast(`✓ Generated Mock ABHA ID: ${abhaNum}`, 'success');
}


// ==============================================================================
// 3. CASE TAKING LAUNCH & CONSENT SCREEN
// ==============================================================================
function launchClinicalCaseTaking(patientId = null) {
    activeCasePatientId = patientId || (currentAuth && currentAuth.patientId) || 'PAT-1001';
    switchView('case-taking');
    
    // Auto-fill patient badge
    const badge = document.getElementById('case-patient-badge');
    if (badge) {
        const pName = (currentAuth && currentAuth.patientName) || 'Patient Self-Recording';
        badge.innerHTML = `<span class="material-symbols-outlined" style="font-size: 16px;">person</span> <strong>${activeCasePatientId}</strong> (${escapeHtml(pName)})`;
    }

    // Reset wizard to Step 1 (Consent & Intake)
    document.getElementById('case-step-consent').style.display = 'block';
    document.getElementById('case-step-wizard').style.display = 'none';
    document.getElementById('case-step-summary').style.display = 'none';
    
    // Clear state
    activeCaseId = null;
    currentSectionIndex = 0;
    recordedCaseAnswers = {};
    attachedCaseDocuments = [];
}

async function handleCaseConsentSubmit(event) {
    if (event) event.preventDefault();
    const consentCheckbox = document.getElementById('case-consent-checkbox');
    if (!consentCheckbox || !consentCheckbox.checked) {
        showModalAlert('Please review and check the informed consent box to proceed with recording your clinical history.', 'Consent Required');
        return;
    }

    const chiefComplaintInput = document.getElementById('case-initial-complaint');
    const chiefComplaint = chiefComplaintInput ? chiefComplaintInput.value.trim() : '';
    const abhaInput = document.getElementById('case-abha-input');
    const abhaId = abhaInput ? abhaInput.value.trim() : '';

    try {
        const payload = {
            patient_id: activeCasePatientId || 'PAT-1001',
            chief_complaint: chiefComplaint,
            abha_id: abhaId || '91-DEMO-ABHA',
            consent_given: true,
            consent_text: 'I voluntarily provide informed consent for automated clinical case-taking, voice transcript processing, and medical document extraction for physician decision support.'
        };

        const res = await fetch(apiUrl('/api/cases/start'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const err = await safeJson(res);
            throw new Error(err.detail || 'Could not initialize clinical case.');
        }

        const data = await res.json();
        activeCaseId = data.case_id;
        showToast(`✓ Clinical Case initialized: ${activeCaseId}`, 'success');

        // Transition to Guided Wizard
        document.getElementById('case-step-consent').style.display = 'none';
        document.getElementById('case-step-wizard').style.display = 'block';
        document.getElementById('case-step-summary').style.display = 'none';

        // Pre-populate chief complaint if provided
        if (chiefComplaint) {
            recordedCaseAnswers['chief_complaint'] = { raw: chiefComplaint };
        }

        renderCurrentSection();
        loadAvailableDocumentsForAttachment();
    } catch (err) {
        showModalAlert(`Error starting case taking: ${err.message}`, 'Initialization Failed');
    }
}


// ==============================================================================
// 4. GUIDED SECTION WIZARD & ADAPTIVE PROMPT
// ==============================================================================
function renderCurrentSection() {
    if (!clinicalSectionsData || clinicalSectionsData.length === 0) return;
    const sec = clinicalSectionsData[currentSectionIndex];
    if (!sec) return;

    // Update Progress Stepper
    const total = clinicalSectionsData.length;
    const progressPct = Math.round(((currentSectionIndex + 1) / total) * 100);
    const bar = document.getElementById('case-progress-bar');
    const label = document.getElementById('case-progress-label');
    if (bar) bar.style.width = `${progressPct}%`;
    if (label) label.innerText = `Section ${currentSectionIndex + 1} of ${total} • ${sec.title}`;

    // Update Section Title and Description
    const titleEl = document.getElementById('case-section-title');
    const descEl = document.getElementById('case-section-desc');
    const iconEl = document.getElementById('case-section-icon');
    if (titleEl) titleEl.innerText = sec.title;
    if (descEl) descEl.innerText = sec.description;
    if (iconEl) iconEl.innerText = sec.icon || 'edit_note';

    // Populate Chips
    const chipsContainer = document.getElementById('case-section-chips');
    if (chipsContainer) {
        chipsContainer.innerHTML = (sec.chips || []).map(chip => `
            <button type="button" class="case-chip-btn" onclick="addChipToCurrentInput('${escapeHtml(chip)}')">
                <span>+</span> ${escapeHtml(chip)}
            </button>
        `).join('');
    }

    // Set Textarea Value
    const textarea = document.getElementById('case-section-input');
    if (textarea) {
        textarea.placeholder = sec.placeholder || 'Type or speak your answer here...';
        const saved = recordedCaseAnswers[sec.id];
        textarea.value = saved ? (saved.raw || '') : '';
        textarea.focus();
    }

    // Fetch Adaptive Questions for HPI or Chief Complaint
    fetchAndRenderAdaptiveQuestions(sec.id);
}

function addChipToCurrentInput(chipText) {
    const textarea = document.getElementById('case-section-input');
    if (!textarea) return;
    const cur = textarea.value.trim();
    if (!cur) {
        textarea.value = chipText;
    } else if (!cur.includes(chipText)) {
        textarea.value = `${cur}, ${chipText}`;
    }
}

async function fetchAndRenderAdaptiveQuestions(sectionId) {
    const container = document.getElementById('case-adaptive-container');
    if (!container) return;

    if (sectionId !== 'chief_complaint' && sectionId !== 'hpi') {
        container.style.display = 'none';
        return;
    }

    const cc = (recordedCaseAnswers['chief_complaint'] && recordedCaseAnswers['chief_complaint'].raw) || '';
    if (!cc) {
        container.style.display = 'none';
        return;
    }

    try {
        const res = await fetch(apiUrl(`/api/cases/${activeCaseId}/adaptive-questions`), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chief_complaint: cc, answers: {} })
        });

        if (!res.ok) return;
        const data = await res.json();
        const questions = data.questions || [];

        if (questions.length === 0) {
            container.style.display = 'none';
            return;
        }

        container.style.display = 'block';
        container.innerHTML = `
            <div class="case-adaptive-header">
                <span class="material-symbols-outlined" style="color: #0284c7;">psychology</span>
                <span><strong>Adaptive Follow-up Questions</strong> (Clinically tailored to your symptom)</span>
            </div>
            <div class="case-adaptive-list">
                ${questions.map(q => `
                    <div class="case-adaptive-card">
                        <div class="case-adaptive-q-text">💬 ${escapeHtml(q.question)}</div>
                        <div class="case-adaptive-options">
                            ${(q.options || []).map(opt => `
                                <button type="button" class="case-opt-btn" onclick="addChipToCurrentInput('${escapeHtml(opt)}')">
                                    ${escapeHtml(opt)}
                                </button>
                            `).join('')}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    } catch (e) {
        container.style.display = 'none';
    }
}

async function saveCurrentSectionAndNext() {
    if (!clinicalSectionsData[currentSectionIndex]) return;
    const sec = clinicalSectionsData[currentSectionIndex];
    const textarea = document.getElementById('case-section-input');
    const rawVal = textarea ? textarea.value.trim() : '';

    recordedCaseAnswers[sec.id] = {
        raw: rawVal,
        mode: isRecordingVoice ? 'voice' : 'text'
    };

    // Save to Backend
    if (activeCaseId && rawVal) {
        try {
            await fetch(apiUrl(`/api/cases/${activeCaseId}/save-section`), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    section_id: sec.id,
                    section_title: sec.title,
                    raw_input: rawVal,
                    structured_data: { user_response: rawVal },
                    input_mode: isRecordingVoice ? 'voice' : 'text'
                })
            });
        } catch (e) {
            console.warn('Failed to persist section in real-time:', e);
        }
    }

    if (currentSectionIndex < clinicalSectionsData.length - 1) {
        currentSectionIndex++;
        renderCurrentSection();
    } else {
        // Last section completed -> Move to Review & AYUSH
        showCaseSummaryReview();
    }
}

function navigatePreviousSection() {
    if (currentSectionIndex > 0) {
        currentSectionIndex--;
        renderCurrentSection();
    }
}


// ==============================================================================
// 5. SPEECH-TO-TEXT VOICE INPUT ENGINE (DUAL ENGINE: Browser STT + Server Fallback)
// ==============================================================================
let _caseVoiceBaseText = '';

function toggleVoiceRecording() {
    if (isRecordingVoice) {
        stopVoiceRecording();
    } else {
        startVoiceRecording();
    }
}

async function startVoiceRecording() {
    const micBtn = document.getElementById('case-mic-btn');
    const micStatus = document.getElementById('case-mic-status');
    const textarea = document.getElementById('case-section-input');

    if (!textarea) return;

    _caseVoiceBaseText = textarea.value.trim();
    isRecordingVoice = true;

    // Immediate visual cue
    if (micBtn) micBtn.classList.add('recording-pulse');
    if (micStatus) micStatus.innerHTML = '<span class="rec-dot"></span> Listening... Speak now (auto-stops on pause)';

    const lang = window._selectedLanguage || 'en-IN';
    let targetLangCode = 'en-IN';
    if (lang === 'Hindi' || lang === 'hi-IN') targetLangCode = 'hi-IN';
    else if (lang === 'Telugu' || lang === 'te-IN') targetLangCode = 'te-IN';
    else if (typeof lang === 'string' && lang.includes('-')) targetLangCode = lang;

    if (typeof voiceStartListening !== 'function') {
        console.warn('[CaseTaking] voiceStartListening not yet loaded');
        return;
    }

    await voiceStartListening(
        targetLangCode,
        // onInterim: display live transcription as the patient speaks
        (interimText) => {
            if (textarea) {
                textarea.value = _caseVoiceBaseText ? `${_caseVoiceBaseText} ${interimText}` : interimText;
            }
        },
        // onFinal: write final converted text into textarea
        (finalText) => {
            if (textarea && finalText) {
                textarea.value = _caseVoiceBaseText ? `${_caseVoiceBaseText} ${finalText}` : finalText;
                if (typeof showToast === 'function') {
                    showToast(`✓ Voice converted: "${finalText}"`, 'success');
                }
            }
            stopVoiceRecording();
        },
        // onError: handle microphone permission or recognition notices
        (errorType, errorMsg) => {
            console.warn('[CaseTaking] STT Notice:', errorType, errorMsg);
            if (errorType === 'not-allowed') {
                if (typeof showModalAlert === 'function') {
                    showModalAlert('Microphone permission was blocked. Please click the lock / microphone icon in your browser address bar and select "Allow".', 'Microphone Access Required');
                }
            }
            stopVoiceRecording();
        },
        // onEnd: reset recording UI state
        () => {
            isRecordingVoice = false;
            if (micBtn) micBtn.classList.remove('recording-pulse');
            if (micStatus) micStatus.innerText = 'Click microphone to record with your voice';
        },
        // onStatus: show status updates
        (statusState, statusMsg) => {
            if (micStatus && isRecordingVoice) {
                micStatus.innerHTML = `<span class="rec-dot"></span> ${statusMsg}`;
            }
        },
        // onVolume: live volume indicator meter
        (rms) => {
            if (micStatus && isRecordingVoice) {
                const level = Math.min(8, Math.max(1, Math.round(rms * 90)));
                const bars = ' ▂▃▄▅▆▇█'.slice(0, level);
                micStatus.innerHTML = `<span class="rec-dot"></span> Listening... <span style="color:#0284c7;font-family:monospace;font-weight:700;">${bars}</span> (auto-stops on pause)`;
            }
        }
    );
}

async function stopVoiceRecording() {
    isRecordingVoice = false;
    const micBtn = document.getElementById('case-mic-btn');
    const micStatus = document.getElementById('case-mic-status');

    if (micBtn) micBtn.classList.remove('recording-pulse');
    if (micStatus) micStatus.innerText = 'Click microphone to record with your voice';

    if (typeof voiceStopListening === 'function') {
        await voiceStopListening();
    }
}


// ==============================================================================
// 6. MEDICAL DOCUMENT ATTACHMENT
// ==============================================================================
async function loadAvailableDocumentsForAttachment() {
    const listEl = document.getElementById('case-doc-attach-list');
    if (!listEl) return;

    try {
        const res = await fetch(apiUrl(`/api/reports/patient/${activeCasePatientId}`));
        if (!res.ok) {
            listEl.innerHTML = `<div style="font-size: 0.8rem; color: #94a3b8;">No previous laboratory reports found for this patient.</div>`;
            return;
        }

        const data = await res.json();
        const reports = data.reports || [];
        if (reports.length === 0) {
            listEl.innerHTML = `<div style="font-size: 0.8rem; color: #94a3b8;">No existing reports on file. Upload a new PDF/image below.</div>`;
            return;
        }

        listEl.innerHTML = reports.map(r => `
            <div class="case-doc-item">
                <div>
                    <strong>${escapeHtml(r.report_id)}</strong> &bull; <span style="text-transform: capitalize;">${escapeHtml(r.test_category)}</span>
                    <div style="font-size: 0.72rem; color: #64748b;">Date: ${escapeHtml(r.created_at ? r.created_at.slice(0,10) : 'Recent')}</div>
                </div>
                <button type="button" class="btn-secondary" style="font-size: 0.76rem; padding: 4px 10px;" onclick="attachExistingReportToCase('${r.report_id}', '${r.test_category}')">
                    <span class="material-symbols-outlined" style="font-size: 14px;">attach_file</span> Attach
                </button>
            </div>
        `).join('');
    } catch (e) {
        listEl.innerHTML = `<div style="font-size: 0.8rem; color: #94a3b8;">Documents ready to attach.</div>`;
    }
}

async function attachExistingReportToCase(reportId, category) {
    if (!activeCaseId) return;
    try {
        const res = await fetch(apiUrl(`/api/cases/${activeCaseId}/attach-document`), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                report_id: reportId,
                document_type: 'lab_report',
                filename: `${category.toUpperCase()}_Official_Report_${reportId}.pdf`
            })
        });

        if (res.ok) {
            showToast(`✓ Attached ${reportId} to clinical case!`, 'success');
            attachedCaseDocuments.push({ filename: `${reportId} (${category})` });
            renderAttachedBadges();
        }
    } catch (e) {
        showModalAlert('Could not attach report.', 'Notice');
    }
}

async function handleCaseFileUpload(event) {
    const file = event.target.files[0];
    if (!file || !activeCaseId) return;

    showToast('📄 Uploading & extracting parameters from document...', 'info');
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', 'lab_report');

    try {
        const res = await fetch(apiUrl(`/api/cases/${activeCaseId}/upload-and-attach-file`), {
            method: 'POST',
            body: formData
        });

        if (!res.ok) throw new Error('Upload failed');
        const data = await res.json();
        showToast(`✓ Document attached and parsed: ${file.name}`, 'success');
        attachedCaseDocuments.push({ filename: file.name });
        renderAttachedBadges();
    } catch (e) {
        showModalAlert(`Failed to process document: ${e.message}`, 'Upload Notice');
    }
}

function renderAttachedBadges() {
    const badgeContainer = document.getElementById('case-attached-badges');
    if (!badgeContainer) return;
    if (attachedCaseDocuments.length === 0) {
        badgeContainer.innerHTML = '';
        return;
    }
    badgeContainer.innerHTML = attachedCaseDocuments.map(d => `
        <span class="case-attached-tag">
            <span class="material-symbols-outlined" style="font-size: 14px;">description</span> ${escapeHtml(d.filename)}
        </span>
    `).join('');
}


// ==============================================================================
// 7. SUMMARY SYNTHESIS & REVIEW SCREEN
// ==============================================================================
async function showCaseSummaryReview() {
    document.getElementById('case-step-consent').style.display = 'none';
    document.getElementById('case-step-wizard').style.display = 'none';
    document.getElementById('case-step-summary').style.display = 'block';

    const cc = (recordedCaseAnswers['chief_complaint'] && recordedCaseAnswers['chief_complaint'].raw) || '';
    
    // Read optional AYUSH inputs if filled
    const ayushPrakriti = document.getElementById('ayush-prakriti-select');
    const ayushAgni = document.getElementById('ayush-agni-select');
    const ayushVyayama = document.getElementById('ayush-vyayama-select');
    const ayushSattva = document.getElementById('ayush-sattva-select');
    const ayushLifestyle = document.getElementById('ayush-lifestyle-input');

    const ayushPayload = (ayushPrakriti && ayushPrakriti.value) ? {
        prakriti: ayushPrakriti.value,
        agni_ahara: ayushAgni ? ayushAgni.value : '',
        vyayama_shakti: ayushVyayama ? ayushVyayama.value : '',
        sattva: ayushSattva ? ayushSattva.value : '',
        ahara_vihara: ayushLifestyle ? ayushLifestyle.value : ''
    } : null;

    try {
        const res = await fetch(apiUrl(`/api/cases/${activeCaseId}/generate-summary`), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                chief_complaint: cc,
                ayush_data: ayushPayload
            })
        });

        if (!res.ok) throw new Error('Could not generate summary');
        const data = await res.json();
        renderSummarySheet(data.summary);
    } catch (e) {
        showModalAlert(`Error synthesizing case sheet: ${e.message}`, 'Notice');
    }
}

function renderSummarySheet(summary) {
    const container = document.getElementById('case-summary-content');
    if (!container || !summary) return;

    const hdr = summary.header || {};
    const secs = summary.sections || {};
    const redFlags = summary.red_flags || [];
    const docs = summary.attached_documents || [];
    const ayush = summary.ayush_profile || {};
    const triageLevel = (summary.triage_level || 'routine').toLowerCase();

    let triageBadgeClass = 'triage-routine';
    let triageIcon = 'check_circle';
    let triageLabel = 'ROUTINE (Standard Consultation)';
    if (triageLevel === 'emergency' || triageLevel === 'critical') {
        triageBadgeClass = 'triage-emergency';
        triageIcon = 'crisis_alert';
        triageLabel = 'EMERGENCY / STAT (Immediate Attention)';
    } else if (triageLevel === 'urgent') {
        triageBadgeClass = 'triage-urgent';
        triageIcon = 'warning';
        triageLabel = 'URGENT (Priority Clinical Triage)';
    }

    let redFlagHtml = '';
    if (redFlags.length > 0) {
        redFlagHtml = `
            <div class="case-red-flag-banner">
                <span class="material-symbols-outlined alert-icon">warning</span>
                <div>
                    <div class="alert-title">CRITICAL TRIAGE ALERT &bull; POTENTIAL EMERGENCY INDICATOR</div>
                    <div class="alert-list">
                        ${redFlags.map(f => `<div>&bull; ${escapeHtml(f.message || f)}</div>`).join('')}
                    </div>
                    <div style="font-size: 0.74rem; opacity: 0.9; margin-top: 6px; font-weight: 500;">
                        * Automated clinical decision-support triage alert for attending healthcare personnel.
                    </div>
                </div>
            </div>
        `;
    }

    const hasAllergies = secs.allergy_history && !secs.allergy_history.includes('NKDA') && !secs.allergy_history.toLowerCase().includes('no known');

    container.innerHTML = `
        ${redFlagHtml}

        <div class="case-sheet-card">
            <!-- Official Header Letterhead -->
            <div class="case-sheet-header">
                <div class="case-sheet-header-left">
                    <div class="case-sheet-badge">
                        <span class="material-symbols-outlined" style="font-size: 14px;">verified</span> OFFICIAL CLINICAL CASE SHEET &bull; SIH PATIENT INTAKE
                    </div>
                    <h2 class="case-sheet-title">PATIENT CLINICAL CASE SHEET</h2>
                    <div class="case-sheet-subtitle">MEDLENS AI x Medicover Clinical Precision Healthcare Platform</div>
                </div>
                <div class="case-sheet-header-right">
                    <div class="case-meta-item">
                        <span class="meta-lbl">Case ID:</span>
                        <span class="meta-val-code">${escapeHtml(hdr.case_id || activeCaseId)}</span>
                    </div>
                    <div class="case-meta-item">
                        <span class="meta-lbl">Generated:</span>
                        <span class="meta-val">${escapeHtml(hdr.generated_at || 'Just now')}</span>
                    </div>
                    <div class="case-meta-item">
                        <span class="meta-lbl">ABHA / ABDM:</span>
                        <span class="meta-val-abha">${escapeHtml(hdr.abha_id || '91-5423-4671-3173')}</span>
                    </div>
                </div>
            </div>

            <!-- Patient Demographics Info Bar -->
            <div class="case-sheet-patient-bar">
                <div class="patient-bar-col">
                    <div class="bar-lbl"><span class="material-symbols-outlined">person</span> Patient Demographics</div>
                    <div class="bar-val-main">${escapeHtml(hdr.patient_name || 'Outpatient')} <span class="bar-sub-id">(${escapeHtml(hdr.patient_id || activeCasePatientId)})</span></div>
                    <div class="bar-val-sub">Age: <strong>${escapeHtml(hdr.age_gender ? hdr.age_gender.split('/')[0].trim() : '—')}</strong> &bull; Gender: <strong>${escapeHtml(hdr.age_gender ? (hdr.age_gender.split('/')[1] || '').trim() : '—')}</strong></div>
                </div>

                <div class="patient-bar-col">
                    <div class="bar-lbl"><span class="material-symbols-outlined">health_and_safety</span> Health ID (ABHA)</div>
                    <div class="bar-val-main" style="font-family: var(--font-mono); color: #00397e; font-size: 0.92rem;">
                        ${escapeHtml(hdr.abha_id || '91-5423-4671-3173')}
                    </div>
                    <div class="bar-val-sub" style="color: #059669; font-weight: 700;">✓ ABDM Consent Verified</div>
                </div>

                <div class="patient-bar-col">
                    <div class="bar-lbl"><span class="material-symbols-outlined">emergency</span> Clinical Triage Level</div>
                    <div>
                        <span class="case-triage-pill ${triageBadgeClass}">
                            <span class="material-symbols-outlined" style="font-size: 14px;">${triageIcon}</span> ${triageLabel}
                        </span>
                    </div>
                    <div class="bar-val-sub">Assigned by rule-based triage</div>
                </div>
            </div>

            <!-- 10 Structured Clinical History Sections (2-Column Grid) -->
            <div class="case-sheet-body">
                <div class="case-sheet-grid-title">
                    <span class="material-symbols-outlined" style="color: #00397e; font-size: 18px;">format_list_bulleted</span>
                    <span>10-SECTION STRUCTURED CLINICAL HISTORY</span>
                </div>

                <div class="case-sheet-sections-grid">
                    <div class="case-sec-box sec-accent-primary">
                        <div class="case-sec-lbl">
                            <span class="sec-num-badge">1</span>
                            <span>CHIEF COMPLAINT (CC)</span>
                        </div>
                        <div class="case-sec-val">${escapeHtml(secs.chief_complaint || 'None reported')}</div>
                    </div>

                    <div class="case-sec-box sec-accent-primary">
                        <div class="case-sec-lbl">
                            <span class="sec-num-badge">2</span>
                            <span>HISTORY OF PRESENT ILLNESS (HPI)</span>
                        </div>
                        <div class="case-sec-val">${escapeHtml(secs.hpi || 'None reported')}</div>
                    </div>

                    <div class="case-sec-box">
                        <div class="case-sec-lbl">
                            <span class="sec-num-badge">3</span>
                            <span>PAST MEDICAL HISTORY (PMHx)</span>
                        </div>
                        <div class="case-sec-val">${escapeHtml(secs.past_medical || 'None reported')}</div>
                    </div>

                    <div class="case-sec-box">
                        <div class="case-sec-lbl">
                            <span class="sec-num-badge">4</span>
                            <span>PAST SURGICAL HISTORY (PSHx)</span>
                        </div>
                        <div class="case-sec-val">${escapeHtml(secs.past_surgical || 'None reported')}</div>
                    </div>

                    <div class="case-sec-box">
                        <div class="case-sec-lbl">
                            <span class="sec-num-badge">5</span>
                            <span>DRUG &amp; MEDICATION HISTORY (Rx)</span>
                        </div>
                        <div class="case-sec-val">${escapeHtml(secs.drug_history || 'No current routine medications')}</div>
                    </div>

                    <div class="case-sec-box ${hasAllergies ? 'sec-accent-danger' : 'sec-accent-success'}">
                        <div class="case-sec-lbl">
                            <span class="sec-num-badge ${hasAllergies ? 'badge-danger' : 'badge-success'}">6</span>
                            <span>ALLERGIES &amp; ADVERSE REACTIONS</span>
                        </div>
                        <div class="case-sec-val ${hasAllergies ? 'text-danger-bold' : ''}">
                            ${hasAllergies ? '⚠️ ' : '✓ '}${escapeHtml(secs.allergy_history || 'No Known Drug Allergies (NKDA)')}
                        </div>
                    </div>

                    <div class="case-sec-box">
                        <div class="case-sec-lbl">
                            <span class="sec-num-badge">7</span>
                            <span>FAMILY HISTORY (FHx)</span>
                        </div>
                        <div class="case-sec-val">${escapeHtml(secs.family_history || 'Non-contributory / No significant hereditary illness')}</div>
                    </div>

                    <div class="case-sec-box">
                        <div class="case-sec-lbl">
                            <span class="sec-num-badge">8</span>
                            <span>PERSONAL &amp; SOCIAL HISTORY (SHx)</span>
                        </div>
                        <div class="case-sec-val">${escapeHtml(secs.personal_history || 'Standard routine')}</div>
                    </div>

                    <div class="case-sec-box">
                        <div class="case-sec-lbl">
                            <span class="sec-num-badge">9</span>
                            <span>REVIEW OF SYSTEMS (ROS)</span>
                        </div>
                        <div class="case-sec-val">${escapeHtml(secs.ros || 'Systemic review non-contributory')}</div>
                    </div>

                    <div class="case-sec-box">
                        <div class="case-sec-lbl">
                            <span class="sec-num-badge">10</span>
                            <span>PREVIOUS INVESTIGATIONS &amp; LABS</span>
                        </div>
                        <div class="case-sec-val">${escapeHtml(secs.previous_investigations || 'No prior investigations attached')}</div>
                    </div>
                </div>

                <!-- AYUSH Constitutional Profile (if filled) -->
                ${ayush.has_ayush ? `
                    <div class="case-ayush-panel">
                        <div class="ayush-panel-header">
                            <span class="material-symbols-outlined" style="color: #15803d;">spa</span>
                            <span class="ayush-panel-title">OPTIONAL AYUSH CONSTITUTIONAL &amp; HOLISTIC PROFILE</span>
                        </div>
                        <div class="ayush-grid">
                            <div class="ayush-tile"><strong>Prakriti:</strong> <span>${escapeHtml(ayush.prakriti || '—')}</span></div>
                            <div class="ayush-tile"><strong>Agni / Ahara:</strong> <span>${escapeHtml(ayush.agni_ahara || '—')}</span></div>
                            <div class="ayush-tile"><strong>Vyayama Shakti:</strong> <span>${escapeHtml(ayush.vyayama_shakti || '—')}</span></div>
                            <div class="ayush-tile"><strong>Sattva:</strong> <span>${escapeHtml(ayush.sattva || '—')}</span></div>
                        </div>
                        ${ayush.ahara_vihara ? `<div class="ayush-lifestyle-note"><strong>Lifestyle &amp; Diet (Ahara/Vihara):</strong> ${escapeHtml(ayush.ahara_vihara)}</div>` : ''}
                    </div>
                ` : ''}

                <!-- Attached Medical Documents (if any) -->
                ${docs.length > 0 ? `
                    <div class="case-docs-panel">
                        <div class="docs-panel-header">
                            <span class="material-symbols-outlined" style="color: #0284c7;">attach_file</span>
                            <span>ATTACHED MEDICAL DOCUMENTS &amp; EXTRACTED PARAMETERS</span>
                        </div>
                        <div class="docs-grid">
                            ${docs.map(d => `
                                <div class="case-doc-tile">
                                    <div class="doc-tile-title">
                                        <span class="material-symbols-outlined" style="font-size: 16px; color: #0284c7;">description</span>
                                        <strong>${escapeHtml(d.filename)}</strong>
                                        <span class="doc-tile-type">${escapeHtml(d.type)}</span>
                                    </div>
                                    ${d.key_parameters && d.key_parameters.length > 0 ? `
                                        <div class="doc-params-wrap">
                                            ${d.key_parameters.map(p => `<span class="doc-param-chip">${escapeHtml(p)}</span>`).join('')}
                                        </div>
                                    ` : ''}
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}

                <!-- Official Notice / Safe Phrasing -->
                <div class="case-disclaimer-box">
                    <span class="material-symbols-outlined" style="font-size: 18px; color: #0284c7;">clinical_notes</span>
                    <span><strong>CLINICAL INTAKE NOTICE:</strong> ${escapeHtml(summary.disclaimer || 'This structured case summary is compiled from patient-reported history and preliminary diagnostic records for attending physician review. It does not replace independent clinical examination.')}</span>
                </div>

                <!-- Action Toolbar -->
                <div class="case-sheet-actions">
                    <button type="button" class="btn-secondary" onclick="window.print()" style="display: inline-flex; align-items: center; gap: 6px;">
                        <span class="material-symbols-outlined" style="font-size: 16px;">print</span> Print Case Sheet
                    </button>
                    <button type="button" class="btn-primary" onclick="finishCaseTaking()" style="background: linear-gradient(135deg, #00397e, #1a50a0); display: inline-flex; align-items: center; gap: 6px; padding: 10px 22px;">
                        <span class="material-symbols-outlined" style="font-size: 16px;">check_circle</span> Save &amp; Finish Intake
                    </button>
                </div>
            </div>
        </div>
    `;
}

function finishCaseTaking() {
    showToast('✓ Clinical Case Sheet recorded successfully!', 'success');
    switchView('patient');
}


// ==============================================================================
// 8. DOCTOR CONSOLE CASE REVIEW BOARD
// ==============================================================================
async function loadDoctorClinicalCases() {
    const listContainer = document.getElementById('doctor-case-list');
    if (!listContainer) return;

    listContainer.innerHTML = '<div style="padding: 20px; text-align: center; color: #64748b;">Loading clinical cases...</div>';

    try {
        const res = await fetch(apiUrl('/api/cases/all/list'));
        if (!res.ok) throw new Error('Could not fetch cases');
        const data = await res.json();
        const cases = data.cases || [];

        if (cases.length === 0) {
            listContainer.innerHTML = '<div style="padding: 20px; text-align: center; color: #94a3b8;">No clinical cases submitted yet.</div>';
            return;
        }

        listContainer.innerHTML = cases.map(c => `
            <div class="doctor-case-card ${c.triage_urgency === 'emergency' ? 'urgent-border' : ''}">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 10px;">
                    <div>
                        <div style="display: flex; align-items: center; gap: 6px;">
                            <span class="badge-${(c.triage_urgency || 'routine').toLowerCase()}">${escapeHtml((c.triage_urgency || 'ROUTINE').toUpperCase())}</span>
                            <strong style="color: #00397e; font-size: 0.95rem;">${escapeHtml(c.patient_name || c.patient_id)}</strong>
                            <span style="font-size: 0.78rem; color: #64748b;">(${escapeHtml(c.patient_id)}, ${c.patient_age || '—'}Y)</span>
                        </div>
                        <div style="font-size: 0.84rem; color: #334155; margin-top: 4px;">
                            <strong>Chief Complaint:</strong> ${escapeHtml(c.chief_complaint || 'Clinical review')}
                        </div>
                        <div style="font-size: 0.74rem; color: #94a3b8; margin-top: 4px;">
                            Case ID: <strong>${c.case_id}</strong> &bull; Status: <span style="text-transform: capitalize; font-weight: 700;">${escapeHtml(c.status)}</span> &bull; Submitted: ${c.created_at ? c.created_at.slice(0,16).replace('T', ' ') : 'Recent'}
                        </div>
                    </div>
                    <button type="button" class="btn-primary" style="font-size: 0.8rem; padding: 6px 12px;" onclick="openDoctorCaseReviewModal('${c.case_id}')">
                        <span class="material-symbols-outlined" style="font-size: 16px;">rate_review</span> Review &amp; Confirm
                    </button>
                </div>
            </div>
        `).join('');
    } catch (e) {
        listContainer.innerHTML = `<div style="padding: 20px; color: #ef4444;">Failed to load cases: ${e.message}</div>`;
    }
}

let activeDoctorReviewCaseId = null;

async function openDoctorCaseReviewModal(caseId) {
    activeDoctorReviewCaseId = caseId;
    const modal = document.getElementById('modal-doctor-case-review');
    const content = document.getElementById('doc-case-review-body');
    if (!modal || !content) return;

    content.innerHTML = '<div style="padding: 30px; text-align: center;">Loading full case history...</div>';
    modal.style.display = 'flex';

    try {
        const res = await fetch(apiUrl(`/api/cases/${caseId}`));
        if (!res.ok) throw new Error('Could not load case details');
        const caseData = await res.json();
        const sum = caseData.summary || {};
        const secs = sum.sections || {};

        content.innerHTML = `
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px 18px; margin-bottom: 16px; display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; font-size: 0.84rem;">
                <div>
                    <div style="font-size: 0.72rem; font-weight: 800; color: #64748b; text-transform: uppercase;">Patient Name &amp; ID</div>
                    <strong style="color: #00397e; font-size: 0.96rem;">${escapeHtml(caseData.patient_name || caseData.patient_id)}</strong>
                    <div style="color: #64748b; font-size: 0.78rem;">ID: ${escapeHtml(caseData.patient_id)} &bull; ${caseData.patient_age || '—'}Y / ${caseData.patient_gender || '—'}</div>
                </div>
                <div>
                    <div style="font-size: 0.72rem; font-weight: 800; color: #64748b; text-transform: uppercase;">ABHA ID / ABDM</div>
                    <div style="font-family: var(--font-mono); color: #0284c7; font-weight: 700; font-size: 0.88rem;">${escapeHtml(caseData.abha_id || '91-5423-4671-3173')}</div>
                    <div style="color: #059669; font-size: 0.76rem; font-weight: 700;">✓ Digital Consent Verified</div>
                </div>
                <div>
                    <div style="font-size: 0.72rem; font-weight: 800; color: #64748b; text-transform: uppercase;">Triage Priority</div>
                    <div style="margin-top: 2px;">
                        <span class="case-triage-pill triage-${(caseData.triage_urgency || 'routine').toLowerCase()}">
                            ${escapeHtml((caseData.triage_urgency || 'ROUTINE').toUpperCase())}
                        </span>
                    </div>
                </div>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.82rem;">
                <div class="case-sec-box" style="margin: 0; padding: 10px 12px;">
                    <div class="case-sec-lbl" style="font-size: 0.74rem;"><span class="sec-num-badge" style="width: 16px; height: 16px; font-size: 0.65rem;">1</span> Chief Complaint</div>
                    <div style="color: #334155; font-weight: 600;">${escapeHtml(secs.chief_complaint || caseData.chief_complaint || 'None')}</div>
                </div>
                <div class="case-sec-box" style="margin: 0; padding: 10px 12px;">
                    <div class="case-sec-lbl" style="font-size: 0.74rem;"><span class="sec-num-badge" style="width: 16px; height: 16px; font-size: 0.65rem;">2</span> HPI</div>
                    <div style="color: #334155;">${escapeHtml(secs.hpi || 'None')}</div>
                </div>
                <div class="case-sec-box" style="margin: 0; padding: 10px 12px;">
                    <div class="case-sec-lbl" style="font-size: 0.74rem;"><span class="sec-num-badge" style="width: 16px; height: 16px; font-size: 0.65rem;">3</span> Past Medical</div>
                    <div style="color: #334155;">${escapeHtml(secs.past_medical || 'None')}</div>
                </div>
                <div class="case-sec-box" style="margin: 0; padding: 10px 12px;">
                    <div class="case-sec-lbl" style="font-size: 0.74rem;"><span class="sec-num-badge" style="width: 16px; height: 16px; font-size: 0.65rem;">4</span> Past Surgical</div>
                    <div style="color: #334155;">${escapeHtml(secs.past_surgical || 'None')}</div>
                </div>
                <div class="case-sec-box" style="margin: 0; padding: 10px 12px;">
                    <div class="case-sec-lbl" style="font-size: 0.74rem;"><span class="sec-num-badge" style="width: 16px; height: 16px; font-size: 0.65rem;">5</span> Medications</div>
                    <div style="color: #334155;">${escapeHtml(secs.drug_history || 'None')}</div>
                </div>
                <div class="case-sec-box" style="margin: 0; padding: 10px 12px; border-left-color: ${secs.allergy_history && !secs.allergy_history.includes('NKDA') ? '#ef4444' : '#10b981'};">
                    <div class="case-sec-lbl" style="font-size: 0.74rem;"><span class="sec-num-badge" style="width: 16px; height: 16px; font-size: 0.65rem;">6</span> Allergies</div>
                    <div style="color: ${secs.allergy_history && !secs.allergy_history.includes('NKDA') ? '#b91c1c' : '#047857'}; font-weight: 700;">
                        ${escapeHtml(secs.allergy_history || 'No Known Drug Allergies (NKDA)')}
                    </div>
                </div>
            </div>

            <div style="margin-top: 16px;">
                <label style="font-size: 0.84rem; font-weight: 800; color: #00397e; display: flex; align-items: center; gap: 6px; margin-bottom: 6px;">
                    <span class="material-symbols-outlined" style="font-size: 18px; color: #0284c7;">edit_note</span> Attending Physician Clinical Notes &amp; Verification *
                </label>
                <textarea id="doctor-case-notes" class="search-input" rows="3" placeholder="Enter clinical assessment, differential diagnosis, or advised prescription/investigation orders..." style="width: 100%; border: 1.5px solid #bfdbfe; border-radius: 8px; padding: 10px 12px; font-size: 0.85rem; line-height: 1.4;">${escapeHtml(caseData.doctor_notes || '')}</textarea>
            </div>
        `;
    } catch (e) {
        content.innerHTML = `<div style="padding: 20px; color: #ef4444;">Error: ${e.message}</div>`;
    }
}

function closeDoctorCaseReviewModal() {
    const modal = document.getElementById('modal-doctor-case-review');
    if (modal) modal.style.display = 'none';
    activeDoctorReviewCaseId = null;
}

async function submitDoctorCaseSignoff() {
    if (!activeDoctorReviewCaseId) return;
    const notesEl = document.getElementById('doctor-case-notes');
    const notes = notesEl ? notesEl.value.trim() : '';

    try {
        const res = await fetch(apiUrl(`/api/cases/${activeDoctorReviewCaseId}/doctor-review`), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                doctor_id: (currentAuth && currentAuth.patientName) || 'Dr. Medicover Clinical Desk',
                doctor_notes: notes || 'Clinical case history verified and confirmed.',
                status: 'confirmed'
            })
        });

        if (res.ok) {
            showToast('✓ Clinical Case confirmed and signed off by physician!', 'success');
            closeDoctorCaseReviewModal();
            loadDoctorClinicalCases();
        }
    } catch (e) {
        showModalAlert('Failed to submit doctor sign-off.', 'Notice');
    }
}
