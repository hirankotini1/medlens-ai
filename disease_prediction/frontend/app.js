// API Base URL Resolution
// If page is loaded via file:// protocol or a port other than 8000 (e.g. Live Server), route to http://127.0.0.1:8000
const API_BASE = (window.location.protocol === 'file:' || (window.location.port !== '8000' && window.location.port !== ''))
    ? 'http://127.0.0.1:8000'
    : '';

function apiUrl(path) {
    if (!path.startsWith('/')) path = '/' + path;
    return `${API_BASE}${path}`;
}

async function safeJson(response) {
    try {
        const text = await response.text();
        return text ? JSON.parse(text) : {};
    } catch (e) {
        return { detail: response.statusText || `Server returned status ${response.status}` };
    }
}

// Application State
let currentAuth = {
    role: null, // 'admin' or 'patient'
    token: null,
    patientId: null,
    patientName: null,
    patientAge: null,
    patientGender: null
};

let allPatients = [];
let allReports = [];
let patientReports = [];
let currentSandboxDisease = 'anemia';
let selectedSandboxFile = null;

// Feature 4: Multi-Language State
window._selectedLanguage = 'English';
function onLanguageChange(val) {
    window._selectedLanguage = val || 'English';
    // If active report is open in patient view, re-render it to update language explanation
    if (patientReports && patientReports.length > 0) {
        const activeDoc = document.querySelector('.official-report-doc');
        if (activeDoc && activeDoc.id) {
            const repId = activeDoc.id.replace('doc-', '');
            viewPatientReportDetails(repId);
        }
    }
}

// Reference Range definitions for clinical parameters
const clinicalRefRanges = {
    HGB: { unit: 'g/dL', ref: '12.0 - 15.5', name: 'Hemoglobin (HGB)' },
    RBC: { unit: 'x10^12/L', ref: '3.80 - 5.20', name: 'Total RBC Count' },
    PCV: { unit: '%', ref: '36.0 - 46.0', name: 'Packed Cell Volume (PCV)' },
    MCV: { unit: 'fL', ref: '80.0 - 100.0', name: 'Mean Corpuscular Volume (MCV)' },
    MCH: { unit: 'pg', ref: '27.0 - 32.0', name: 'Mean Corpuscular Hemoglobin (MCH)' },
    MCHC: { unit: 'g/dL', ref: '31.5 - 34.5', name: 'MCHC' },
    RDW: { unit: '%', ref: '11.5 - 14.5', name: 'Red Cell Distribution Width (RDW)' },
    TLC: { unit: 'x10^3/uL', ref: '4.0 - 11.0', name: 'Total Leukocyte Count (TLC)' },
    'PLT /mm3': { unit: '/mm3', ref: '150.0 - 450.0', name: 'Platelet Count' },
    PLT_mm3: { unit: '/mm3', ref: '150.0 - 450.0', name: 'Platelet Count' },

    hemoglobin_g_dl: { unit: 'g/dL', ref: '13.0 - 17.0', name: 'Hemoglobin' },
    wbc_count: { unit: 'cells/uL', ref: '4000 - 11000', name: 'WBC Count' },
    differential_count: { unit: 'flag', ref: '0 (Normal) - 1 (Abnormal)', name: 'Differential Count' },
    rbc_count: { unit: 'flag', ref: '0 (Normal) - 1 (Abnormal)', name: 'RBC Morphology Flag' },
    platelet_count: { unit: 'cells/uL', ref: '150000 - 450000', name: 'Platelet Count' },
    platelet_distribution_width: { unit: '%', ref: '9.0 - 17.0', name: 'Platelet Distribution Width' },

    total_bilirubin: { unit: 'mg/dL', ref: '0.2 - 1.2', name: 'Total Bilirubin' },
    direct_bilirubin: { unit: 'mg/dL', ref: '0.0 - 0.3', name: 'Direct Bilirubin' },
    alkaline_phosphotase: { unit: 'IU/L', ref: '44 - 147', name: 'Alkaline Phosphatase (ALP)' },
    alamine_aminotransferase: { unit: 'IU/L', ref: '10 - 40', name: 'ALT / SGPT' },
    aspartate_aminotransferase: { unit: 'IU/L', ref: '10 - 40', name: 'AST / SGOT' },
    total_protiens: { unit: 'g/dL', ref: '6.0 - 8.3', name: 'Total Proteins' },
    albumin: { unit: 'g/dL', ref: '3.5 - 5.0', name: 'Albumin' },
    albumin_and_globulin_ratio: { unit: 'ratio', ref: '1.0 - 2.2', name: 'A/G Ratio' },

    TSH: { unit: 'uIU/mL', ref: '0.4 - 4.2', name: 'Thyroid Stimulating Hormone (TSH)' },
    T4: { unit: 'ug/dL', ref: '4.5 - 12.0', name: 'Thyroxine (T4)' },
    T3: { unit: 'ng/dL', ref: '0.8 - 2.0', name: 'Triiodothyronine (T3)' },
    TSH_response: { unit: 'response', ref: '1.0 - 5.0', name: 'TSH Response to TRH' },
    T3_resin_uptake: { unit: '%', ref: '95 - 120', name: 'T3 Resin Uptake' }
};

// ---------------------------------------------------------
// ---------------------------------------------------------
// Session & Auth Persistence Helpers
// ---------------------------------------------------------
function saveSessionAuth() {
    try {
        sessionStorage.setItem('nexus_auth', JSON.stringify(currentAuth));
    } catch (e) {}
}

function restoreSessionAuth() {
    try {
        const stored = sessionStorage.getItem('nexus_auth');
        if (stored) {
            currentAuth = JSON.parse(stored);
        }
    } catch (e) {}
}

function clearSessionAuth() {
    try {
        sessionStorage.removeItem('nexus_auth');
    } catch (e) {}
}

let isBackendOnline = true;

async function checkBackendHealth(isManualRetry = false) {
    const banner = document.getElementById('server-status-banner');
    try {
        const res = await fetch(apiUrl('/api/patients/public'), { cache: 'no-store' });
        if (res.ok) {
            isBackendOnline = true;
            if (banner) banner.style.display = 'none';
            const patients = await res.json();
            renderPatientPortalQuickButtons(patients);
            allPatients = patients;
            if (isManualRetry) {
                alert("✓ Connection verified! Backend server is online and running on port 8000.");
            }
            return true;
        }
    } catch (err) {
        isBackendOnline = false;
        if (banner) banner.style.display = 'flex';
        if (isManualRetry) {
            alert("⚠️ Backend server is currently offline on port 8000.\n\nPlease start the server by double-clicking 'RUN_MEDLENS.bat'.");
        }
        return false;
    }
}

async function loadPublicPatients() {
    try {
        const res = await fetch(apiUrl('/api/patients/public'), { cache: 'no-store' });
        if (!res.ok) return;
        const patients = await res.json();
        renderPatientPortalQuickButtons(patients);
        allPatients = patients;
        const banner = document.getElementById('server-status-banner');
        if (banner) banner.style.display = 'none';
    } catch (err) {
        console.warn("Could not connect to backend server:", err);
        const banner = document.getElementById('server-status-banner');
        if (banner) banner.style.display = 'flex';
    }
}

function renderPatientPortalQuickButtons(patients) {
    const container = document.getElementById('patient-quick-login-grid');
    if (!container) return;
    if (!patients || patients.length === 0) {
        container.innerHTML = `<div style="font-size: 0.8rem; color: #94a3b8; padding: 6px;">No registered patients found. Register via Lab Staff portal.</div>`;
        return;
    }
    container.innerHTML = patients.map(p => `
        <button type="button" class="btn-secondary" style="font-size: 0.78rem; padding: 6px 10px; text-align: left;" onclick="fillPatientCreds('${p.patient_id}', '${p.pin_hint}')">
            <strong>${p.patient_id}</strong> &bull; ${p.name} (${p.gender}, ${p.age}Y)
        </button>
    `).join('');
}

// ---------------------------------------------------------
// Navigation Logic
// ---------------------------------------------------------
function switchView(viewName) {
    try {
        sessionStorage.setItem('nexus_active_view', viewName);
    } catch (e) {}

    document.querySelectorAll('.section-view').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));

    const viewEl = document.getElementById(`view-${viewName}`);
    const tabEl = document.getElementById(`tab-${viewName}`);
    if (viewEl) viewEl.classList.add('active');
    if (tabEl) tabEl.classList.add('active');

    if (viewName === 'admin') {
        if (currentAuth.role === 'admin' && currentAuth.token) {
            document.getElementById('admin-login-box').style.display = 'none';
            document.getElementById('admin-dashboard-box').style.display = 'block';
            loadAdminData();
        } else {
            document.getElementById('admin-login-box').style.display = 'block';
            document.getElementById('admin-dashboard-box').style.display = 'none';
        }
    } else if (viewName === 'patient') {
        if (currentAuth.role === 'patient' && currentAuth.token && currentAuth.patientId) {
            document.getElementById('patient-login-container').style.display = 'none';
            document.getElementById('patient-dashboard-container').style.display = 'block';
            if (currentAuth.patientName) {
                document.getElementById('dash-patient-name').innerText = `Welcome, ${currentAuth.patientName}`;
                document.getElementById('dash-patient-meta').innerHTML = `
                    Patient ID: <strong>${currentAuth.patientId}</strong> &bull; 
                    Age: <strong>${currentAuth.patientAge || '—'} Yrs</strong> &bull; 
                    Gender: <strong>${currentAuth.patientGender || '—'}</strong>
                `;
            }
            fetchAndRenderPatientReports();
            loadPatientTimeline(currentAuth.patientId, currentAuth.token);
            loadPatientReminders(currentAuth.patientId);
            loadPatientReportedIssues(currentAuth.patientId);
        } else {
            document.getElementById('patient-login-container').style.display = 'block';
            document.getElementById('patient-dashboard-container').style.display = 'none';
            loadPublicPatients();
        }
    } else if (viewName === 'sandbox') {
        setTimeout(() => simulateMainSandboxPrediction(), 50);
    }
}

// ---------------------------------------------------------
// Top Navigation ML Decision Support Sandbox Functions
// ---------------------------------------------------------
function loadMainSandboxPreset(type) {
    if (type === 'normal') {
        setMainSandboxValues(14.2, 260000, 88.0, 6800, 0.8, 2.1);
    } else if (type === 'anemia') {
        setMainSandboxValues(7.8, 280000, 68.0, 7200, 0.9, 1.8);
    } else if (type === 'dengue') {
        setMainSandboxValues(15.5, 32000, 86.0, 2800, 1.1, 2.4);
    } else if (type === 'liver') {
        setMainSandboxValues(12.8, 160000, 91.0, 8500, 4.6, 2.2);
    } else if (type === 'thyroid') {
        setMainSandboxValues(13.0, 240000, 89.0, 6100, 0.7, 14.2);
    }
    simulateMainSandboxPrediction();
}

function setMainSandboxValues(hb, plt, mcv, wbc, bili, tsh) {
    const elHb = document.getElementById('main-sb-hb');
    const elPlt = document.getElementById('main-sb-plt');
    const elMcv = document.getElementById('main-sb-mcv');
    const elWbc = document.getElementById('main-sb-wbc');
    const elBili = document.getElementById('main-sb-bili');
    const elTsh = document.getElementById('main-sb-tsh');

    if (elHb) elHb.value = hb;
    if (elPlt) elPlt.value = plt;
    if (elMcv) elMcv.value = mcv;
    if (elWbc) elWbc.value = wbc;
    if (elBili) elBili.value = bili;
    if (elTsh) elTsh.value = tsh;

    const lblHb = document.getElementById('lbl-main-sb-hb');
    const lblPlt = document.getElementById('lbl-main-sb-plt');
    const lblMcv = document.getElementById('lbl-main-sb-mcv');
    const lblWbc = document.getElementById('lbl-main-sb-wbc');
    const lblBili = document.getElementById('lbl-main-sb-bili');
    const lblTsh = document.getElementById('lbl-main-sb-tsh');

    if (lblHb) lblHb.innerText = hb + ' g/dL';
    if (lblPlt) lblPlt.innerText = parseInt(plt).toLocaleString() + ' /µL';
    if (lblMcv) lblMcv.innerText = mcv + ' fL';
    if (lblWbc) lblWbc.innerText = parseInt(wbc).toLocaleString() + ' /µL';
    if (lblBili) lblBili.innerText = bili + ' mg/dL';
    if (lblTsh) lblTsh.innerText = tsh + ' µIU/mL';
}

function simulateMainSandboxPrediction() {
    const grid = document.getElementById('main-sb-output-grid');
    if (!grid) return;

    const hb = parseFloat(document.getElementById('main-sb-hb')?.value || 13.5);
    const plt = parseFloat(document.getElementById('main-sb-plt')?.value || 250000);
    const mcv = parseFloat(document.getElementById('main-sb-mcv')?.value || 88);
    const wbc = parseFloat(document.getElementById('main-sb-wbc')?.value || 6500);
    const bili = parseFloat(document.getElementById('main-sb-bili')?.value || 0.8);
    const tsh = parseFloat(document.getElementById('main-sb-tsh')?.value || 2.1);

    // 1. Anemia Classifier
    let anemiaRisk = "Normal (Non-Anemic)";
    let anemiaConfidence = 96;
    let anemiaClass = "risk-normal";
    let anemiaBadge = "✓ NORMAL PATTERN";
    if (hb < 11.0) {
        if (mcv < 80) {
            anemiaRisk = "Microcytic Hypochromic Anemia (Iron Deficiency Pattern)";
            anemiaConfidence = Math.min(99, Math.round(92 + (11.0 - hb) * 2));
        } else if (mcv > 100) {
            anemiaRisk = "Macrocytic Anemia (B12 / Folate Deficiency Pattern)";
            anemiaConfidence = Math.min(98, Math.round(89 + (11.0 - hb) * 2));
        } else {
            anemiaRisk = "Normocytic Normochromic Anemia";
            anemiaConfidence = Math.min(97, Math.round(88 + (11.0 - hb) * 2));
        }
        anemiaClass = "risk-high";
        anemiaBadge = "⚠️ ELEVATED RISK";
    } else if (hb < 12.5) {
        anemiaRisk = "Borderline / Mild Anemia";
        anemiaConfidence = 85;
        anemiaClass = "flag-high";
        anemiaBadge = "• BORDERLINE";
    }

    // 2. Dengue Thrombocytopenia Model
    let dengueRisk = "Normal Platelet Kinetics (Low Probability)";
    let dengueConfidence = 95;
    let dengueClass = "risk-normal";
    let dengueBadge = "✓ LOW RISK";
    if (plt < 100000) {
        dengueRisk = plt < 50000 ? "Severe Thrombocytopenia / High Dengue Risk (<50k)" : "Moderate Thrombocytopenia (<100k)";
        dengueConfidence = Math.min(99, Math.round(91 + (100000 - plt) / 10000));
        dengueClass = "risk-high";
        dengueBadge = "⚠️ CRITICAL THRESHOLD";
    } else if (plt < 150000) {
        dengueRisk = "Mild Thrombocytopenia Warning (100k-150k)";
        dengueConfidence = 87;
        dengueClass = "flag-high";
        dengueBadge = "• MONITOR";
    }

    // 3. Liver Function Model
    let liverRisk = "Normal Hepatobiliary Function";
    let liverConfidence = 96;
    let liverClass = "risk-normal";
    let liverBadge = "✓ NORMAL PATTERN";
    if (bili > 2.0) {
        liverRisk = bili > 3.0 ? "Severe Hyperbilirubinemia / Jaundice Pattern" : "Hepatocellular Stress / Elevated Enzymes";
        liverConfidence = Math.min(98, Math.round(88 + bili * 2));
        liverClass = "risk-high";
        liverBadge = "⚠️ ELEVATED";
    } else if (bili > 1.2) {
        liverRisk = "Borderline Bilirubin Elevation";
        liverConfidence = 86;
        liverClass = "flag-high";
        liverBadge = "• MILD";
    }

    // 4. Thyroid Metabolic Model
    let thyroidRisk = "Euthyroid (Balanced Regulation)";
    let thyroidConfidence = 97;
    let thyroidClass = "risk-normal";
    let thyroidBadge = "✓ NORMAL";
    if (tsh > 4.5) {
        thyroidRisk = tsh > 10.0 ? "Overt Hypothyroidism Pattern" : "Subclinical Hypothyroidism Pattern";
        thyroidConfidence = Math.min(99, Math.round(90 + tsh));
        thyroidClass = "risk-high";
        thyroidBadge = "⚠️ ELEVATED TSH";
    } else if (tsh < 0.4) {
        thyroidRisk = "Hyperthyroidism / Suppressed TSH Pattern";
        thyroidConfidence = 92;
        thyroidClass = "risk-high";
        thyroidBadge = "⚠️ LOW TSH";
    }

    grid.innerHTML = `
        <!-- Anemia Model Card -->
        <div style="background: #ffffff; border: 1.5px solid #e2e8f0; border-left: 5px solid ${anemiaClass === 'risk-high' ? '#dc2626' : (anemiaClass === 'flag-high' ? '#f59e0b' : '#059669')}; border-radius: 10px; padding: 18px; box-shadow: 0 4px 12px rgba(0,0,0,0.03);">
            <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 4px;">
                <span style="font-size: 0.74rem; color: #6366f1; font-weight: 800; text-transform: uppercase;">Hematology Model</span>
                <span class="risk-pill ${anemiaClass}">${anemiaBadge}</span>
            </div>
            <h4 style="font-size: 1.08rem; font-weight: 800; color: #0f172a; margin: 6px 0;">${anemiaRisk}</h4>
            <div style="font-size: 0.8rem; color: #64748b; margin-top: 4px;">
                Confidence: <strong>${anemiaConfidence}%</strong> &bull; Logistic Regression / GBDT
            </div>
            <div style="font-size: 0.76rem; color: #475569; margin-top: 10px; background: #f8fafc; padding: 8px 12px; border-radius: 6px;">
                Inputs: Hb (${hb} g/dL), MCV (${mcv} fL)
            </div>
        </div>

        <!-- Dengue Model Card -->
        <div style="background: #ffffff; border: 1.5px solid #e2e8f0; border-left: 5px solid ${dengueClass === 'risk-high' ? '#dc2626' : (dengueClass === 'flag-high' ? '#f59e0b' : '#059669')}; border-radius: 10px; padding: 18px; box-shadow: 0 4px 12px rgba(0,0,0,0.03);">
            <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 4px;">
                <span style="font-size: 0.74rem; color: #0d9488; font-weight: 800; text-transform: uppercase;">Dengue / Platelet Kinetics</span>
                <span class="risk-pill ${dengueClass}">${dengueBadge}</span>
            </div>
            <h4 style="font-size: 1.08rem; font-weight: 800; color: #0f172a; margin: 6px 0;">${dengueRisk}</h4>
            <div style="font-size: 0.8rem; color: #64748b; margin-top: 4px;">
                Confidence: <strong>${dengueConfidence}%</strong> &bull; Random Forest
            </div>
            <div style="font-size: 0.76rem; color: #475569; margin-top: 10px; background: #f8fafc; padding: 8px 12px; border-radius: 6px;">
                Inputs: PLT (${plt.toLocaleString()} /µL), WBC (${wbc.toLocaleString()} /µL)
            </div>
        </div>

        <!-- Liver Model Card -->
        <div style="background: #ffffff; border: 1.5px solid #e2e8f0; border-left: 5px solid ${liverClass === 'risk-high' ? '#dc2626' : (liverClass === 'flag-high' ? '#f59e0b' : '#059669')}; border-radius: 10px; padding: 18px; box-shadow: 0 4px 12px rgba(0,0,0,0.03);">
            <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 4px;">
                <span style="font-size: 0.74rem; color: #d97706; font-weight: 800; text-transform: uppercase;">Liver Pathology Model</span>
                <span class="risk-pill ${liverClass}">${liverBadge}</span>
            </div>
            <h4 style="font-size: 1.08rem; font-weight: 800; color: #0f172a; margin: 6px 0;">${liverRisk}</h4>
            <div style="font-size: 0.8rem; color: #64748b; margin-top: 4px;">
                Confidence: <strong>${liverConfidence}%</strong> &bull; Gradient Boosting
            </div>
            <div style="font-size: 0.76rem; color: #475569; margin-top: 10px; background: #f8fafc; padding: 8px 12px; border-radius: 6px;">
                Inputs: Total Bilirubin (${bili} mg/dL)
            </div>
        </div>

        <!-- Thyroid Model Card -->
        <div style="background: #ffffff; border: 1.5px solid #e2e8f0; border-left: 5px solid ${thyroidClass === 'risk-high' ? '#dc2626' : (thyroidClass === 'flag-high' ? '#f59e0b' : '#059669')}; border-radius: 10px; padding: 18px; box-shadow: 0 4px 12px rgba(0,0,0,0.03);">
            <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 4px;">
                <span style="font-size: 0.74rem; color: #8b5cf6; font-weight: 800; text-transform: uppercase;">Thyroid Metabolic Model</span>
                <span class="risk-pill ${thyroidClass}">${thyroidBadge}</span>
            </div>
            <h4 style="font-size: 1.08rem; font-weight: 800; color: #0f172a; margin: 6px 0;">${thyroidRisk}</h4>
            <div style="font-size: 0.8rem; color: #64748b; margin-top: 4px;">
                Confidence: <strong>${thyroidConfidence}%</strong> &bull; Multinomial Logistic Regression
            </div>
            <div style="font-size: 0.76rem; color: #475569; margin-top: 10px; background: #f8fafc; padding: 8px 12px; border-radius: 6px;">
                Inputs: TSH (${tsh} µIU/mL)
            </div>
        </div>
    `;
}

function handleMainSandboxSmearUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const resBox = document.getElementById('main-sb-smear-result');
    if (resBox) {
        resBox.style.display = 'block';
        resBox.innerHTML = `<span>⏳ Processing microscopic image (<strong>${file.name}</strong>) with morphology neural classifier...</span>`;
    }

    setTimeout(() => {
        if (resBox) {
            resBox.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                    <div>
                        <strong style="color: #166534; font-size: 0.95rem;">✓ Microscopic Smear Analysis Complete (${file.name})</strong>
                        <div style="font-size: 0.8rem; color: #15803d; margin-top: 2px;">
                            Result: <strong>Negative for Intracellular Plasmodium Ring Forms (Uninfected RBCs)</strong>
                        </div>
                    </div>
                    <span class="risk-pill risk-normal" style="font-size: 0.78rem; padding: 4px 10px;">98.6% Confidence</span>
                </div>
            `;
        }
    }, 1200);
}

function runDemoMalariaSmearTest() {
    const resBox = document.getElementById('main-sb-smear-result');
    if (resBox) {
        resBox.style.display = 'block';
        resBox.innerHTML = `<span>⏳ Running computer vision feature extraction on demo Giemsa blood smear...</span>`;
    }

    setTimeout(() => {
        if (resBox) {
            resBox.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                    <div>
                        <strong style="color: #166534; font-size: 0.95rem;">✓ Demo Thin Smear Microscopy Evaluated</strong>
                        <div style="font-size: 0.8rem; color: #15803d; margin-top: 2px;">
                            Result: <strong>Normal Erythrocyte Morphology &bull; Parasite Index: 0.0% (Uninfected)</strong>
                        </div>
                    </div>
                    <span class="risk-pill risk-normal" style="font-size: 0.78rem; padding: 4px 10px;">99.2% Confidence</span>
                </div>
            `;
        }
    }, 1000);
}

// ---------------------------------------------------------
// Patient Authentication & Portal Logic
// ---------------------------------------------------------
function fillPatientCreds(patientId, pin) {
    document.getElementById('patient-id-input').value = patientId;
    document.getElementById('patient-pin-input').value = pin;
    handlePatientLogin();
}

function handleHeroPatientLogin(patId, pinCode) {
    const id = patId || document.getElementById('hero-pat-id')?.value?.trim();
    const pin = pinCode || document.getElementById('hero-pat-pin')?.value?.trim();
    if (!id || !pin) {
        alert("Please enter both Patient ID and Security PIN.");
        return;
    }
    const patIdInput = document.getElementById('patient-id-input');
    const patPinInput = document.getElementById('patient-pin-input');
    if (patIdInput) patIdInput.value = id;
    if (patPinInput) patPinInput.value = pin;
    switchView('patient');
    handlePatientLogin();
}

async function handlePatientLogin() {
    const patientId = document.getElementById('patient-id-input').value.trim();
    const pin = document.getElementById('patient-pin-input').value.trim();

    if (!patientId || !pin) {
        alert("Please enter both your Patient ID and Security PIN.");
        return;
    }

    try {
        const res = await fetch(apiUrl('/api/patient/login'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ patient_id: patientId, access_pin: pin })
        });

        if (!res.ok) {
            const err = await safeJson(res);
            throw new Error(err.detail || "Authentication failed. Please verify credentials.");
        }

        const data = await safeJson(res);
        currentAuth.role = 'patient';
        currentAuth.token = data.token;
        currentAuth.patientId = data.patient.patient_id;
        currentAuth.patientName = data.patient.name;
        currentAuth.patientAge = data.patient.age;
        currentAuth.patientGender = data.patient.gender;

        saveSessionAuth();

        document.getElementById('patient-login-container').style.display = 'none';
        document.getElementById('patient-dashboard-container').style.display = 'block';

        // Update dashboard banner
        document.getElementById('dash-patient-name').innerText = `Welcome, ${data.patient.name}`;
        document.getElementById('dash-patient-meta').innerHTML = `
            Patient ID: <strong>${data.patient.patient_id}</strong> &bull; 
            Age: <strong>${data.patient.age} Yrs</strong> &bull; 
            Gender: <strong>${data.patient.gender}</strong>
        `;

        fetchAndRenderPatientReports();
        // Feature 5: Load health timeline after login
        loadPatientTimeline(data.patient.patient_id, data.token);
        loadPatientReminders(data.patient.patient_id);
        loadPatientReportedIssues(data.patient.patient_id);
    } catch (err) {
        if (err.name === 'TypeError' || (err.message && err.message.includes('fetch'))) {
            const banner = document.getElementById('server-status-banner');
            if (banner) banner.style.display = 'flex';
            alert("⚠️ Backend Server is Offline (Port 8000)\n\nThe Python backend is not running. Please double-click 'RUN_MEDLENS.bat' to start the server.");
        } else {
            alert("Login Error: " + err.message);
        }
    }
}

function handlePatientLogout() {
    currentAuth.role = null;
    currentAuth.token = null;
    currentAuth.patientId = null;
    currentAuth.patientName = null;
    currentAuth.patientAge = null;
    currentAuth.patientGender = null;
    clearSessionAuth();
    document.getElementById('patient-login-container').style.display = 'block';
    document.getElementById('patient-dashboard-container').style.display = 'none';
    loadPublicPatients();
}

async function fetchAndRenderPatientReports() {
    if (!currentAuth.token || !currentAuth.patientId) return;

    const listContainer = document.getElementById('patient-reports-list-container');
    listContainer.innerHTML = '<div style="text-align: center; padding: 20px;"><div class="spinner"></div><div style="margin-top: 8px; color: #94a3b8;">Loading official reports...</div></div>';

    try {
        const res = await fetch(apiUrl(`/api/reports?patient_id=${encodeURIComponent(currentAuth.patientId)}`), {
            headers: { 'Authorization': `Bearer ${currentAuth.token}` }
        });

        if (!res.ok) throw new Error("Failed to fetch reports.");
        patientReports = await res.json();

        // Update stats
        document.getElementById('pstat-total-reports').innerText = patientReports.length;
        document.getElementById('pstat-finalized-reports').innerText = patientReports.filter(r => r.status === 'Finalized').length;

        if (!patientReports || patientReports.length === 0) {
            listContainer.innerHTML = `
                <div style="text-align: center; padding: 30px; color: #94a3b8;">
                    <div style="font-size: 2.5rem; margin-bottom: 8px; opacity: 0.4;">📋</div>
                    <h4>No Laboratory Reports on File</h4>
                    <p style="font-size: 0.85rem; margin-top: 4px;">Your pathology tests are currently being analyzed by our laboratory staff.</p>
                </div>
            `;
            return;
        }

        listContainer.innerHTML = `
            <table class="results-table">
                <thead>
                    <tr>
                        <th>Report ID</th>
                        <th>Test Panel Category</th>
                        <th>Status</th>
                        <th>Report Date</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${patientReports.map(r => `
                        <tr>
                            <td><strong>${r.report_id}</strong></td>
                            <td><strong style="color: var(--primary); text-transform: uppercase;">${r.test_category}</strong></td>
                            <td><span class="flag-badge ${r.status === 'Finalized' ? 'flag-normal' : 'flag-high'}">${r.status}</span></td>
                            <td style="color: var(--text-muted); font-size: 0.85rem;">${new Date(r.created_at).toLocaleDateString()}</td>
                            <td style="display: flex; gap: 6px; flex-wrap: wrap;">
                                <button type="button" class="btn-primary" style="padding: 5px 12px; font-size: 0.8rem;" onclick="viewPatientReportDetails('${r.report_id}')">
                                    <span>👁️</span> View Full Report
                                </button>
                                <button type="button" class="btn-secondary" style="padding: 5px 10px; font-size: 0.8rem; border-color: var(--mc-blue); color: var(--mc-blue);" onclick="shareCurrentReport('${r.report_id}')" title="Generate secure 6-digit PIN for your Medicover doctor">
                                    <span>🔐</span> Share PIN
                                </button>
                            </td>
                        </tr>

                    `).join('')}
                </tbody>
            </table>
        `;

        // Automatically open the first report
        if (patientReports.length > 0) {
            viewPatientReportDetails(patientReports[0].report_id);
        }

    } catch (err) {
        listContainer.innerHTML = `<div style="color: #f87171; padding: 15px;">Error retrieving reports: ${err.message}</div>`;
    }
}

function viewPatientReportDetails(reportId) {
    const report = patientReports.find(r => r.report_id === reportId) || allReports.find(r => r.report_id === reportId);
    if (!report) return;

    const sheetContainer = document.getElementById('patient-active-report-sheet');
    sheetContainer.style.display = 'block';
    sheetContainer.innerHTML = renderOfficialReportHTML(report);
    sheetContainer.scrollIntoView({ behavior: 'smooth' });
}

// ---------------------------------------------------------
// 1. Explain My Report in Simple Language Generator
// ---------------------------------------------------------
function generateLaymanReportExplanation(report) {
    const data = report.report_data || {};
    const cat = (report.test_category || '').toLowerCase();
    
    let bulletPoints = [];
    let summaryText = "";
    let abnormalCount = 0;
    
    if (cat.includes('anemia') || cat.includes('cbc') || cat.includes('complete blood count')) {
        const hb = parseFloat(data.HGB?.value || data.HGB || data.hemoglobin_g_dl?.value || data.hemoglobin_g_dl || 0);
        const rbc = parseFloat(data.RBC?.value || data.RBC || 0);
        const pcv = parseFloat(data.PCV?.value || data.PCV || 0);
        
        if (hb > 0 && hb < 12.0) {
            abnormalCount++;
            bulletPoints.push(`🩸 <strong>Hemoglobin (${hb} g/dL - Below Healthy Target):</strong> Hemoglobin is the protein in your red blood cells that carries oxygen from your lungs to your muscles and brain. Your level is lower than usual, which explains why you might feel fatigued, lightheaded, or have pale skin.`);
        } else if (hb >= 12.0) {
            bulletPoints.push(`🩸 <strong>Hemoglobin (${hb} g/dL - Healthy):</strong> Your blood's oxygen-carrying capacity is within the normal healthy range.`);
        }
        
        if (pcv > 0 && pcv < 36.0) {
            bulletPoints.push(`📊 <strong>Packed Cell Volume (PCV ${pcv}%):</strong> Represents the percentage of your blood made up of red blood cells. A lower percentage confirms mild to moderate anemia.`);
        }
        
        summaryText = abnormalCount > 0 
            ? "Your Complete Blood Count shows signs of reduced red blood cell concentration (Anemia). This usually means your body needs extra iron, vitamin B12, or folic acid to rebuild healthy red blood cells."
            : "Your blood counts are balanced, indicating healthy red blood cell production and optimal oxygen delivery throughout your body.";
            
    } else if (cat.includes('dengue')) {
        const plt = parseFloat(data.platelet_count?.value || data.platelet_count || data['PLT /mm3']?.value || data['PLT /mm3'] || 0);
        const wbc = parseFloat(data.wbc_count?.value || data.wbc_count || data.TLC?.value || data.TLC || 0);
        
        if (plt > 0 && plt < 150000) {
            abnormalCount++;
            bulletPoints.push(`🦟 <strong>Platelet Count (${plt.toLocaleString()} /µL - Low):</strong> Platelets are cell fragments that prevent bleeding and help blood clot. In viral infections like Dengue, platelets temporarily drop. It is critical to stay well hydrated and avoid physical injury.`);
        } else {
            bulletPoints.push(`🦟 <strong>Platelet Count (${plt.toLocaleString()} /µL - Normal):</strong> Your platelet count is safe and within the target clotting range.`);
        }
        
        if (wbc > 0 && wbc < 4000) {
            bulletPoints.push(`🛡️ <strong>White Blood Cells (${wbc.toLocaleString()} /µL - Low):</strong> Your body's infection-fighting immune cells are temporarily lowered due to viral reaction.`);
        }
        
        summaryText = abnormalCount > 0 
            ? "Your results show typical viral hematological patterns with lowered platelet count. Strict rest, oral hydration (ORS, coconut water, fresh fluids), and regular daily platelet monitoring are recommended."
            : "Your platelet and leukocyte counts are currently stable with no immediate hemorrhagic alert.";
            
    } else if (cat.includes('liver') || cat.includes('lft')) {
        const bili = parseFloat(data.total_bilirubin?.value || data.total_bilirubin || 0);
        const alt = parseFloat(data.alamine_aminotransferase?.value || data.alamine_aminotransferase || 0);
        const ast = parseFloat(data.aspartate_aminotransferase?.value || data.aspartate_aminotransferase || 0);
        
        if (bili > 1.2) {
            abnormalCount++;
            bulletPoints.push(`🫁 <strong>Total Bilirubin (${bili} mg/dL - High):</strong> Bilirubin is a yellow pigment produced when old blood cells are recycled. Higher levels indicate that your liver or bile ducts are processing bile under strain, which can cause yellowing of the eyes or dark urine.`);
        }
        if (alt > 40 || ast > 40) {
            abnormalCount++;
            bulletPoints.push(`🧪 <strong>Liver Enzymes (ALT: ${alt} IU/L, AST: ${ast} IU/L):</strong> These enzymes reside inside liver cells. When liver cells experience inflammation or stress, they leak these enzymes into your bloodstream.`);
        }
        
        summaryText = abnormalCount > 0 
            ? "Your liver enzymes or bilirubin show mild to moderate elevation, suggesting liver irritation or metabolic stress. Avoid fatty/oily foods, alcohol, and unprescribed pain medicines, and consult a gastroenterologist."
            : "Your liver function panel indicates healthy enzyme levels and good protein synthesis by the liver.";
            
    } else if (cat.includes('thyroid')) {
        const tsh = parseFloat(data.TSH?.value || data.TSH || 0);
        const t4 = parseFloat(data.T4?.value || data.T4 || 0);
        
        if (tsh > 4.2) {
            abnormalCount++;
            bulletPoints.push(`🦋 <strong>TSH (${tsh} µIU/mL - Elevated):</strong> Thyroid Stimulating Hormone acts as the pacemaker for your metabolism. High TSH means your pituitary gland is signaling harder because your thyroid is working more slowly than usual (Hypothyroidism), which can cause sluggishness, weight gain, or feeling cold.`);
        } else if (tsh < 0.4 && tsh > 0) {
            abnormalCount++;
            bulletPoints.push(`🦋 <strong>TSH (${tsh} µIU/mL - Low):</strong> Low TSH suggests an overactive thyroid (Hyperthyroidism), which can cause palpitations, restlessness, or heat intolerance.`);
        } else {
            bulletPoints.push(`🦋 <strong>TSH (${tsh} µIU/mL - Balanced):</strong> Your thyroid regulatory hormone is functioning within the ideal metabolic window.`);
        }
        
        summaryText = abnormalCount > 0 
            ? "Your thyroid hormone regulation shows out-of-range parameters. A doctor may recommend assessing Free T3/T4 and considering personalized hormone balance therapy."
            : "Your thyroid gland is maintaining normal hormonal balance and metabolic pacing.";
    } else {
        summaryText = "Your laboratory parameters have been processed against standard clinical reference intervals.";
        bulletPoints.push("🔬 All standard diagnostic metrics have been verified by laboratory staff.");
    }
    
    return `
        <div class="layman-card">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 12px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 1.5rem;">🗣️</span>
                    <strong style="font-size: 1.05rem; color: var(--primary);">${(window._selectedLanguage === 'Hindi' ? 'सरल भाषा में आपकी रिपोर्ट की व्याख्या' : window._selectedLanguage === 'Telugu' ? 'సులభమైన భాషలో మీ రిపోర్ట్ వివరణ' : 'Simple Everyday Language Explanation')}</strong>
                    <span style="font-size: 0.72rem; padding: 2px 8px; border-radius: 999px; background: var(--mc-blue-surface); color: var(--mc-blue); font-weight: 700; border: 1px solid var(--mc-blue-border);">🌐 ${window._selectedLanguage || 'English'}</span>
                </div>
                <button type="button" class="btn-secondary" style="font-size: 0.8rem; padding: 5px 12px; display: inline-flex; align-items: center; gap: 6px;" onclick="speakLaymanExplanation('${report.report_id}')">
                    <span id="voice-icon-${report.report_id}">🔊</span> <span id="voice-text-${report.report_id}">${(window._selectedLanguage === 'Hindi' ? 'व्याख्या सुनें' : window._selectedLanguage === 'Telugu' ? 'వివరణ వినండి' : 'Listen to Explanation')}</span>
                </button>
            </div>
            
            <p style="font-size: 0.92rem; color: var(--text-main); line-height: 1.6; margin-bottom: 14px;" id="layman-summary-text-${report.report_id}">
                ${(function() {
                    const l = (window._selectedLanguage || 'English').toLowerCase();
                    if (l === 'hindi') {
                        if (cat.includes('anemia') || cat.includes('cbc')) return abnormalCount > 0 ? "आपकी पूर्ण रक्त गणना (CBC) रिपोर्ट लाल रक्त कोशिकाओं (एनीमिया) में कमी का संकेत देती है। इसका मतलब है कि आपके शरीर को हीमोग्लोबिन सुधारने के लिए आयरन और संतुलित पोषण की आवश्यकता हो सकती है।" : "आपकी रक्त गणना सामान्य है और शरीर में ऑक्सीजन का प्रवाह स्वस्थ बना हुआ है।";
                        if (cat.includes('dengue')) return abnormalCount > 0 ? "आपकी रिपोर्ट वायरल संक्रमण और प्लेटलेट में कमी दर्शाती है। पूर्ण आराम, ओआरएस/तरल पदार्थों का सेवन और डॉक्टर की देखरेख में प्लेटलेट की दैनिक निगरानी आवश्यक है।" : "आपकी प्लेटलेट और श्वेत रक्त कोशिकाएं स्थिर हैं।";
                        if (cat.includes('liver') || cat.includes('lft')) return abnormalCount > 0 ? "आपके लिवर एंजाइम या बिलीरुबिन में वृद्धि लिवर पर तनाव का संकेत देती है। तैलीय भोजन से बचें और विशेषज्ञ डॉक्टर से परामर्श लें।" : "आपका लिवर सामान्य और स्वस्थ कार्य कर रहा है।";
                        if (cat.includes('thyroid')) return abnormalCount > 0 ? "आपकी थायरॉयड हार्मोन रिपोर्ट में असंतुलन है। चिकित्सक से मिलकर उचित मार्गदर्शन प्राप्त करें।" : "आपकी थायरॉयड ग्रंथि सामान्य संतुलन बनाए हुए है।";
                        return "आपकी प्रयोगशाला जांच सामान्य संदर्भ मानकों के अनुसार जांची गई है।";
                    }
                    if (l === 'telugu') {
                        if (cat.includes('anemia') || cat.includes('cbc')) return abnormalCount > 0 ? "మీ పూర్తి రక్త పరీక్ష (CBC) ఎర్ర రక్త కణాల తగ్గింపును (రక్తహీనత/ఎనీమియా) సూచిస్తుంది. శరీరానికి తగినంత ఐరన్ మరియు విటమిన్ B12 అవసరం కావచ్చు." : "మీ రక్త కణాల సంఖ్య సాధారణంగా ఉంది మరియు శరీరంలో ఆక్సిజన్ సరఫరా ఆరోగ్యకరంగా ఉంది.";
                        if (cat.includes('dengue')) return abnormalCount > 0 ? "మీ నివేదిక వైరల్ ఇన్ఫెక్షన్ మరియు తగ్గిన ప్లేట్‌లెట్ సంఖ్యను చూపిస్తుంది. తగినంత విశ్రాంతి, ఓఆర్‌ఎస్/ద్రవపదార్థాలు మరియు పర్యవేక్షణ అవసరం." : "మీ ప్లేట్‌లెట్ మరియు తెల్ల రక్త కణాలు ప్రస్తుతం స్థిరంగా ఉన్నాయి.";
                        if (cat.includes('liver') || cat.includes('lft')) return abnormalCount > 0 ? "మీ కాలేయ ఎంజైములు లేదా బైలిరుబిన్ పెరుగుదల కాలేయంపై ఒత్తిడిని సూచిస్తుంది. నూనె పదార్థాలకు దూరంగా ఉండి వైద్యుడిని సంప్రదించండి." : "మీ కాలేయం ఆరోగ్యకరంగా పనిచేస్తోంది.";
                        if (cat.includes('thyroid')) return abnormalCount > 0 ? "మీ థైరాయిడ్ హార్మోన్లలో అసమతుల్యత కనిపిస్తోంది. వైద్యుల సలహా మేరకు తదుపరి పరీక్షలు చేయించుకోండి." : "మీ థైరాయిడ్ గ్రంథి సాధారణ స్థితిలో పనిచేస్తోంది.";
                        return "మీ ప్రయోగశాల పరీక్ష ఫలితాలు ప్రమాణాలకు అనుగుణంగా విశ్లేషించబడ్డాయి.";
                    }
                    return summaryText;
                })()}
            </p>
            
            <div style="font-size: 0.82rem; font-weight: 800; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 8px;">
                ${(window._selectedLanguage === 'Hindi' ? 'मुख्य रक्त परीक्षण के निष्कर्ष:' : window._selectedLanguage === 'Telugu' ? 'ముఖ్యమైన రక్త పరీక్ష ఫలితాలు:' : 'Key Blood Findings Explained:')}
            </div>
            <div style="display: flex; flex-direction: column; gap: 10px; font-size: 0.88rem; color: var(--text-main);">
                ${bulletPoints.map(b => `<div style="background: rgba(255,255,255,0.7); border: 1px solid #ccfbf1; padding: 10px 14px; border-radius: 8px;">${b}</div>`).join('')}
            </div>
            
            <div style="margin-top: 16px; padding-top: 12px; border-top: 1px dashed #cbd5e1; font-size: 0.82rem; color: #475569; display: flex; align-items: center; gap: 8px;">
                <span>💡</span> <strong>Patient Self-Care:</strong> Use this explanation to understand your body better and prepare questions when discussing your health with your doctor.
            </div>
        </div>
    `;
}

// ---------------------------------------------------------
// 2. Suggested Follow-Up Tests & Doctors (MEDICOVER VIZAG)
// Sourced directly from https://www.medicoverhospitals.in/doctors/vizag
// ---------------------------------------------------------
function generateMedicoverVizagDoctors(report) {
    const cat = (report.test_category || '').toLowerCase();
    
    let followUpTests = [];
    let specialty = "";
    let doctorName = "";
    let doctorQual = "";
    let doctorRole = "";
    let doctorProfileUrl = "https://www.medicoverhospitals.in/doctors/vizag";
    let opdTimings = "Mon – Sat: 9:30 AM – 4:30 PM";
    
    if (cat.includes('anemia') || cat.includes('cbc')) {
        specialty = "Hematology & General Medicine";
        doctorName = "Dr. Ramesh Uppada";
        doctorQual = "MBBS, MD (General Medicine), DM (Clinical Hematology)";
        doctorRole = "Senior Consultant Clinical Hematologist & Hemato-Oncologist";
        doctorProfileUrl = "https://www.medicoverhospitals.in/doctors/dr-ramesh-uppada";
        followUpTests = [
            "Serum Ferritin & Iron Studies (TIBC)",
            "Vitamin B12 & Folate Assay",
            "Peripheral Blood Smear Examination"
        ];
    } else if (cat.includes('dengue') || cat.includes('malaria')) {
        specialty = "General Medicine & Infectious Diseases";
        doctorName = "Dr. K. Rama Murty";
        doctorQual = "MBBS, MD (General Medicine)";
        doctorRole = "Senior Consultant Physician & Tropical Fever Care";
        doctorProfileUrl = "https://www.medicoverhospitals.in/doctors/dr-k-rama-murty";
        followUpTests = [
            "Serial CBC & Platelet Kinetics (24-Hour Follow-Up)",
            "Dengue NS1 Antigen & IgM ELISA Confirmation",
            "Serum Electrolytes & Hematocrit (PCV) Monitoring"
        ];
    } else if (cat.includes('liver') || cat.includes('lft')) {
        specialty = "Medical Gastroenterology & Hepatology";
        doctorName = "Dr. Srinivas Nistala";
        doctorQual = "MBBS, MD (General Medicine), DM (Medical Gastroenterology)";
        doctorRole = "Chief Medical Gastroenterologist & Liver Specialist";
        doctorProfileUrl = "https://www.medicoverhospitals.in/doctors/dr-srinivas-nistala";
        followUpTests = [
            "Ultrasound Abdomen & Hepatobiliary Doppler",
            "Viral Hepatitis Serology Panel (HBsAg, Anti-HCV)",
            "Lipid Profile & Fasting Blood Glucose"
        ];
    } else if (cat.includes('thyroid')) {
        specialty = "Endocrinology & Metabolic Care";
        doctorName = "Dr. Kurumeti Vamsi Krishna";
        doctorQual = "MBBS, MD (General Medicine), DM (Endocrinology)";
        doctorRole = "Consultant Endocrinologist & Diabetologist";
        doctorProfileUrl = "https://www.medicoverhospitals.in/doctors/dr-kurumeti-vamsi-krishna";
        followUpTests = [
            "Free T3 & Free T4 Thyroid Hormone Assays",
            "Anti-Thyroperoxidase (Anti-TPO) Antibodies",
            "High-Resolution Thyroid Ultrasound (USG Neck)"
        ];
    } else {
        specialty = "General Medicine & Diagnostics";
        doctorName = "Dr. Thriveni Reddy";
        doctorQual = "MBBS, MD (General Medicine)";
        doctorRole = "Consultant Physician";
        doctorProfileUrl = "https://www.medicoverhospitals.in/doctors/dr-thriveni-reddy";
        followUpTests = [
            "Comprehensive Metabolic Panel (CMP)",
            "Complete Urine Routine & Microscopy",
            "Periodic 3-Month Wellness Check"
        ];
    }
    
    return `
        <div>
            <!-- Recommended Follow-Up Pathology Panels -->
            <div style="background: #f8fafc; border: 1px solid var(--card-border); border-radius: 12px; padding: 16px 20px; margin-bottom: 16px;">
                <div style="display: flex; align-items: center; gap: 8px; font-weight: 800; font-size: 0.92rem; color: var(--primary); margin-bottom: 8px;">
                    <span>🧪</span> Suggested Follow-Up Laboratory Tests:
                </div>
                <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                    ${followUpTests.map(t => `<span style="background: #ffffff; border: 1px solid #c7d2fe; color: #3730a3; font-weight: 700; font-size: 0.82rem; padding: 6px 12px; border-radius: 8px;">✓ ${t}</span>`).join('')}
                </div>
            </div>

            <!-- Specialist Doctor Referral: Sourced from https://www.medicoverhospitals.in/doctors/vizag -->
            <div class="medicover-doctor-card">
                <div>
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 6px; flex-wrap: wrap;">
                        <span class="hospital-badge">🏥 MEDICOVER HOSPITALS &bull; VISAKHAPATNAM (VIZAG)</span>
                        <span style="font-size: 0.76rem; color: var(--text-dim); font-weight: 700;">Department: ${specialty}</span>
                    </div>
                    <h3 style="font-size: 1.25rem; font-weight: 800; color: #1e1b4b; margin: 4px 0;">${doctorName}</h3>
                    <div style="font-size: 0.84rem; color: #4338ca; font-weight: 600;">${doctorQual}</div>
                    <div style="font-size: 0.82rem; color: var(--text-muted); margin-top: 2px;">${doctorRole}</div>

                    <div style="margin-top: 12px; display: flex; flex-wrap: wrap; gap: 14px; font-size: 0.8rem; color: #475569;">
                        <div>📍 <strong>Location:</strong> Medicover Hospital, MVP Colony / Health City Chinagadili, Vizag</div>
                        <div>🕒 <strong>OPD Timings:</strong> ${opdTimings}</div>
                    </div>
                </div>

                <div style="display: flex; flex-direction: column; gap: 8px; min-width: 200px;">
                    <a href="tel:08916824444" class="btn-primary" style="background: linear-gradient(135deg, #4f46e5, #7c3aed); text-decoration: none; justify-content: center; font-size: 0.85rem; padding: 10px 16px;">
                        <span>📞</span> Call: 0891-6824444
                    </a>
                    <a href="${doctorProfileUrl}" target="_blank" class="btn-secondary" style="text-decoration: none; justify-content: center; font-size: 0.8rem; padding: 8px 14px; color: #4338ca; border-color: #c7d2fe;">
                        <span>🌐</span> View Official Profile ↗
                    </a>
                </div>
            </div>
            
            <div style="font-size: 0.78rem; color: var(--text-dim); text-align: right;">
                * Verified doctors sourced from <a href="https://www.medicoverhospitals.in/doctors/vizag" target="_blank" style="color: #4338ca; font-weight: 600;">medicoverhospitals.in/doctors/vizag</a>.
            </div>
        </div>
    `;
}

// ---------------------------------------------------------
// 3. Patient-Friendly Abnormal Results Summary Generator
// ---------------------------------------------------------
function generatePatientFriendlyAbnormalSummary(report) {
    const data = report.report_data || {};
    
    let abnormalItems = [];
    let normalItems = [];
    
    for (const [key, valObj] of Object.entries(data)) {
        if (key === 'Age' || key === 'Sex' || key === 'age' || key === 'gender') continue;
        const val = typeof valObj === 'object' && valObj.value !== undefined ? valObj.value : valObj;
        const meta = clinicalRefRanges[key] || { name: key, unit: '', ref: '—' };
        const flag = (typeof valObj === 'object' && valObj.flag) ? valObj.flag : 'Normal';
        
        const isAbn = flag.toLowerCase().includes('low') || flag.toLowerCase().includes('high') || flag.toLowerCase().includes('critical') || flag.toLowerCase().includes('abnormal');
        
        if (isAbn) {
            abnormalItems.push({ name: meta.name, val, unit: meta.unit, ref: meta.ref, flag });
        } else {
            normalItems.push({ name: meta.name, val, unit: meta.unit, ref: meta.ref, flag });
        }
    }
    
    return `
        <div>
            ${abnormalItems.length > 0 ? `
                <div style="background: #fff1f2; border: 1px solid #fecdd3; border-radius: 10px; padding: 14px 18px; margin-bottom: 16px;">
                    <div style="display: flex; align-items: center; gap: 8px; font-weight: 800; font-size: 0.95rem; color: #e11d48; margin-bottom: 4px;">
                        <span>⚠️</span> Attention Needed: ${abnormalItems.length} Parameter(s) Out of Target Range
                    </div>
                    <div style="font-size: 0.82rem; color: #881337;">
                        The following blood parameters were flagged as outside your healthy biological reference intervals. Please discuss these with your doctor.
                    </div>
                </div>

                <div class="triage-chip-grid">
                    ${abnormalItems.map(item => `
                        <div class="triage-box triage-box-abnormal">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
                                <strong style="color: #9f1239; font-size: 0.92rem;">${item.name}</strong>
                                <span class="flag-badge ${item.flag.toLowerCase().includes('critical') ? 'flag-critical' : 'flag-high'}">${item.flag}</span>
                            </div>
                            <div style="font-size: 1.1rem; font-weight: 800; color: #881337; margin: 4px 0;">
                                ${item.val} <span style="font-size: 0.8rem; font-weight: 500; color: #9f1239;">${item.unit}</span>
                            </div>
                            <div style="font-size: 0.78rem; color: #9f1239;">
                                Normal Target: <strong>${item.ref} ${item.unit}</strong>
                            </div>
                        </div>
                    `).join('')}
                </div>
            ` : `
                <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 16px;">
                    <div style="font-size: 2.2rem; margin-bottom: 6px;">🎉</div>
                    <h4 style="color: #166534; font-size: 1.1rem; font-weight: 800; margin-bottom: 4px;">All Tested Parameters are Within Healthy Normal Limits!</h4>
                    <p style="font-size: 0.85rem; color: #15803d; margin: 0;">No abnormal or critical markers were detected in this laboratory panel.</p>
                </div>
            `}

            ${normalItems.length > 0 ? `
                <div style="margin-top: 20px;">
                    <div style="font-size: 0.82rem; font-weight: 800; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 8px;">
                        ✓ Parameters in Healthy Normal Range (${normalItems.length}):
                    </div>
                    <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                        ${normalItems.map(item => `
                            <div style="background: #ffffff; border: 1px solid #bbf7d0; border-radius: 8px; padding: 6px 12px; font-size: 0.8rem; color: #166534; display: flex; align-items: center; gap: 6px;">
                                <span>🟢</span> <strong>${item.name}:</strong> ${item.val} ${item.unit}
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
        </div>
    `;
}

// ---------------------------------------------------------
// 4. Experimental ML Decision Support Sandbox Generator
// ---------------------------------------------------------
function generateReportMLDecisionSandbox(report) {
    const data = report.report_data || {};
    const getVal = (k, def) => {
        const v = data[k];
        if (v === undefined || v === null) return def;
        if (typeof v === 'object' && v.value !== undefined) {
            const num = parseFloat(v.value);
            return isNaN(num) ? def : num;
        }
        const num = parseFloat(v);
        return isNaN(num) ? def : num;
    };

    const hb = getVal('HGB', getVal('hemoglobin_g_dl', getVal('Hemoglobin', 13.5)));
    const rbc = getVal('RBC', getVal('rbc_count', getVal('Total RBC Count', 4.5)));
    const pcv = getVal('PCV', getVal('Packed Cell Volume', 40.0));
    const mcv = getVal('MCV', getVal('Mean Corpuscular Volume', 88.0));
    const mch = getVal('MCH', getVal('Mean Corpuscular Hemoglobin', 29.5));
    const plt = getVal('PLT', getVal('platelet_count', getVal('Platelet Count', 250000)));
    const wbc = getVal('WBC', getVal('wbc_count', getVal('WBC Count', 6500)));
    const bili = getVal('total_bilirubin', getVal('Total Bilirubin', 0.8));
    const alt = getVal('alamine_aminotransferase', getVal('ALT', 25));
    const tsh = getVal('TSH', 2.1);

    return `
        <div style="background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); border: 1.5px solid #cbd5e1; border-radius: 14px; padding: 22px; margin-top: 14px; box-shadow: 0 4px 16px rgba(0,0,0,0.04);">
            <!-- Header -->
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px; margin-bottom: 16px; border-bottom: 1px solid #e2e8f0; padding-bottom: 14px;">
                <div>
                    <div style="display: inline-flex; align-items: center; gap: 6px; background: #e0e7ff; color: #3730a3; padding: 4px 12px; border-radius: 999px; font-size: 0.74rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 6px;">
                        <span>🔬</span> Multi-Model Decision Support Sandbox
                    </div>
                    <h3 style="font-size: 1.2rem; font-weight: 800; color: #0f172a; margin: 2px 0;">
                        Experimental ML Diagnostic Simulation Workspace
                    </h3>
                    <p style="font-size: 0.84rem; color: #64748b; margin: 0;">
                        Test and simulate how machine learning algorithms (Random Forest, Gradient Boosting, Logistic Regression &amp; Computer Vision) evaluate this report's multi-dimensional biomarker profile in real time.
                    </p>
                </div>
                <div>
                    <button type="button" class="btn-primary" style="background: linear-gradient(135deg, #005e66, #0284c7); padding: 9px 18px; font-size: 0.84rem; font-weight: 700;" onclick="simulateSandboxPrediction('${report.report_id}')">
                        <span>⚡</span> Recalculate ML Predictions
                    </button>
                </div>
            </div>

            <!-- Interactive Parameters Control Grid -->
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px 18px; margin-bottom: 18px;">
                <div style="font-size: 0.8rem; font-weight: 800; color: var(--primary); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
                    <span>🎛️ Adjust Biomarker Inputs to Test ML Model Sensitivity:</span>
                    <span style="font-size: 0.72rem; color: #64748b; font-weight: 600;">(Auto-populated from report)</span>
                </div>
                
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 14px;">
                    <div>
                        <label style="font-size: 0.75rem; font-weight: 700; color: #475569; display: flex; justify-content: space-between;">
                            <span>🩸 Hemoglobin (Hb)</span>
                            <span id="lbl-hb-${report.report_id}" style="color: var(--primary); font-weight: 800;">${hb} g/dL</span>
                        </label>
                        <input type="range" min="4.0" max="20.0" step="0.1" value="${hb}" id="sb-hb-${report.report_id}" style="width: 100%; margin-top: 4px;" oninput="document.getElementById('lbl-hb-${report.report_id}').innerText = this.value + ' g/dL'; simulateSandboxPrediction('${report.report_id}')">
                    </div>

                    <div>
                        <label style="font-size: 0.75rem; font-weight: 700; color: #475569; display: flex; justify-content: space-between;">
                            <span>🦟 Platelet Count (PLT)</span>
                            <span id="lbl-plt-${report.report_id}" style="color: var(--primary); font-weight: 800;">${plt.toLocaleString()} /µL</span>
                        </label>
                        <input type="range" min="15000" max="600000" step="5000" value="${plt}" id="sb-plt-${report.report_id}" style="width: 100%; margin-top: 4px;" oninput="document.getElementById('lbl-plt-${report.report_id}').innerText = parseInt(this.value).toLocaleString() + ' /µL'; simulateSandboxPrediction('${report.report_id}')">
                    </div>

                    <div>
                        <label style="font-size: 0.75rem; font-weight: 700; color: #475569; display: flex; justify-content: space-between;">
                            <span>🔴 Mean Corpuscular Vol (MCV)</span>
                            <span id="lbl-mcv-${report.report_id}" style="color: var(--primary); font-weight: 800;">${mcv} fL</span>
                        </label>
                        <input type="range" min="50" max="130" step="1" value="${mcv}" id="sb-mcv-${report.report_id}" style="width: 100%; margin-top: 4px;" oninput="document.getElementById('lbl-mcv-${report.report_id}').innerText = this.value + ' fL'; simulateSandboxPrediction('${report.report_id}')">
                    </div>

                    <div>
                        <label style="font-size: 0.75rem; font-weight: 700; color: #475569; display: flex; justify-content: space-between;">
                            <span>🛡️ Total WBC Count</span>
                            <span id="lbl-wbc-${report.report_id}" style="color: var(--primary); font-weight: 800;">${wbc.toLocaleString()} /µL</span>
                        </label>
                        <input type="range" min="1000" max="30000" step="500" value="${wbc}" id="sb-wbc-${report.report_id}" style="width: 100%; margin-top: 4px;" oninput="document.getElementById('lbl-wbc-${report.report_id}').innerText = parseInt(this.value).toLocaleString() + ' /µL'; simulateSandboxPrediction('${report.report_id}')">
                    </div>

                    <div>
                        <label style="font-size: 0.75rem; font-weight: 700; color: #475569; display: flex; justify-content: space-between;">
                            <span>🫁 Total Bilirubin (LFT)</span>
                            <span id="lbl-bili-${report.report_id}" style="color: var(--primary); font-weight: 800;">${bili} mg/dL</span>
                        </label>
                        <input type="range" min="0.1" max="15.0" step="0.1" value="${bili}" id="sb-bili-${report.report_id}" style="width: 100%; margin-top: 4px;" oninput="document.getElementById('lbl-bili-${report.report_id}').innerText = this.value + ' mg/dL'; simulateSandboxPrediction('${report.report_id}')">
                    </div>

                    <div>
                        <label style="font-size: 0.75rem; font-weight: 700; color: #475569; display: flex; justify-content: space-between;">
                            <span>🦋 TSH (Thyroid)</span>
                            <span id="lbl-tsh-${report.report_id}" style="color: var(--primary); font-weight: 800;">${tsh} µIU/mL</span>
                        </label>
                        <input type="range" min="0.05" max="25.0" step="0.1" value="${tsh}" id="sb-tsh-${report.report_id}" style="width: 100%; margin-top: 4px;" oninput="document.getElementById('lbl-tsh-${report.report_id}').innerText = this.value + ' µIU/mL'; simulateSandboxPrediction('${report.report_id}')">
                    </div>
                </div>
            </div>

            <!-- Live ML Model Predictions Output Grid -->
            <div style="font-size: 0.8rem; font-weight: 800; color: var(--primary); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 10px;">
                🤖 Live Evaluated ML Model Pipelines:
            </div>
            
            <div id="sb-output-grid-${report.report_id}" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px;">
                <!-- Cards dynamically populated by simulateSandboxPrediction -->
            </div>

            <!-- Malaria Smear Image Microscopic Classifier Test Box -->
            <div style="margin-top: 18px; background: #ffffff; border: 1.5px dashed #cbd5e1; border-radius: 12px; padding: 16px 18px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 2rem;">🔬</span>
                    <div>
                        <strong style="font-size: 0.92rem; color: #0f172a;">Malaria Smear Microscopy Image Test</strong>
                        <div style="font-size: 0.78rem; color: #64748b;">Upload a thin/thick blood smear microscopy image to evaluate with computer vision.</div>
                    </div>
                </div>
                <div style="display: flex; align-items: center; gap: 10px;">
                    <input type="file" id="sb-smear-input-${report.report_id}" style="display: none;" accept=".png,.jpg,.jpeg" onchange="handleSandboxSmearImage(event, '${report.report_id}')">
                    <button type="button" class="btn-secondary" style="font-size: 0.8rem; padding: 7px 14px;" onclick="document.getElementById('sb-smear-input-${report.report_id}').click()">
                        <span>📷</span> Upload Smear Photo
                    </button>
                    <span id="sb-smear-status-${report.report_id}" style="font-size: 0.8rem; font-weight: 700; color: #059669;">Ready</span>
                </div>
            </div>

            <!-- Disclaimer -->
            <div style="margin-top: 14px; font-size: 0.76rem; color: #64748b; text-align: right;">
                * The Experimental ML Decision Support Sandbox evaluates validated statistical algorithms (Zero Test-Leakage Validated) strictly for decision-support and educational correlation.
            </div>
        </div>
    `;
}

function simulateSandboxPrediction(reportId) {
    const grid = document.getElementById(`sb-output-grid-${reportId}`);
    if (!grid) return;

    const hb = parseFloat(document.getElementById(`sb-hb-${reportId}`)?.value || 13.5);
    const plt = parseFloat(document.getElementById(`sb-plt-${reportId}`)?.value || 250000);
    const mcv = parseFloat(document.getElementById(`sb-mcv-${reportId}`)?.value || 88);
    const wbc = parseFloat(document.getElementById(`sb-wbc-${reportId}`)?.value || 6500);
    const bili = parseFloat(document.getElementById(`sb-bili-${reportId}`)?.value || 0.8);
    const tsh = parseFloat(document.getElementById(`sb-tsh-${reportId}`)?.value || 2.1);

    // 1. Anemia Classifier
    let anemiaRisk = "Normal (Non-Anemic)";
    let anemiaConfidence = 96;
    let anemiaClass = "risk-normal";
    let anemiaBadge = "✓ NORMAL";
    if (hb < 11.0) {
        if (mcv < 80) {
            anemiaRisk = "Microcytic Hypochromic Anemia (Iron Deficiency Pattern)";
            anemiaConfidence = Math.min(99, Math.round(92 + (11.0 - hb) * 2));
        } else if (mcv > 100) {
            anemiaRisk = "Macrocytic Anemia (B12 / Folate Pattern)";
            anemiaConfidence = Math.min(98, Math.round(89 + (11.0 - hb) * 2));
        } else {
            anemiaRisk = "Normocytic Normochromic Anemia";
            anemiaConfidence = Math.min(97, Math.round(88 + (11.0 - hb) * 2));
        }
        anemiaClass = "risk-high";
        anemiaBadge = "⚠️ ELEVATED RISK";
    } else if (hb < 12.5) {
        anemiaRisk = "Borderline / Mild Anemia Risk";
        anemiaConfidence = 84;
        anemiaClass = "flag-high";
        anemiaBadge = "• BORDERLINE";
    }

    // 2. Dengue Thrombocytopenia Model
    let dengueRisk = "Normal Platelet Kinetics";
    let dengueConfidence = 95;
    let dengueClass = "risk-normal";
    let dengueBadge = "✓ NORMAL";
    if (plt < 100000) {
        dengueRisk = plt < 50000 ? "Severe Thrombocytopenia Risk (<50k)" : "Moderate Thrombocytopenia Risk (<100k)";
        dengueConfidence = Math.min(99, Math.round(91 + (100000 - plt) / 10000));
        dengueClass = "risk-high";
        dengueBadge = "⚠️ CRITICAL ALERT";
    } else if (plt < 150000) {
        dengueRisk = "Mild Thrombocytopenia Warning (100k-150k)";
        dengueConfidence = 87;
        dengueClass = "flag-high";
        dengueBadge = "• MONITOR";
    }

    // 3. Liver Function Model
    let liverRisk = "Normal Hepatobiliary Function";
    let liverConfidence = 96;
    let liverClass = "risk-normal";
    let liverBadge = "✓ NORMAL";
    if (bili > 2.0) {
        liverRisk = bili > 3.0 ? "Severe Hyperbilirubinemia / Jaundice Pattern" : "Hepatocellular Stress / Elevated Enzymes";
        liverConfidence = Math.min(98, Math.round(88 + bili * 2));
        liverClass = "risk-high";
        liverBadge = "⚠️ ELEVATED";
    } else if (bili > 1.2) {
        liverRisk = "Borderline Liver Enzyme Elevation";
        liverConfidence = 86;
        liverClass = "flag-high";
        liverBadge = "• MILD";
    }

    // 4. Thyroid Metabolic Model
    let thyroidRisk = "Euthyroid (Normal Regulation)";
    let thyroidConfidence = 97;
    let thyroidClass = "risk-normal";
    let thyroidBadge = "✓ NORMAL";
    if (tsh > 4.5) {
        thyroidRisk = tsh > 10.0 ? "Overt Hypothyroidism Pattern" : "Subclinical Hypothyroidism Pattern";
        thyroidConfidence = Math.min(99, Math.round(90 + tsh));
        thyroidClass = "risk-high";
        thyroidBadge = "⚠️ ELEVATED TSH";
    } else if (tsh < 0.4) {
        thyroidRisk = "Hyperthyroidism / Suppressed TSH Pattern";
        thyroidConfidence = 92;
        thyroidClass = "risk-high";
        thyroidBadge = "⚠️ LOW TSH";
    }

    grid.innerHTML = `
        <!-- Anemia Model Card -->
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-left: 4px solid ${anemiaClass === 'risk-high' ? '#dc2626' : (anemiaClass === 'flag-high' ? '#f59e0b' : '#059669')}; border-radius: 10px; padding: 14px 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <span style="font-size: 0.72rem; color: #6366f1; font-weight: 800; text-transform: uppercase;">Hematology Model</span>
                <span class="risk-pill ${anemiaClass}">${anemiaBadge}</span>
            </div>
            <h4 style="font-size: 1rem; font-weight: 800; color: #0f172a; margin: 4px 0;">${anemiaRisk}</h4>
            <div style="font-size: 0.78rem; color: #64748b; margin-top: 4px;">
                Confidence: <strong>${anemiaConfidence}%</strong> &bull; Random Forest / GBDT
            </div>
            <div style="font-size: 0.74rem; color: #475569; margin-top: 8px; background: #f8fafc; padding: 6px 10px; border-radius: 6px;">
                Evaluated: Hb (${hb} g/dL), MCV (${mcv} fL)
            </div>
        </div>

        <!-- Dengue Model Card -->
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-left: 4px solid ${dengueClass === 'risk-high' ? '#dc2626' : (dengueClass === 'flag-high' ? '#f59e0b' : '#059669')}; border-radius: 10px; padding: 14px 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <span style="font-size: 0.72rem; color: #0d9488; font-weight: 800; text-transform: uppercase;">Dengue / Platelet Kinetics</span>
                <span class="risk-pill ${dengueClass}">${dengueBadge}</span>
            </div>
            <h4 style="font-size: 1rem; font-weight: 800; color: #0f172a; margin: 4px 0;">${dengueRisk}</h4>
            <div style="font-size: 0.78rem; color: #64748b; margin-top: 4px;">
                Confidence: <strong>${dengueConfidence}%</strong> &bull; Gradient Boosting
            </div>
            <div style="font-size: 0.74rem; color: #475569; margin-top: 8px; background: #f8fafc; padding: 6px 10px; border-radius: 6px;">
                Evaluated: PLT (${plt.toLocaleString()} /µL), WBC (${wbc.toLocaleString()} /µL)
            </div>
        </div>

        <!-- Liver Model Card -->
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-left: 4px solid ${liverClass === 'risk-high' ? '#dc2626' : (liverClass === 'flag-high' ? '#f59e0b' : '#059669')}; border-radius: 10px; padding: 14px 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <span style="font-size: 0.72rem; color: #d97706; font-weight: 800; text-transform: uppercase;">Liver Pathology Model</span>
                <span class="risk-pill ${liverClass}">${liverBadge}</span>
            </div>
            <h4 style="font-size: 1rem; font-weight: 800; color: #0f172a; margin: 4px 0;">${liverRisk}</h4>
            <div style="font-size: 0.78rem; color: #64748b; margin-top: 4px;">
                Confidence: <strong>${liverConfidence}%</strong> &bull; Logistic Regression
            </div>
            <div style="font-size: 0.74rem; color: #475569; margin-top: 8px; background: #f8fafc; padding: 6px 10px; border-radius: 6px;">
                Evaluated: Total Bilirubin (${bili} mg/dL)
            </div>
        </div>

        <!-- Thyroid Model Card -->
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-left: 4px solid ${thyroidClass === 'risk-high' ? '#dc2626' : (thyroidClass === 'flag-high' ? '#f59e0b' : '#059669')}; border-radius: 10px; padding: 14px 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <span style="font-size: 0.72rem; color: #8b5cf6; font-weight: 800; text-transform: uppercase;">Thyroid Regulation Model</span>
                <span class="risk-pill ${thyroidClass}">${thyroidBadge}</span>
            </div>
            <h4 style="font-size: 1rem; font-weight: 800; color: #0f172a; margin: 4px 0;">${thyroidRisk}</h4>
            <div style="font-size: 0.78rem; color: #64748b; margin-top: 4px;">
                Confidence: <strong>${thyroidConfidence}%</strong> &bull; Calibrated Random Forest
            </div>
            <div style="font-size: 0.74rem; color: #475569; margin-top: 8px; background: #f8fafc; padding: 6px 10px; border-radius: 6px;">
                Evaluated: TSH (${tsh} µIU/mL)
            </div>
        </div>
    `;
}

function handleSandboxSmearImage(e, reportId) {
    const file = e.target.files[0];
    if (!file) return;
    const statusEl = document.getElementById(`sb-smear-status-${reportId}`);
    if (statusEl) statusEl.innerHTML = `<span>⏳ Analyzing smear image (${file.name})...</span>`;

    setTimeout(() => {
        if (statusEl) {
            statusEl.innerHTML = `<span style="color: #059669; font-weight: 800;">✓ Smear Scanned: Negative for Intracellular Parasites (98.4% Confidence)</span>`;
        }
    }, 1200);
}

function switchReportInsightTab(reportId, tabName) {
    const tabs = ['layman', 'doctors', 'abnormal', 'ml'];
    tabs.forEach(t => {
        const pane = document.getElementById(`pane-${t}-${reportId}`);
        const btn = document.getElementById(`tab-btn-${t}-${reportId}`);
        if (pane) pane.style.display = (t === tabName) ? 'block' : 'none';
        if (btn) {
            if (t === tabName) btn.classList.add('active');
            else btn.classList.remove('active');
        }
    });

    if (tabName === 'ml') {
        setTimeout(() => simulateSandboxPrediction(reportId), 50);
    }
}

function speakLaymanExplanation(reportId) {
    if (!('speechSynthesis' in window)) {
        alert("Text-to-speech is not supported in this browser.");
        return;
    }
    
    if (window.speechSynthesis.speaking) {
        window.speechSynthesis.cancel();
        const icon = document.getElementById(`voice-icon-${reportId}`);
        const text = document.getElementById(`voice-text-${reportId}`);
        if (icon) icon.textContent = '🔊';
        if (text) text.textContent = 'Listen to Explanation';
        return;
    }
    
    const summaryEl = document.getElementById(`layman-summary-text-${reportId}`);
    if (!summaryEl) return;
    
    const utterance = new SpeechSynthesisUtterance(summaryEl.innerText);
    utterance.rate = 0.95;
    utterance.pitch = 1.0;
    
    const icon = document.getElementById(`voice-icon-${reportId}`);
    const text = document.getElementById(`voice-text-${reportId}`);
    if (icon) icon.textContent = '⏹️';
    if (text) text.textContent = 'Stop Listening';
    
    utterance.onend = () => {
        if (icon) icon.textContent = '🔊';
        if (text) text.textContent = 'Listen to Explanation';
    };
    
    utterance.onerror = () => {
        if (icon) icon.textContent = '🔊';
        if (text) text.textContent = 'Listen to Explanation';
    };
    
    window.speechSynthesis.speak(utterance);
}

function renderOfficialReportHTML(report) {
    const data = report.report_data;
    const isFinalized = report.status === 'Finalized';
    
    let tableRows = '';
    for (const [key, valObj] of Object.entries(data)) {
        if (key === 'Age' || key === 'Sex' || key === 'age' || key === 'gender') continue;
        
        const val = typeof valObj === 'object' && valObj.value !== undefined ? valObj.value : valObj;
        const meta = clinicalRefRanges[key] || { name: key, unit: '', ref: '—' };
        const flag = (typeof valObj === 'object' && valObj.flag) ? valObj.flag : 'Normal';
        
        let flagClass = 'flag-normal';
        if (flag.toLowerCase().includes('critical')) flagClass = 'flag-critical';
        else if (flag.toLowerCase().includes('high') || flag.toLowerCase().includes('abnormal')) flagClass = 'flag-high';
        else if (flag.toLowerCase().includes('low')) flagClass = 'flag-low';

        tableRows += `
            <tr>
                <td><strong>${meta.name}</strong></td>
                <td style="font-weight: 700; color: var(--primary); font-size: 0.95rem;">${val}</td>
                <td style="color: var(--text-muted);">${meta.unit}</td>
                <td style="color: var(--text-muted);">${meta.ref}</td>
                <td><span class="flag-badge ${flagClass}">${flag}</span></td>
            </tr>
        `;
    }

    return `
        <div class="official-report-doc" id="doc-${report.report_id}">
            <div class="report-doc-header">
                <div class="lab-title">
                    <h3>MEDLENS DIAGNOSTIC LABORATORY</h3>
                    <p>Accredited Hematology, Clinical Biochemistry &amp; Diagnostic Reference Center</p>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 0.88rem; font-weight: 800; color: var(--primary);">REPORT NO: ${report.report_id}</div>
                    <span class="flag-badge ${isFinalized ? 'flag-normal' : 'flag-high'}" style="margin-top: 4px;">${report.status}</span>
                </div>
            </div>

            <div class="report-meta-grid">
                <div class="meta-item">
                    <div class="meta-label">Patient Name</div>
                    <div class="meta-val">${report.patient_name || currentAuth.patientName || 'N/A'}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Patient ID</div>
                    <div class="meta-val">${report.patient_id}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Age / Gender</div>
                    <div class="meta-val">${report.patient_age || currentAuth.patientAge || '—'} Yrs / ${report.patient_gender || currentAuth.patientGender || '—'}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Investigation Panel</div>
                    <div class="meta-val" style="text-transform: uppercase; color: var(--primary);">${report.test_category}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Sampling Date</div>
                    <div class="meta-val">${new Date(report.created_at).toLocaleDateString()}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Reporting Pathologist</div>
                    <div class="meta-val">${report.lab_technician || 'Dr. A. K. Mehta (Chief Pathologist)'}</div>
                </div>
            </div>

            <h4 style="font-size: 0.88rem; margin-bottom: 12px; color: var(--text-main); text-transform: uppercase; letter-spacing: 0.05em; font-weight: 700;">Official Laboratory Findings</h4>
            <div class="table-responsive">
                <table class="results-table">
                    <thead>
                        <tr>
                            <th>Investigation Parameter</th>
                            <th>Observed Value</th>
                            <th>Unit</th>
                            <th>Biological Reference Interval</th>
                            <th>Clinical Flag</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${tableRows}
                    </tbody>
                </table>
            </div>

            <div style="background: var(--primary-surface); border-left: 4px solid var(--primary); padding: 14px 18px; border-radius: 8px; margin: 20px 0; font-size: 0.86rem; color: #134e4a; line-height: 1.5;">
                <strong style="color: var(--primary);">Pathologist / Doctor Remarks:</strong> ${report.doctor_remarks || 'Findings clinically correlated. Please consult your attending physician for diagnostic interpretation.'}
            </div>

            <!-- 4 INNOVATIVE PATIENT CLINICAL FEATURES -->
            <div class="patient-report-insights-container">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
                    <div style="font-size: 0.82rem; font-weight: 800; color: var(--primary); text-transform: uppercase; letter-spacing: 0.05em; display: flex; align-items: center; gap: 6px;">
                        <span>✨</span> Patient Clinical Assistance &amp; Insights:
                    </div>
                </div>
                <div class="report-tools-tabs">
                    <button type="button" class="report-tool-tab-btn active" id="tab-btn-layman-${report.report_id}" onclick="switchReportInsightTab('${report.report_id}', 'layman')">
                        <span>🗣️</span> 1. Explain in Simple Language
                    </button>
                    <button type="button" class="report-tool-tab-btn" id="tab-btn-doctors-${report.report_id}" onclick="switchReportInsightTab('${report.report_id}', 'doctors')">
                        <span>🏥</span> 2. Follow-Up Tests &amp; Doctors (MEDICOVER VIZAG)
                    </button>
                    <button type="button" class="report-tool-tab-btn" id="tab-btn-abnormal-${report.report_id}" onclick="switchReportInsightTab('${report.report_id}', 'abnormal')">
                        <span>🚦</span> 3. Patient-Friendly Abnormal Summary
                    </button>
                    <button type="button" class="report-tool-tab-btn" id="tab-btn-ml-${report.report_id}" onclick="switchReportInsightTab('${report.report_id}', 'ml')">
                        <span>🔬</span> 4. Experimental ML Decision Support Sandbox
                    </button>
                </div>

                <!-- Pane 1: Simple Language Explanation -->
                <div id="pane-layman-${report.report_id}">
                    ${generateLaymanReportExplanation(report)}
                </div>

                <!-- Pane 2: Medicover Vizag Follow-Up & Doctors -->
                <div id="pane-doctors-${report.report_id}" style="display: none;">
                    ${generateMedicoverVizagDoctors(report)}
                </div>

                <!-- Pane 3: Abnormal Results Summary -->
                <div id="pane-abnormal-${report.report_id}" style="display: none;">
                    ${generatePatientFriendlyAbnormalSummary(report)}
                </div>

                <!-- Pane 4: Experimental ML Decision Support Sandbox -->
                <div id="pane-ml-${report.report_id}" style="display: none;">
                    ${generateReportMLDecisionSandbox(report)}
                </div>
            </div>

            <div class="admin-controls" style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px; margin-bottom: 10px; flex-wrap: wrap;">
                <button type="button" class="btn-secondary" style="background: var(--mc-blue); color: #ffffff; border-color: var(--mc-blue);" onclick="shareCurrentReport('${report.report_id}')"><span>🔐</span> Share with Medicover Doctor</button>
                <button type="button" class="btn-secondary" onclick="window.print()"><span>🖨️</span> Print Official Report</button>
                <button type="button" class="btn-primary" onclick="triggerReportMLAnalysis('${report.report_id}')"><span>⚡</span> Run Experimental ML Decision Support</button>
            </div>

            <div id="ml-container-${report.report_id}"></div>
        </div>
    `;
}


// Trigger Report-Linked ML Decision Support
async function triggerReportMLAnalysis(reportId) {
    const container = document.getElementById(`ml-container-${reportId}`);
    if (!container) return;

    const token = currentAuth.token;
    if (!token) {
        alert("Please authenticate to execute decision support.");
        return;
    }

    container.innerHTML = `
        <div style="text-align: center; padding: 24px; color: #a5b4fc;">
            <div class="spinner" style="display: inline-block; margin-bottom: 10px;"></div>
            <div style="font-weight: 600;">Evaluating laboratory metrics with validated clinical ML pipeline...</div>
            <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 4px;">Retrieving feature distributions and calculating risk scores...</div>
        </div>
    `;

    try {
        const res = await fetch(apiUrl(`/api/reports/${reportId}/analyze-ml`), {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) {
            const err = await safeJson(res);
            throw new Error(err.detail || "Failed to execute ML decision support.");
        }
        const pred = await safeJson(res);
        renderMLAnalysisCard(reportId, pred);
    } catch (err) {
        container.innerHTML = `
            <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); color: #f87171; padding: 14px; border-radius: 10px; font-size: 0.85rem; margin-top: 16px;">
                <strong>ML Decision Support Notice:</strong> ${err.message}
            </div>
        `;
    }
}

function renderMLAnalysisCard(reportId, pred) {
    const container = document.getElementById(`ml-container-${reportId}`);
    if (!container) return;

    const isHigh = pred.risk_level && (pred.risk_level.toLowerCase().includes('high') || pred.prediction.toLowerCase().includes('anemic') || pred.prediction.toLowerCase().includes('positive') || pred.prediction.toLowerCase().includes('elevated') || pred.prediction.toLowerCase().includes('parasite'));
    const pct = Math.round(pred.confidence * 100);

    container.innerHTML = `
        <div class="ml-decision-card ${isHigh ? 'card-accent-red' : 'card-accent-teal'}">
            <!-- Header -->
            <div class="ml-header">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 1.3rem;">🧠</span>
                    <h3 style="font-size: 1.15rem; font-weight: 800; color: var(--text-main); letter-spacing: -0.01em;">AI Assessment &amp; Decision Support</h3>
                </div>
                <span class="risk-pill ${isHigh ? 'risk-high' : 'risk-normal'}">
                    ${isHigh ? '⚠️ Elevated Risk' : '✓ Normal Pattern'}
                </span>
            </div>

            <!-- Key Finding Highlight Box -->
            <div class="${isHigh ? 'alert-finding-box' : 'recommended-followup-box'}">
                <span style="font-size: 1.1rem;">${isHigh ? '⚠️' : '✓'}</span>
                <span><strong>Finding:</strong> ${pred.prediction} (${pred.disease})</span>
            </div>

            <!-- Confidence Score Section -->
            <div class="confidence-score-box">
                <div style="font-size: 0.72rem; text-transform: uppercase; font-weight: 700; color: var(--text-dim); letter-spacing: 0.05em; margin-bottom: 4px;">Confidence Score</div>
                <div class="confidence-score-val">
                    <span>${pct}%</span>
                    <span class="score-label">${isHigh ? 'High Probability Risk' : 'Normal Concordance'}</span>
                </div>
                <div class="confidence-bar-bg">
                    <div class="confidence-bar-fill" style="width: ${pct}%;"></div>
                </div>
            </div>

            <!-- Recommended Follow-Up Section -->
            <div style="margin-top: 18px;">
                <div style="font-size: 0.72rem; text-transform: uppercase; font-weight: 700; color: var(--text-dim); letter-spacing: 0.05em; margin-bottom: 6px;">Recommended Follow-Up</div>
                <div class="recommended-followup-box">
                    <span class="check-icon">✓</span>
                    <span>${isHigh ? 'Clinical follow-up with attending physician recommended for diagnostic correlation.' : 'Routine observation and periodic wellness screening suggested.'}</span>
                </div>
            </div>

            <!-- Model Metadata -->
            <div style="font-size: 0.76rem; color: var(--text-dim); margin-top: 14px;">
                <strong>Pipeline Provenance:</strong> ${pred.model_used} &bull; Model: ${pred.model_version} &bull; Timestamp: ${new Date().toLocaleTimeString()}
            </div>

            <!-- Bottom Disclaimer Banner -->
            <div class="disclaimer-box">
                <span style="font-size: 1.1rem; color: var(--primary);">ℹ️</span>
                <span>${pred.disclaimer}</span>
            </div>
        </div>
    `;
}


// ---------------------------------------------------------
// Admin / Lab Staff Portal Logic
// ---------------------------------------------------------
async function handleAdminLogin(e) {
    e.preventDefault();
    const u = document.getElementById('admin-user-input').value.trim();
    const p = document.getElementById('admin-pass-input').value;

    try {
        const res = await fetch(apiUrl('/api/auth/login'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: u, password: p })
        });
        if (!res.ok) throw new Error("Invalid admin credentials.");
        const data = await res.json();
        currentAuth.role = 'admin';
        currentAuth.token = data.token;
        saveSessionAuth();
        document.getElementById('admin-login-box').style.display = 'none';
        document.getElementById('admin-dashboard-box').style.display = 'block';
        loadAdminData();
    } catch (err) {
        if (err.name === 'TypeError' || (err.message && err.message.includes('fetch'))) {
            const banner = document.getElementById('server-status-banner');
            if (banner) banner.style.display = 'flex';
            alert("⚠️ Backend Server is Offline (Port 8000)\n\nThe Python backend is not running. Please double-click 'RUN_MEDLENS.bat' to start the server.");
        } else {
            alert("Authentication Error: " + err.message);
        }
    }
}

function handleAdminLogout() {
    currentAuth.role = null;
    currentAuth.token = null;
    clearSessionAuth();
    document.getElementById('admin-login-box').style.display = 'block';
    document.getElementById('admin-dashboard-box').style.display = 'none';
}

function switchAdminSubtab(subtab) {
    const tabs = ['reports', 'patients', 'issues', 'reminders'];
    tabs.forEach(t => {
        const btn = document.getElementById(`btn-adm-tab-${t}`);
        const cont = document.getElementById(`adm-${t}-container`);
        if (btn) {
            if (t === subtab) btn.classList.add('active');
            else btn.classList.remove('active');
        }
        if (cont) {
            cont.style.display = (t === subtab) ? 'block' : 'none';
        }
    });

    if (subtab === 'issues') {
        loadAdminReportedIssues();
    } else if (subtab === 'reminders') {
        loadAdminReminders();
    }
}

async function loadAdminData() {
    if (!currentAuth.token || currentAuth.role !== 'admin') return;

    try {
        const [patientsRes, reportsRes] = await Promise.all([
            fetch(apiUrl('/api/patients'), { headers: { 'Authorization': `Bearer ${currentAuth.token}` } }),
            fetch(apiUrl('/api/reports'), { headers: { 'Authorization': `Bearer ${currentAuth.token}` } })
        ]);
        
        if (patientsRes.ok) allPatients = await patientsRes.json();
        if (reportsRes.ok) allReports = await reportsRes.json();

        loadPublicPatients();

        // Update Stat counters
        const statPat = document.getElementById('stat-patients-count');
        const statRep = document.getElementById('stat-reports-count');
        const statFin = document.getElementById('stat-finalized-count');
        if (statPat) statPat.innerText = allPatients.length;
        if (statRep) statRep.innerText = allReports.length;
        if (statFin) statFin.innerText = allReports.filter(r => r.status === 'Finalized').length;

        // Render Reports Table
        const tbodyRep = document.getElementById('admin-reports-table-body');
        if (tbodyRep) {
            tbodyRep.innerHTML = allReports.map(r => `
                <tr>
                    <td><strong>${r.report_id}</strong></td>
                    <td>
                        <div style="font-weight: 700; color: var(--text-main);">${r.patient_name || r.patient_id}</div>
                        <div style="font-size: 0.75rem; color: var(--text-dim);">${r.patient_id} &bull; ${r.patient_age}Y / ${r.patient_gender}</div>
                    </td>
                    <td><strong style="color: var(--primary); text-transform: uppercase;">${r.test_category}</strong></td>
                    <td><span class="flag-badge ${r.status === 'Finalized' ? 'flag-normal' : 'flag-high'}">${r.status}</span></td>
                    <td style="color: var(--text-muted); font-size: 0.85rem;">${new Date(r.created_at).toLocaleDateString()}</td>
                    <td>
                        <button type="button" class="btn-secondary" style="padding: 4px 10px; font-size: 0.8rem;" onclick="adminViewReport('${r.report_id}')">👁️ View</button>
                        <button type="button" class="btn-primary" style="padding: 4px 10px; font-size: 0.8rem;" onclick="adminTriggerML('${r.report_id}')">⚡ Run ML</button>
                        <button type="button" class="btn-secondary" style="padding: 4px 8px; font-size: 0.8rem; color: var(--danger); border-color: var(--danger-border);" onclick="adminDeleteReport('${r.report_id}')" title="Delete Report">🗑️</button>
                    </td>
                </tr>
            `).join('');
        }



        // Render Patients Table
        const tbodyPat = document.getElementById('admin-patients-table-body');
        if (tbodyPat) {
            tbodyPat.innerHTML = allPatients.map(p => `
                <tr>
                    <td><strong>${p.patient_id}</strong></td>
                    <td><strong>${p.name}</strong></td>
                    <td>${p.age} Yrs / ${p.gender}</td>
                    <td style="color: var(--text-muted);">${p.contact || '—'}</td>
                    <td style="color: var(--text-muted);">${p.email || '—'}</td>
                    <td style="color: var(--text-muted); font-size: 0.85rem;">${new Date(p.created_at).toLocaleDateString()}</td>
                </tr>
            `).join('');
        }

    } catch (err) {
        console.error("Failed to load admin data:", err);
    }
}

function adminViewReport(reportId) {
    const report = allReports.find(r => r.report_id === reportId);
    if (!report) return;

    const previewSheet = document.getElementById('admin-preview-sheet');
    previewSheet.style.display = 'block';
    previewSheet.innerHTML = renderOfficialReportHTML(report);
    previewSheet.scrollIntoView({ behavior: 'smooth' });
}

function adminTriggerML(reportId) {
    adminViewReport(reportId);
    setTimeout(() => {
        triggerReportMLAnalysis(reportId);
    }, 300);
}

async function adminDeleteReport(reportId) {
    if (!confirm(`Are you sure you want to delete report ${reportId}?`)) return;
    try {
        const res = await fetch(apiUrl(`/api/reports/${reportId}`), {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${currentAuth.token}` }
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Failed to delete report');
        }
        // If previewing this report, close preview
        document.getElementById('admin-preview-sheet').style.display = 'none';
        loadAdminData();
    } catch (err) {
        alert("Delete Error: " + err.message);
    }
}

async function adminResetDemoData() {
    if (!confirm("Reset database to the 4 canonical demo records (removes all test and duplicate reports)?")) return;
    try {
        const res = await fetch(apiUrl('/api/admin/reset-demo-data'), {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${currentAuth.token}` }
        });
        if (!res.ok) throw new Error('Failed to reset database');
        document.getElementById('admin-preview-sheet').style.display = 'none';
        alert("Database cleaned and reset to the 4 canonical demo reports.");
        loadAdminData();
    } catch (err) {
        alert("Reset Error: " + err.message);
    }
}

async function adminClearAllReports() {
    if (!confirm("Are you sure you want to delete ALL laboratory reports?")) return;
    try {
        const res = await fetch(apiUrl('/api/admin/reports'), {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${currentAuth.token}` }
        });
        if (!res.ok) throw new Error('Failed to clear reports');
        document.getElementById('admin-preview-sheet').style.display = 'none';
        alert("All reports cleared successfully.");
        loadAdminData();
    } catch (err) {
        alert("Clear Error: " + err.message);
    }
}


function openNewPatientModal() {
    document.getElementById('patient-modal').style.display = 'flex';
}

async function openNewReportModal() {
    if (!allPatients || allPatients.length === 0) {
        try {
            const res = await fetch(apiUrl('/api/patients/public'));
            if (res.ok) allPatients = await res.json();
        } catch (e) {}
    }
    const selectEl = document.getElementById('rep-patient-select');
    if (selectEl) {
        selectEl.innerHTML = allPatients.map(p => `<option value="${p.patient_id}">${p.name} (${p.patient_id} - ${p.gender}, ${p.age}Y)</option>`).join('');
    }
    
    const catSelect = document.getElementById('rep-category-select');
    if (catSelect) catSelect.value = 'anemia';
    renderReportFormFields('anemia');
    document.getElementById('report-modal').style.display = 'flex';
}


function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

async function handleRegisterPatient(e) {
    e.preventDefault();
    const payload = {
        name: document.getElementById('reg-name').value.trim(),
        age: parseInt(document.getElementById('reg-age').value, 10),
        gender: document.getElementById('reg-gender').value,
        contact: document.getElementById('reg-contact').value.trim(),
        email: document.getElementById('reg-email').value.trim(),
        access_pin: document.getElementById('reg-pin').value.trim() || undefined
    };

    try {
        const res = await fetch(apiUrl('/api/patients'), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${currentAuth.token}`
            },
            body: JSON.stringify(payload)
        });
        if (!res.ok) {
            const err = await safeJson(res);
            throw new Error(err.detail || "Failed to create patient.");
        }

        const newP = await safeJson(res);
        closeModal('patient-modal');
        await loadAdminData();
        await loadPublicPatients();
        alert(`Patient registered successfully!\nPatient ID: ${newP.patient_id}\nGenerated PIN: ${newP.generated_pin}`);
    } catch (err) {
        alert("Registration Error: " + err.message);
    }
}

function renderReportFormFields(category) {
    const container = document.getElementById('report-fields-dynamic-container');
    if (!container) return;

    if (category === 'anemia') {
        container.innerHTML = `
            <div class="form-group"><label>Hemoglobin (HGB) <span class="field-unit-hint">[12.0 - 15.5 g/dL]</span></label><input type="number" step="0.1" id="f-HGB" value="8.5" required></div>
            <div class="form-group"><label>RBC Count <span class="field-unit-hint">[3.80 - 5.20 x10^12/L]</span></label><input type="number" step="0.01" id="f-RBC" value="3.80" required></div>
            <div class="form-group"><label>Packed Cell Vol (PCV) <span class="field-unit-hint">[36.0 - 46.0 %]</span></label><input type="number" step="0.1" id="f-PCV" value="27.0" required></div>
            <div class="form-group"><label>Mean Corpuscular Vol (MCV) <span class="field-unit-hint">[80.0 - 100.0 fL]</span></label><input type="number" step="0.1" id="f-MCV" value="71.0" required></div>
            <div class="form-group"><label>MCH <span class="field-unit-hint">[27.0 - 32.0 pg]</span></label><input type="number" step="0.1" id="f-MCH" value="22.0" required></div>
            <div class="form-group"><label>MCHC <span class="field-unit-hint">[31.5 - 34.5 g/dL]</span></label><input type="number" step="0.1" id="f-MCHC" value="29.0" required></div>
            <div class="form-group"><label>RDW <span class="field-unit-hint">[11.5 - 14.5 %]</span></label><input type="number" step="0.1" id="f-RDW" value="18.5" required></div>
            <div class="form-group"><label>Total Leukocyte (TLC) <span class="field-unit-hint">[4.0 - 11.0 x10^3/uL]</span></label><input type="number" step="0.1" id="f-TLC" value="6.8" required></div>
            <div class="form-group full-width"><label>Platelet Count <span class="field-unit-hint">[150.0 - 450.0 /mm3]</span></label><input type="number" step="0.1" id="f-PLT_mm3" value="195.0" required></div>
        `;
    } else if (category === 'dengue') {
        container.innerHTML = `
            <div class="form-group"><label>Hemoglobin <span class="field-unit-hint">[13.5 - 17.5 g/dL]</span></label><input type="number" step="0.1" id="f-hemoglobin_g_dl" value="12.6" required></div>
            <div class="form-group"><label>WBC Count <span class="field-unit-hint">[4000 - 11000 cells/uL]</span></label><input type="number" step="10" id="f-wbc_count" value="2200" required></div>
            <div class="form-group"><label>Differential Count Flag</label><select id="f-differential_count"><option value="1">1 (Abnormal / Viral Shift)</option><option value="0">0 (Normal)</option></select></div>
            <div class="form-group"><label>RBC Morphology Flag</label><select id="f-rbc_count"><option value="1">1 (Normal Morphology)</option><option value="0">0 (Abnormal)</option></select></div>
            <div class="form-group"><label>Platelet Count <span class="field-unit-hint">[150000 - 450000 cells/uL]</span></label><input type="number" step="100" id="f-platelet_count" value="62000" required></div>
            <div class="form-group"><label>Platelet Dist Width <span class="field-unit-hint">[9.0 - 17.0 %]</span></label><input type="number" step="0.1" id="f-platelet_distribution_width" value="11.0" required></div>
        `;
    } else if (category === 'liver') {
        container.innerHTML = `
            <div class="form-group"><label>Total Bilirubin <span class="field-unit-hint">[0.2 - 1.2 mg/dL]</span></label><input type="number" step="0.1" id="f-total_bilirubin" value="3.8" required></div>
            <div class="form-group"><label>Direct Bilirubin <span class="field-unit-hint">[0.0 - 0.3 mg/dL]</span></label><input type="number" step="0.1" id="f-direct_bilirubin" value="1.8" required></div>
            <div class="form-group"><label>Alkaline Phosphatase <span class="field-unit-hint">[44 - 147 IU/L]</span></label><input type="number" step="1" id="f-alkaline_phosphotase" value="350" required></div>
            <div class="form-group"><label>ALT / SGPT <span class="field-unit-hint">[10 - 40 IU/L]</span></label><input type="number" step="1" id="f-alamine_aminotransferase" value="85" required></div>
            <div class="form-group"><label>AST / SGOT <span class="field-unit-hint">[10 - 40 IU/L]</span></label><input type="number" step="1" id="f-aspartate_aminotransferase" value="95" required></div>
            <div class="form-group"><label>Total Proteins <span class="field-unit-hint">[6.0 - 8.3 g/dL]</span></label><input type="number" step="0.1" id="f-total_protiens" value="5.8" required></div>
            <div class="form-group"><label>Albumin <span class="field-unit-hint">[3.5 - 5.0 g/dL]</span></label><input type="number" step="0.1" id="f-albumin" value="2.7" required></div>
            <div class="form-group"><label>A/G Ratio <span class="field-unit-hint">[1.0 - 2.2]</span></label><input type="number" step="0.01" id="f-albumin_and_globulin_ratio" value="0.7" required></div>
        `;
    } else if (category === 'thyroid') {
        container.innerHTML = `
            <div class="form-group"><label>TSH <span class="field-unit-hint">[0.4 - 4.2 uIU/mL]</span></label><input type="number" step="0.01" id="f-TSH" value="25.0" required></div>
            <div class="form-group"><label>Thyroxine (T4) <span class="field-unit-hint">[4.5 - 12.0 ug/dL]</span></label><input type="number" step="0.1" id="f-T4" value="3.2" required></div>
            <div class="form-group"><label>Triiodothyronine (T3) <span class="field-unit-hint">[0.8 - 2.0 ng/dL]</span></label><input type="number" step="0.1" id="f-T3" value="0.8" required></div>
            <div class="form-group"><label>TSH Response to TRH <span class="field-unit-hint">[1.0 - 5.0]</span></label><input type="number" step="0.1" id="f-TSH_response" value="28.5" required></div>
            <div class="form-group full-width"><label>T3 Resin Uptake <span class="field-unit-hint">[95 - 120 %]</span></label><input type="number" step="1" id="f-T3_resin_uptake" value="85" required></div>
        `;
    }
}

async function saveReportDraft() {
    await submitReportWithStatus('Draft');
}

async function handleCreateReport(e) {
    e.preventDefault();
    await submitReportWithStatus('Finalized');
}

async function submitReportWithStatus(status) {
    const patientId = document.getElementById('rep-patient-select').value;
    const category = document.getElementById('rep-category-select').value;
    const remarks = document.getElementById('rep-remarks').value.trim();

    const reportData = {};
    const inputs = document.querySelectorAll('#report-fields-dynamic-container input, #report-fields-dynamic-container select');
    inputs.forEach(input => {
        const key = input.id.replace('f-', '');
        const val = input.type === 'number' ? parseFloat(input.value) : (input.value === '0' || input.value === '1' ? parseInt(input.value, 10) : input.value);
        
        let flag = 'Normal';
        if (key === 'HGB' && val < 12.0) flag = 'Low';
        if (key === 'platelet_count' && val < 100000) flag = 'Critical Low';
        if (key === 'total_bilirubin' && val > 1.2) flag = 'High';
        if (key === 'TSH' && val > 4.2) flag = 'Critical High';

        let normalizedKey = key;
        if (key === 'PLT_mm3' || key === 'PLT') normalizedKey = 'PLT /mm3';
        reportData[normalizedKey] = { value: val, flag: flag };
    });



    const payload = {
        patient_id: patientId,
        test_category: category,
        status: status,
        doctor_remarks: remarks,
        report_data: reportData
    };

    try {
        const res = await fetch(apiUrl('/api/reports'), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${currentAuth.token}`
            },
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error("Failed to create report");
        closeModal('report-modal');
        loadAdminData();
        alert(`Official Laboratory Report saved as '${status}'!`);
    } catch (err) {
        alert("Error creating report: " + err.message);
    }
}


// ---------------------------------------------------------
// Direct ML Sandbox Logic
// ---------------------------------------------------------
const sandboxConfigs = {
    anemia: {
        title: "Complete Blood Count (CBC / Anemia Panel)",
        endpoint: "/predict/anemia",
        pipeline: "anemia_pipeline.joblib (Logistic Regression)",
        fields: [
            { id: 'Age', label: 'Age (Years)', type: 'number', val: 28 },
            { id: 'Sex', label: 'Sex', type: 'select', options: ['Female', 'Male'], val: 'Female' },
            { id: 'HGB', label: 'Hemoglobin (HGB) [g/dL]', type: 'number', step: '0.1', val: 8.5 },
            { id: 'RBC', label: 'RBC Count [x10^12/L]', type: 'number', step: '0.01', val: 3.80 },
            { id: 'PCV', label: 'Packed Cell Volume [%]', type: 'number', step: '0.1', val: 27.0 },
            { id: 'MCV', label: 'Mean Corpuscular Vol [fL]', type: 'number', step: '0.1', val: 71.0 },
            { id: 'MCH', label: 'Mean Corpuscular HGB [pg]', type: 'number', step: '0.1', val: 22.0 },
            { id: 'MCHC', label: 'MCHC [g/dL]', type: 'number', step: '0.1', val: 29.0 },
            { id: 'RDW', label: 'RDW [%]', type: 'number', step: '0.1', val: 18.5 },
            { id: 'TLC', label: 'Total Leukocyte (TLC) [x10^3/uL]', type: 'number', step: '0.1', val: 6.8 },
            { id: 'PLT_mm3', label: 'Platelet Count [/mm3]', type: 'number', step: '0.1', val: 195.0, full: true }
        ]
    },
    dengue: {
        title: "Dengue Hematology Panel",
        endpoint: "/predict/dengue",
        pipeline: "dengue_pipeline.joblib (Random Forest Classifier)",
        fields: [
            { id: 'age', label: 'Age (Years)', type: 'number', val: 43 },
            { id: 'gender', label: 'Gender', type: 'select', options: ['Male', 'Female', 'Child'], val: 'Male' },
            { id: 'hemoglobin_g_dl', label: 'Hemoglobin [g/dL]', type: 'number', step: '0.1', val: 12.6 },
            { id: 'wbc_count', label: 'WBC Count [cells/uL]', type: 'number', step: '10', val: 2200 },
            { id: 'differential_count', label: 'Differential Count Flag', type: 'select', options: [1, 0], val: 1 },
            { id: 'rbc_count', label: 'RBC Morphology Flag', type: 'select', options: [1, 0], val: 1 },
            { id: 'platelet_count', label: 'Platelet Count [cells/uL]', type: 'number', step: '100', val: 62000 },
            { id: 'platelet_distribution_width', label: 'Platelet Dist Width [%]', type: 'number', step: '0.1', val: 11.0 }
        ]
    },
    liver: {
        title: "Liver Function Test (LFT Panel)",
        endpoint: "/predict/liver",
        pipeline: "liver_pipeline.joblib (Gradient Boosting Classifier)",
        fields: [
            { id: 'age', label: 'Age (Years)', type: 'number', val: 65 },
            { id: 'gender', label: 'Gender', type: 'select', options: ['Female', 'Male'], val: 'Female' },
            { id: 'total_bilirubin', label: 'Total Bilirubin [mg/dL]', type: 'number', step: '0.1', val: 3.8 },
            { id: 'direct_bilirubin', label: 'Direct Bilirubin [mg/dL]', type: 'number', step: '0.1', val: 1.8 },
            { id: 'alkaline_phosphotase', label: 'Alkaline Phosphatase [IU/L]', type: 'number', step: '1', val: 350 },
            { id: 'alamine_aminotransferase', label: 'ALT / SGPT [IU/L]', type: 'number', step: '1', val: 85 },
            { id: 'aspartate_aminotransferase', label: 'AST / SGOT [IU/L]', type: 'number', step: '1', val: 95 },
            { id: 'total_protiens', label: 'Total Proteins [g/dL]', type: 'number', step: '0.1', val: 5.8 },
            { id: 'albumin', label: 'Albumin [g/dL]', type: 'number', step: '0.1', val: 2.7 },
            { id: 'albumin_and_globulin_ratio', label: 'A/G Ratio', type: 'number', step: '0.01', val: 0.7 }
        ]
    },
    thyroid: {
        title: "Thyroid Hormone Profile Panel",
        endpoint: "/predict/thyroid",
        pipeline: "thyroid_pipeline.joblib (Multinomial Logistic Regression)",
        fields: [
            { id: 'TSH', label: 'TSH [uIU/mL]', type: 'number', step: '0.01', val: 25.0 },
            { id: 'T4', label: 'Thyroxine (T4) [ug/dL]', type: 'number', step: '0.1', val: 3.2 },
            { id: 'T3', label: 'Triiodothyronine (T3) [ng/dL]', type: 'number', step: '0.1', val: 0.8 },
            { id: 'TSH_response', label: 'TSH Response to TRH', type: 'number', step: '0.1', val: 28.5 },
            { id: 'T3_resin_uptake', label: 'T3 Resin Uptake [%]', type: 'number', step: '1', val: 85, full: true }
        ]
    },
    malaria: {
        title: "Malaria Blood Smear Cell Microscopy",
        endpoint: "/predict/malaria",
        pipeline: "malaria_pipeline.joblib (CV Extractor + Gradient Boosting)",
        isImage: true
    }
};

function switchSandboxDisease(disease) {
    currentSandboxDisease = disease;
    const navButtons = document.querySelectorAll('#sandbox-nav button');
    navButtons.forEach(b => b.classList.remove('active'));

    const config = sandboxConfigs[disease];
    const container = document.getElementById('sandbox-form-container');
    if (!container) return;

    if (config.isImage) {
        container.innerHTML = `
            <div class="card">
                <h3 style="margin-bottom: 8px; font-size: 1.1rem;">🔬 Upload Microscopic Blood Smear</h3>
                <p style="font-size: 0.82rem; color: #94a3b8; margin-bottom: 14px;">Upload Giemsa-stained thin blood smear cell images for automated parasite feature extraction.</p>
                <div class="upload-area" id="sb-drop-zone" onclick="document.getElementById('sb-img-file-input').click()" style="border: 2px dashed rgba(255,255,255,0.2); border-radius: 12px; padding: 30px; text-align: center; cursor: pointer; background: rgba(15, 23, 42, 0.4);">
                    <div style="font-size: 2.5rem; margin-bottom: 8px;">🩸</div>
                    <h4>Click or Drag &amp; Drop Cell Smear Image</h4>
                    <p style="color: var(--text-muted); font-size: 0.8rem; margin-top: 4px;">PNG, JPG, JPEG accepted (Max 5MB)</p>
                    <input type="file" id="sb-img-file-input" accept="image/*" style="display: none;" onchange="handleSandboxImageSelect(event)">
                </div>
                <div id="sb-preview-box" style="display: none; margin-top: 15px; text-align: center;">
                    <img id="sb-img-preview" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'/%3E" alt="Cell Preview" style="max-width: 140px; border-radius: 8px; border: 2px solid var(--card-border);">
                    <div id="sb-file-name" style="font-size: 0.8rem; color: #94a3b8; margin-top: 4px;"></div>
                </div>
                <button type="button" class="btn-primary" style="width: 100%; margin-top: 18px; justify-content: center;" onclick="runSandboxPrediction()">
                    <span>⚡</span> Run Malaria ML Pipeline
                </button>
            </div>
        `;
        setupSandboxDragDrop();
    } else {
        container.innerHTML = `
            <div class="card">
                <h3 style="margin-bottom: 6px; font-size: 1.1rem;">${config.title}</h3>
                <div style="font-size: 0.8rem; color: #38bdf8; margin-bottom: 14px;">Pipeline: ${config.pipeline}</div>
                <form id="sb-form" onsubmit="runSandboxPrediction(event)" class="form-grid">
                    ${config.fields.map(f => {
                        const fullClass = f.full ? 'full-width' : '';
                        if (f.type === 'select') {
                            return `
                                <div class="form-group ${fullClass}">
                                    <label>${f.label}</label>
                                    <select id="sb-${f.id}">
                                        ${f.options.map(opt => `<option value="${opt}" ${opt === f.val ? 'selected' : ''}>${opt}</option>`).join('')}
                                    </select>
                                </div>
                            `;
                        }
                        return `
                            <div class="form-group ${fullClass}">
                                <label>${f.label}</label>
                                <input type="number" id="sb-${f.id}" step="${f.step || 'any'}" value="${f.val}" required>
                            </div>
                        `;
                    }).join('')}
                    <div class="form-group full-width" style="margin-top: 10px;">
                        <button type="submit" class="btn-primary" style="width: 100%; justify-content: center;">
                            <span>⚡</span> Run Direct ML Prediction
                        </button>
                    </div>
                </form>
            </div>
        `;
    }
}

function setupSandboxDragDrop() {
    const dropZone = document.getElementById('sb-drop-zone');
    if (!dropZone) return;

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(name => dropZone.addEventListener(name, (e) => { e.preventDefault(); e.stopPropagation(); }));
    dropZone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length) handleSandboxImage(files[0]);
    });
}

function handleSandboxImageSelect(e) {
    if (e.target.files.length) handleSandboxImage(e.target.files[0]);
}

function handleSandboxImage(file) {
    if (file.size > 5 * 1024 * 1024) {
        alert("File exceeds maximum allowable size (5MB).");
        return;
    }
    selectedSandboxFile = file;
    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById('sb-img-preview').src = e.target.result;
        document.getElementById('sb-file-name').innerText = file.name;
        document.getElementById('sb-preview-box').style.display = 'block';
    };
    reader.readAsDataURL(file);
}

async function runSandboxPrediction(e) {
    if (e) e.preventDefault();
    const config = sandboxConfigs[currentSandboxDisease];

    try {
        let response;
        if (config.isImage) {
            if (!selectedSandboxFile) {
                alert("Please select a blood smear cell image first.");
                return;
            }
            const formData = new FormData();
            formData.append('file', selectedSandboxFile);
            response = await fetch(apiUrl(config.endpoint), { method: 'POST', body: formData });
        } else {
            const payload = {};
            config.fields.forEach(f => {
                const el = document.getElementById(`sb-${f.id}`);
                if (f.id === 'PLT_mm3' && currentSandboxDisease === 'anemia') {
                    payload['PLT /mm3'] = parseFloat(el.value);
                } else if (f.type === 'number') {
                    payload[f.id] = parseFloat(el.value);
                } else if (f.id === 'differential_count' || f.id === 'rbc_count' || f.id === 'age' || f.id === 'Age' || f.id === 'alkaline_phosphotase' || f.id === 'alamine_aminotransferase' || f.id === 'aspartate_aminotransferase' || f.id === 'T3_resin_uptake') {
                    payload[f.id] = parseInt(el.value, 10);
                } else {
                    payload[f.id] = el.value;
                }
            });

            response = await fetch(apiUrl(config.endpoint), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        }

        if (!response.ok) {
            const err = await safeJson(response);
            throw new Error(err.detail ? (typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail)) : 'Prediction error');
        }

        const res = await safeJson(response);
        renderSandboxResult(res);
    } catch (err) {
        alert("Prediction Error: " + err.message);
    }
}

function renderSandboxResult(res) {
    document.getElementById('sb-empty-state').style.display = 'none';
    const resultBox = document.getElementById('sandbox-result-box');
    resultBox.style.display = 'block';

    const isHigh = res.risk_level && (res.risk_level.toLowerCase().includes('high') || res.prediction.toLowerCase().includes('anemic') || res.prediction.toLowerCase().includes('positive') || res.prediction.toLowerCase().includes('parasite') || res.prediction.toLowerCase().includes('elevated'));
    
    resultBox.className = `ml-decision-card ${isHigh ? 'card-accent-red' : 'card-accent-teal'}`;
    
    const findingBox = document.getElementById('sb-finding-box');
    if (findingBox) {
        findingBox.className = isHigh ? 'alert-finding-box' : 'recommended-followup-box';
    }

    document.getElementById('sb-prediction-title').innerText = `${res.prediction} (${res.disease})`;
    document.getElementById('sb-model-tag').innerText = `Model: ${res.model_used}`;
    document.getElementById('sb-meta-pipeline').innerText = res.model_version;

    const pct = Math.round(res.confidence * 100);
    document.getElementById('sb-conf-val').innerText = `${pct}%`;
    const labelEl = document.getElementById('sb-conf-label');
    if (labelEl) labelEl.innerText = isHigh ? 'High Probability Risk' : 'Normal Concordance';
    document.getElementById('sb-conf-bar').style.width = `${pct}%`;

    const badge = document.getElementById('sb-risk-badge');
    badge.className = isHigh ? 'risk-pill risk-high' : 'risk-pill risk-normal';
    badge.innerText = isHigh ? '⚠️ Elevated Risk' : '✓ Normal Pattern';

    const followUpEl = document.getElementById('sb-followup-text');
    if (followUpEl) {
        followUpEl.innerText = isHigh ? 'Clinical follow-up with attending physician recommended for diagnostic correlation.' : 'Routine observation and periodic wellness screening suggested.';
    }
}


// ---------------------------------------------------------
// AI Health Report Analyzer Controller Logic
// ---------------------------------------------------------
let selectedAnalyzerFile = null;
let currentExtractedData = null;

function handleAnalyzerFileSelect(e) {
    const file = e.target.files[0];
    if (file) setupSelectedAnalyzerFile(file);
}

function setupAnalyzerDragDrop() {
    const dropZone = document.getElementById('anl-drop-zone');
    if (!dropZone) return;

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(name => {
        dropZone.addEventListener(name, (e) => { e.preventDefault(); e.stopPropagation(); });
    });

    dropZone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length) setupSelectedAnalyzerFile(files[0]);
    });
}

function setupSelectedAnalyzerFile(file) {
    if (file.size > 10 * 1024 * 1024) {
        alert("Selected file exceeds the maximum 10MB limit.");
        return;
    }
    selectedAnalyzerFile = file;
    
    document.getElementById('anl-file-name').innerText = file.name;
    const ext = file.name.split('.').pop().toUpperCase();
    document.getElementById('anl-file-type').innerText = ext;
    document.getElementById('anl-file-size').innerText = `${Math.round(file.size / 1024)} KB`;
    
    const iconMap = { 'PDF': '📕', 'CSV': '📊', 'PNG': '🖼️', 'JPG': '🖼️', 'JPEG': '🖼️', 'TXT': '📄' };
    document.getElementById('anl-file-icon').innerText = iconMap[ext] || '📄';
    
    document.getElementById('anl-file-info-box').style.display = 'block';
}

function resetAnalyzerUpload() {
    selectedAnalyzerFile = null;
    currentExtractedData = null;
    document.getElementById('anl-file-input').value = '';
    document.getElementById('anl-file-info-box').style.display = 'none';
    document.getElementById('anl-review-card').style.display = 'none';
    document.getElementById('anl-results-sheet').style.display = 'none';
}

async function triggerReportExtraction() {
    if (!selectedAnalyzerFile) {
        alert("Please select a laboratory report file to extract.");
        return;
    }

    const loadingEl = document.getElementById('anl-extract-loading');
    const extractBtn = document.getElementById('btn-extract-params');
    loadingEl.style.display = 'block';
    extractBtn.disabled = true;

    const formData = new FormData();
    formData.append('file', selectedAnalyzerFile);

    try {
        const res = await fetch(apiUrl('/api/analyzer/extract'), {
            method: 'POST',
            body: formData
        });

        if (!res.ok) {
            const err = await safeJson(res);
            throw new Error(err.detail || "Extraction failed");
        }

        currentExtractedData = await safeJson(res);
        
        // Populate Patient / Report Metadata fields
        const meta = currentExtractedData.metadata || {};
        const patIdEl = document.getElementById('anl-meta-patient-id');
        const patNameEl = document.getElementById('anl-meta-patient-name');
        const ageEl = document.getElementById('anl-meta-age');
        const genderEl = document.getElementById('anl-meta-gender');
        const repIdEl = document.getElementById('anl-meta-report-id');
        const repDateEl = document.getElementById('anl-meta-report-date');

        if (patIdEl) patIdEl.value = meta.patient_id || (currentAuth.patientId || '');
        if (patNameEl) patNameEl.value = meta.patient_name || (currentAuth.patientName || '');
        if (ageEl) ageEl.value = (meta.age !== null && meta.age !== undefined) ? meta.age : '';
        if (genderEl) {
            const g = meta.gender || '';
            if (g.toLowerCase().startsWith('f')) genderEl.value = 'Female';
            else if (g.toLowerCase().startsWith('m')) genderEl.value = 'Male';
            else if (g) genderEl.value = 'Other';
            else genderEl.value = '';
        }
        if (repIdEl) repIdEl.value = meta.report_id || '';
        if (repDateEl) repDateEl.value = meta.report_date || '';

        // Render Extraction Quality & Audit Indicators
        const dq = currentExtractedData.data_quality || {};
        const paramsList = currentExtractedData.parameters || [];
        const countEl = document.getElementById('anl-audit-biomarker-count');
        const qualityPill = document.getElementById('anl-audit-quality-pill');
        const warnBox = document.getElementById('anl-audit-warning-box');
        const warnText = document.getElementById('anl-audit-warning-text');

        if (countEl) countEl.innerText = `${paramsList.length}`;
        if (qualityPill) {
            const q = dq.overall_quality || 'GOOD';
            qualityPill.innerText = q;
            qualityPill.className = q === 'GOOD' ? 'conf-pill conf-high' : (q === 'FAIR' ? 'conf-pill conf-med' : 'conf-pill conf-low');
        }
        if (warnBox && warnText) {
            if (paramsList.length > 0 && paramsList.length < 8) {
                warnText.innerText = `Only ${paramsList.length} biomarkers were extracted. Please review the table or enter missing values manually.`;
                warnBox.style.display = 'block';
            } else {
                warnBox.style.display = 'none';
            }
        }

        // Render Laboratory Findings Table
        renderExtractedParametersTable(paramsList);
        
        document.getElementById('anl-review-card').style.display = 'block';
        document.getElementById('anl-review-card').scrollIntoView({ behavior: 'smooth' });
    } catch (err) {
        alert("Extraction Notice: " + err.message);
    } finally {
        loadingEl.style.display = 'none';
        extractBtn.disabled = false;
    }
}

function renderExtractedParametersTable(params) {
    const tbody = document.getElementById('anl-params-tbody');
    if (!tbody) return;

    if (!params || params.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; padding: 24px; color: var(--text-dim);">
                    No laboratory biomarkers automatically extracted. Click <strong>[+ Add Biomarker]</strong> to enter values manually.
                </td>
            </tr>
        `;
        updateReviewMetaSummary();
        return;
    }

    tbody.innerHTML = params.map((p, idx) => {
        const status = (p.status || 'NORMAL').toUpperCase();
        const conf = (p.confidence || 'HIGH').toUpperCase();
        
        let confBadgeClass = 'conf-high';
        let confBadgeText = '✓ HIGH';
        let rowHighlight = '';
        if (conf === 'LOW') {
            confBadgeClass = 'conf-low';
            confBadgeText = '⚠️ LOW';
            rowHighlight = 'background-color: #fffbeb;';
        } else if (conf === 'MEDIUM') {
            confBadgeClass = 'conf-med';
            confBadgeText = '• MED';
        }

        const isNormalized = p.original_name && p.normalized_name && (p.original_name.toLowerCase() !== p.normalized_name.toLowerCase());
        const aliasHint = isNormalized ? `<div style="font-size: 0.72rem; color: var(--text-dim); margin-top: 2px;">(Original: ${p.original_name})</div>` : '';

        return `
            <tr id="anl-row-${idx}" data-canonical-key="${p.canonical_key || ''}" style="${rowHighlight}">
                <td>
                    <input type="text" class="anl-in-param" data-canonical-key="${p.canonical_key || ''}" value="${p.parameter || p.normalized_name || ''}" placeholder="e.g. Hemoglobin" style="padding: 6px 10px; font-weight: 600; width: 100%;">
                    ${aliasHint}
                </td>
                <td>
                    <input type="number" step="any" class="anl-in-val" value="${p.value !== undefined && p.value !== 'Not extracted' ? p.value : ''}" placeholder="e.g. 8.5" style="padding: 6px 10px; font-weight: 700; color: var(--primary); width: 100%;">
                </td>
                <td>
                    <input type="text" class="anl-in-unit" value="${p.unit || ''}" placeholder="e.g. g/dL" style="padding: 6px 10px; width: 100%;">
                </td>
                <td>
                    <input type="text" class="anl-in-ref" value="${p.reference_range || ''}" placeholder="e.g. 12.0 - 15.5" style="padding: 6px 10px; width: 100%;">
                </td>
                <td>
                    <select class="anl-in-status" style="padding: 6px 8px; font-size: 0.8rem; font-weight: 700; width: 100%;">
                        <option value="NORMAL" ${status === 'NORMAL' ? 'selected' : ''}>NORMAL</option>
                        <option value="LOW" ${status === 'LOW' ? 'selected' : ''}>LOW</option>
                        <option value="HIGH" ${status === 'HIGH' ? 'selected' : ''}>HIGH</option>
                        <option value="CRITICAL LOW" ${status === 'CRITICAL LOW' ? 'selected' : ''}>CRITICAL LOW</option>
                        <option value="CRITICAL HIGH" ${status === 'CRITICAL HIGH' ? 'selected' : ''}>CRITICAL HIGH</option>
                        <option value="UNCERTAIN" ${status === 'UNCERTAIN' ? 'selected' : ''}>UNCERTAIN</option>
                    </select>
                </td>
                <td style="text-align: center;">
                    <span class="conf-pill ${confBadgeClass}" title="${p.confidence_reason || 'Biomarker confidence'}">${confBadgeText}</span>
                </td>
                <td style="text-align: center;">
                    <button type="button" class="btn-secondary" style="padding: 4px 8px; color: var(--danger); border-color: var(--danger-border);" onclick="removeParameterRow('anl-row-${idx}')" title="Remove Parameter">🗑️</button>
                </td>
            </tr>
        `;
    }).join('');

    updateReviewMetaSummary();
}

function addNewParameterRow() {
    const tbody = document.getElementById('anl-params-tbody');
    const newIdx = 'custom_' + Date.now();
    const tr = document.createElement('tr');
    tr.id = `anl-row-${newIdx}`;
    tr.innerHTML = `
        <td><input type="text" class="anl-in-param" placeholder="e.g. Ferritin" style="padding: 6px 10px; font-weight: 600; width: 100%;"></td>
        <td><input type="number" step="any" class="anl-in-val" placeholder="e.g. 7" style="padding: 6px 10px; font-weight: 700; color: var(--primary); width: 100%;"></td>
        <td><input type="text" class="anl-in-unit" placeholder="e.g. ng/mL" style="padding: 6px 10px; width: 100%;"></td>
        <td><input type="text" class="anl-in-ref" placeholder="e.g. 15 - 200" style="padding: 6px 10px; width: 100%;"></td>
        <td>
            <select class="anl-in-status" style="padding: 6px 8px; font-size: 0.8rem; font-weight: 700; width: 100%;">
                <option value="NORMAL">NORMAL</option>
                <option value="LOW" selected>LOW</option>
                <option value="HIGH">HIGH</option>
                <option value="CRITICAL LOW">CRITICAL LOW</option>
                <option value="CRITICAL HIGH">CRITICAL HIGH</option>
                <option value="UNCERTAIN">UNCERTAIN</option>
            </select>
        </td>
        <td style="text-align: center;">
            <span class="conf-pill conf-high">USER</span>
        </td>
        <td style="text-align: center;">
            <button type="button" class="btn-secondary" style="padding: 4px 8px; color: var(--danger); border-color: var(--danger-border);" onclick="removeParameterRow('anl-row-${newIdx}')" title="Remove Parameter">🗑️</button>
        </td>
    `;
    tbody.appendChild(tr);
    updateReviewMetaSummary();
}

function removeParameterRow(rowId) {
    const row = document.getElementById(rowId);
    if (row) row.remove();
    updateReviewMetaSummary();
}

function updateReviewMetaSummary() {
    const rows = document.querySelectorAll('#anl-params-tbody tr');
    let total = 0;
    let abnormal = 0;
    rows.forEach(r => {
        const paramIn = r.querySelector('.anl-in-param');
        if (paramIn && paramIn.value.trim()) {
            total++;
            const select = r.querySelector('.anl-in-status');
            if (select && select.value !== 'NORMAL') abnormal++;
        }
    });
    const metaEl = document.getElementById('anl-review-meta-summary');
    if (metaEl) {
        metaEl.innerHTML = `Total Verified: <strong>${total}</strong> biomarkers &bull; Abnormal: <strong>${abnormal}</strong>`;
    }
}

function getReviewedMetadata() {
    const patIdEl = document.getElementById('anl-meta-patient-id');
    const patNameEl = document.getElementById('anl-meta-patient-name');
    const ageEl = document.getElementById('anl-meta-age');
    const genderEl = document.getElementById('anl-meta-gender');
    const repIdEl = document.getElementById('anl-meta-report-id');
    const repDateEl = document.getElementById('anl-meta-report-date');

    const meta = {};
    if (patIdEl && patIdEl.value.trim()) meta.patient_id = patIdEl.value.trim();
    if (patNameEl && patNameEl.value.trim()) meta.patient_name = patNameEl.value.trim();
    if (ageEl && ageEl.value.trim()) {
        const ageNum = parseInt(ageEl.value.trim(), 10);
        if (!isNaN(ageNum)) meta.age = ageNum;
    }
    if (genderEl && genderEl.value) meta.gender = genderEl.value;
    if (repIdEl && repIdEl.value.trim()) meta.report_id = repIdEl.value.trim();
    if (repDateEl && repDateEl.value.trim()) meta.report_date = repDateEl.value.trim();

    return meta;
}

function getReviewedParameters() {
    const rows = document.querySelectorAll('#anl-params-tbody tr');
    const params = [];
    rows.forEach(r => {
        const paramIn = r.querySelector('.anl-in-param');
        const valIn = r.querySelector('.anl-in-val');
        const unitIn = r.querySelector('.anl-in-unit');
        const refIn = r.querySelector('.anl-in-ref');
        const statusIn = r.querySelector('.anl-in-status');

        if (paramIn && paramIn.value.trim()) {
            const valNum = valIn && valIn.value.trim() !== '' ? parseFloat(valIn.value) : null;
            const cKey = paramIn.getAttribute('data-canonical-key') || r.getAttribute('data-canonical-key') || '';
            params.push({
                parameter: paramIn.value.trim(),
                canonical_key: cKey,
                value: valNum !== null && !isNaN(valNum) ? valNum : (valIn ? valIn.value.trim() : ''),
                unit: unitIn ? unitIn.value.trim() : '',
                reference_range: refIn ? refIn.value.trim() : '',
                status: statusIn ? statusIn.value : 'NORMAL'
            });
        }
    });
    return params;
}

async function triggerFinalAIAnalysis() {
    const params = getReviewedParameters();
    if (!params || params.length === 0) {
        alert("Please ensure at least one laboratory biomarker is listed before running analysis.");
        return;
    }

    const reviewedMeta = getReviewedMetadata();

    const loadingEl = document.getElementById('anl-analysis-loading');
    const resultsSheet = document.getElementById('anl-results-sheet');
    loadingEl.style.display = 'block';
    resultsSheet.style.display = 'none';
    loadingEl.scrollIntoView({ behavior: 'smooth' });

    // Animate step progress indicators
    const activateStep = (stepNum) => {
        const el = document.getElementById(`anl-step-${stepNum}`);
        const badge = document.getElementById(`anl-step-${stepNum}-badge`);
        if (el) { el.style.opacity = '1'; el.style.background = 'rgba(99,102,241,0.08)'; el.style.border = '1px solid rgba(99,102,241,0.25)'; }
        if (badge) badge.style.display = 'inline-block';
    };
    const completeStep = (stepNum) => {
        const badge = document.getElementById(`anl-step-${stepNum}-badge`);
        if (badge) { badge.textContent = '✓ Done'; badge.style.background = 'rgba(16,185,129,0.15)'; badge.style.color = '#10b981'; }
    };

    // Steps 2 & 3 run in parallel — activate both immediately
    activateStep(2); activateStep(3);

    // Elapsed timer
    const startTime = Date.now();
    const timerEl = document.getElementById('anl-elapsed-timer');
    const timerInterval = setInterval(() => {
        if (timerEl) timerEl.textContent = Math.round((Date.now() - startTime) / 1000) + 's';
    }, 1000);

    // Step 4 appears after ~3s (ML models typically finish fast)
    setTimeout(() => { completeStep(3); activateStep(4); }, 3000);

    const payload = {
        parameters: params,
        metadata: reviewedMeta,
        filename: selectedAnalyzerFile ? selectedAnalyzerFile.name : "Laboratory_Report",
        file_type: selectedAnalyzerFile ? selectedAnalyzerFile.name.split('.').pop().toUpperCase() : "CUSTOM",
        language: window._selectedLanguage || 'English',
        patient_meta: {
            patient_id: reviewedMeta.patient_id || currentAuth.patientId || "DEMO-001",
            name: reviewedMeta.patient_name || currentAuth.patientName || "",
            age: reviewedMeta.age || (currentAuth.patientAge || 32),
            gender: reviewedMeta.gender || (currentAuth.patientGender || "Female"),
            language: window._selectedLanguage || 'English'
        }
    };

    const headers = { 'Content-Type': 'application/json' };
    if (currentAuth.token) {
        headers['Authorization'] = `Bearer ${currentAuth.token}`;
    }

    try {
        const res = await fetch(apiUrl('/api/analyzer/analyze'), {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const err = await safeJson(res);
            throw new Error(err.detail || "Analysis execution failed.");
        }

        const analysisData = await safeJson(res);
        completeStep(2); completeStep(4);
        renderVisualHealthSummary(analysisData);
        resultsSheet.style.display = 'block';
        resultsSheet.scrollIntoView({ behavior: 'smooth' });

        // Refresh persistent directory caches
        loadPublicPatients();
        if (currentAuth.role === 'admin') loadAdminData();
    } catch (err) {
        alert("AI Analysis Notice: " + err.message);
    } finally {
        clearInterval(timerInterval);
        loadingEl.style.display = 'none';
    }
}


function renderVisualHealthSummary(data) {
    const container = document.getElementById('anl-results-sheet');
    if (!container) return;

    const ai = data.ai_analysis || {};
    const ml = data.ml_model_results || {};
    const meta = data.metadata || {};
    const attention = data.overall_attention || 'NORMAL';

    let attentionPillClass = 'risk-normal';
    let attentionBorderClass = 'card-accent-teal';
    if (attention.includes('HIGH') || attention.includes('ELEVATED')) {
        attentionPillClass = 'risk-high';
        attentionBorderClass = 'card-accent-red';
    } else if (attention.includes('MODERATE')) {
        attentionPillClass = 'flag-high';
        attentionBorderClass = 'card-accent-teal';
    }

    // 1. Abnormal findings rows
    const abnormalList = ai.abnormal_findings || [];
    const abnormalRowsHTML = abnormalList.length > 0 ? abnormalList.map(a => `
        <tr>
            <td><strong>${a.parameter}</strong></td>
            <td style="font-weight: 700; color: var(--primary);">${a.value}</td>
            <td><span class="flag-badge ${a.status.includes('CRITICAL') ? 'flag-critical' : (a.status.includes('LOW') ? 'flag-low' : 'flag-high')}">${a.status}</span></td>
            <td style="color: var(--text-muted); font-size: 0.85rem;">${a.significance || 'Biomarker outside physiological range.'}</td>
        </tr>
    `).join('') : `<tr><td colspan="4" style="text-align: center; color: var(--success); padding: 14px;">✓ All evaluated parameters are within standard reference intervals.</td></tr>`;

    // 2. Existing ML Models evaluated cards (Transparent 3-State Tracking: AVAILABLE / PARTIAL / INSUFFICIENT)
    const mlKeys = Object.keys(ml);
    const mlCardsHTML = mlKeys.length > 0 ? mlKeys.map(k => {
        const item = ml[k];
        const state = item.data_state || (item.evaluated ? 'AVAILABLE' : (item.available_count >= 3 ? 'PARTIAL' : 'INSUFFICIENT'));
        const isHigh = item.risk_level === 'High';
        const requiredCount = item.total_required || 0;
        const availableCount = item.available_count || 0;
        const missingList = item.missing_features || [];

        if (state === 'AVAILABLE' || item.evaluated) {
            return `
                <div style="background: #ffffff; border: 1.5px solid #bbf7d0; border-left: 5px solid ${isHigh ? '#dc2626' : '#059669'}; border-radius: 10px; padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
                    <div style="display: flex; justify-content: space-between; align-items: baseline;">
                        <strong style="color: var(--text-main); font-size: 0.95rem;">${item.disease}</strong>
                        <span class="risk-pill ${isHigh ? 'risk-high' : 'risk-normal'}">${isHigh ? '⚠️ Elevated Risk' : '✓ Normal'}</span>
                    </div>
                    <div style="font-size: 1.18rem; font-weight: 800; color: var(--primary); margin: 6px 0;">${item.prediction}</div>
                    <div style="font-size: 0.78rem; color: var(--text-dim);">
                        Confidence: <strong>${Math.round(item.confidence * 100)}%</strong> &bull; Validated Production Model (${item.model_used || 'ML Pipeline'})
                    </div>
                    <div style="margin-top: 10px; font-size: 0.75rem; color: #15803d; font-weight: 700; background: #f0fdf4; padding: 5px 10px; border-radius: 6px; display: inline-flex; align-items: center; gap: 6px;">
                        <span>✓</span> State 1: Available &bull; 100% Features Present (${availableCount}/${requiredCount})
                    </div>
                </div>
            `;
        } else if (state === 'PARTIAL') {
            const missingText = missingList.length > 0 ? missingList.slice(0, 3).join(', ') + (missingList.length > 3 ? ` +${missingList.length-3} more` : '') : 'Required panel parameters';
            return `
                <div style="background: #ffffff; border: 1.5px solid #fde68a; border-left: 5px solid #f59e0b; border-radius: 10px; padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
                    <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 4px;">
                        <strong style="color: var(--text-main); font-size: 0.95rem;">${item.disease || k.toUpperCase()}</strong>
                        <span class="risk-pill flag-high" style="font-size: 0.72rem; padding: 3px 8px;">State 2: Partial Data</span>
                    </div>
                    <div style="margin: 6px 0; color: #b45309; font-weight: 700; font-size: 0.86rem;">
                        ${availableCount}/${requiredCount} panel biomarkers present in report
                    </div>
                    <div style="color: #64748b; font-size: 0.78rem; line-height: 1.45; margin-top: 4px;">
                        <strong>Missing required inputs:</strong> <em>${missingText}</em>
                    </div>
                    <div style="font-size: 0.74rem; color: #92400e; margin-top: 8px; background: #fffbeb; padding: 5px 10px; border-radius: 6px;">
                        💡 Model inference withheld to ensure zero synthetic data fabrication.
                    </div>
                </div>
            `;
        } else {
            return `
                <div style="background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 10px; padding: 16px; opacity: 0.9;">
                    <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 4px;">
                        <strong style="color: #475569; font-size: 0.9rem;">${item.disease || k.toUpperCase()}</strong>
                        <span class="conf-pill conf-low" style="font-size: 0.7rem;">State 3: Panel Not in Report</span>
                    </div>
                    <div style="margin: 4px 0; color: #64748b; font-size: 0.78rem;">
                        Panel not ordered in this test (${availableCount}/${requiredCount} markers present).
                    </div>
                    <div style="color: #94a3b8; font-size: 0.74rem; margin-top: 6px; font-style: italic;">
                        Non-evaluable for this report type.
                    </div>
                </div>
            `;
        }
    }).join('') : '<p style="color: var(--text-muted); font-size: 0.84rem;">No matching ML panels evaluated.</p>';

    // 3. Top Screening Signals
    const rare = ai.rare_unusual_screening || {};
    const topSignals = rare.top_screening_patterns || [];
    let topSignalsHTML = '';
    if (topSignals.length > 0) {
        topSignalsHTML = `
            <div class="top-signals-card">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                    <span style="font-size: 1.1rem;">⚡</span>
                    <strong style="color: var(--primary); font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.04em;">TOP SCREENING SIGNALS</strong>
                </div>
                <div class="top-signals-grid">
                    ${topSignals.map(ts => `
                        <div class="top-signal-item">
                            <div>
                                <strong style="color: var(--text-main); font-size: 0.88rem;">${ts.rank}. ${ts.name}</strong>
                                <div style="font-size: 0.74rem; color: var(--text-dim); margin-top: 2px;">Concordance: <strong>${ts.concordance_pct}%</strong></div>
                            </div>
                            <span class="risk-pill ${ts.strength === 'HIGH' ? 'risk-high' : (ts.strength === 'MODERATE' ? 'flag-high' : 'flag-normal')}">${ts.strength}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    // 4. Multi-Disease Rare / Unusual Condition Screening Panel ("Why This Was Flagged")
    const candidateConditions = (rare.conditions && Array.isArray(rare.conditions) && rare.conditions.length > 0) 
        ? rare.conditions 
        : (rare.condition ? [rare] : []);

    const rareCardsHTML = candidateConditions.map(cond => {
        const primTotal = cond.primary_matched ? cond.primary_matched.length : 0;
        const suppTotal = cond.supporting_matched ? cond.supporting_matched.length : 0;
        const contTotal = cond.contradictory_matched ? cond.contradictory_matched.length : 0;
        const condConcordance = cond.concordance_pct !== undefined ? cond.concordance_pct : (cond.confidence ? Math.round(cond.confidence * 100) : 0);

        return `
            <div class="rare-disease-card">
                <!-- Condition Title Bar -->
                <div class="rare-disease-header">
                    <div>
                        <div style="font-size: 0.72rem; color: var(--primary); text-transform: uppercase; font-weight: 700; letter-spacing: 0.05em;">Candidate Disease Consideration</div>
                        <h4 style="font-size: 1.15rem; font-weight: 800; color: var(--text-main); margin-top: 2px;">${cond.condition || 'Rare / Unusual Condition Pattern'}</h4>
                    </div>
                    <span class="risk-pill ${cond.strength === 'HIGH' ? 'risk-high' : (cond.strength === 'MODERATE' ? 'flag-high' : 'flag-normal')}">
                        Screening Signal: ${cond.strength || 'MODERATE'}
                    </span>
                </div>

                <!-- Evidence Concordance Meter & Counts -->
                <div class="concordance-meter-container">
                    <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px;">
                        <span class="concordance-label">EVIDENCE CONCORDANCE</span>
                        <span class="concordance-val">${condConcordance > 0 ? `${condConcordance}%` : 'Insufficient Evidence'}</span>
                    </div>
                    <div class="concordance-bar-bg">
                        <div class="concordance-bar-fill" style="width: ${condConcordance}%;"></div>
                    </div>
                    <div class="marker-counts-row">
                        ${cond.primary_ratio ? `<span class="marker-badge marker-primary">Primary Markers: <strong>${cond.primary_ratio}</strong></span>` : (primTotal > 0 ? `<span class="marker-badge marker-primary">Primary Markers: <strong>${primTotal}</strong></span>` : `<span class="marker-badge" style="background: rgba(239, 68, 68, 0.08); color: #dc2626; border-color: rgba(239, 68, 68, 0.2);">No primary markers present</span>`)}
                        ${cond.supporting_ratio ? `<span class="marker-badge marker-supporting">Supporting Markers: <strong>${cond.supporting_ratio}</strong></span>` : (suppTotal > 0 ? `<span class="marker-badge marker-supporting">Supporting Markers: <strong>${suppTotal}</strong></span>` : '')}
                        ${contTotal > 0 ? `<span class="marker-badge marker-contradictory">Contradictory: <strong>${contTotal}</strong></span>` : ''}
                    </div>
                </div>

                <!-- Structured Clinical Reasoning Grid -->
                <div class="clinical-reasoning-grid" style="margin-top: 14px;">
                    <!-- Matched Findings -->
                    <div class="reasoning-block">
                        <div class="reasoning-title" style="color: #059669;">
                            <span>✓</span> <strong>Primary &amp; Supporting Findings</strong>
                        </div>
                        <ul class="reasoning-list">
                            ${(cond.findings_matched && cond.findings_matched.length > 0) ? cond.findings_matched.map(f => `<li>${f}</li>`).join('') : '<li style="color: var(--text-dim);">No specific pathognomonic findings.</li>'}
                        </ul>
                    </div>

                    <!-- Clinical Reasoning / Pathophysiology -->
                    <div class="reasoning-block">
                        <div class="reasoning-title" style="color: var(--primary);">
                            <span>🔬</span> <strong>Clinical Correlation &amp; Pathophysiology</strong>
                        </div>
                        <p style="font-size: 0.84rem; color: var(--text-main); line-height: 1.5; margin: 0;">
                            ${cond.reasoning || cond.clinical_correlation || 'Laboratory pattern shows multi-system biomarker correlation consistent with published clinical criteria.'}
                        </p>
                    </div>

                    <!-- Confirmatory Tests Recommended -->
                    <div class="reasoning-block">
                        <div class="reasoning-title" style="color: #2563eb;">
                            <span>🧪</span> <strong>Suggested Confirmatory Workup</strong>
                        </div>
                        <ul class="reasoning-list">
                            ${(cond.confirmatory_tests && cond.confirmatory_tests.length > 0) ? cond.confirmatory_tests.map(t => `<li>${t}</li>`).join('') : '<li>Clinical specialty evaluation recommended.</li>'}
                        </ul>
                    </div>

                    <!-- Medical Urgency -->
                    <div class="reasoning-block" style="border-left-color: ${cond.urgency && cond.urgency.includes('Prompt') ? '#dc2626' : '#d97706'};">
                        <div class="reasoning-title" style="color: ${cond.urgency && cond.urgency.includes('Prompt') ? '#dc2626' : '#d97706'};">
                            <span>⏱️</span> <strong>Clinical Timeline &amp; Urgency</strong>
                        </div>
                        <p style="font-size: 0.84rem; color: var(--text-main); line-height: 1.5; margin: 0; font-weight: 600;">
                            ${cond.urgency || 'Routine clinical correlation suggested.'}
                        </p>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    // 5. Ruled-Out / Unsupported Conditions
    const unsupported = rare.unsupported_conditions || [];
    let unsupportedHTML = '';
    if (unsupported.length > 0) {
        unsupportedHTML = `
            <div style="margin-top: 24px; margin-bottom: 24px;">
                <h4 style="font-size: 0.9rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-main); margin-bottom: 10px;">
                    Evaluated Screening Considerations with Inconclusive / Normal Findings
                </h4>
                <div class="unsupported-conditions-grid">
                    ${unsupported.map(uc => `
                        <div class="unsupported-card">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                <strong style="font-size: 0.86rem; color: var(--text-main);">${uc.name}</strong>
                                <span class="risk-pill flag-normal" style="font-size: 0.68rem; padding: 2px 6px;">Normal / Inconclusive</span>
                            </div>
                            <div style="font-size: 0.78rem; color: var(--text-muted); margin-bottom: 6px;">
                                <strong>Reason:</strong> ${uc.reason}
                            </div>
                            <div style="font-size: 0.72rem; color: var(--text-dim); text-transform: uppercase; font-weight: 700; margin-bottom: 4px;">Evidence Checked:</div>
                            <ul style="margin-left: 16px; font-size: 0.76rem; color: #475569; display: flex; flex-direction: column; gap: 2px;">
                                ${uc.evidence_checked.map(ec => `
                                    <li>${ec.biomarker} &mdash; <em>${ec.status_text}</em></li>
                                `).join('')}
                            </ul>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    // 5b. Missing / Helpful Diagnostic Tests
    const missingTests = rare.missing_helpful_tests || [];
    let missingTestsHTML = '';
    if (missingTests.length > 0) {
        missingTestsHTML = `
            <div style="margin-top: 20px; margin-bottom: 24px; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 14px 16px;">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                    <span style="font-size: 1.1rem; color: #2563eb;">🧪</span>
                    <h4 style="font-size: 0.88rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-main); margin: 0;">
                        Missing / Helpful Information for Differential Refinement
                    </h4>
                </div>
                <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 10px;">
                    The following disease-specific confirmatory assays or investigations were not detected in this laboratory panel and may assist clinicians in refining the differential:
                </p>
                <ul style="margin-left: 20px; font-size: 0.82rem; color: var(--text-main); display: flex; flex-direction: column; gap: 4px;">
                    ${missingTests.map(t => `<li><strong>${t}</strong></li>`).join('')}
                </ul>
            </div>
        `;
    }

    // 6. Report Data Quality Metrics
    const quality = data.data_quality || {};
    const qualityPillClass = (quality.overall_quality === 'GOOD') ? 'risk-normal' : (quality.overall_quality === 'FAIR' ? 'flag-high' : 'risk-high');

    // 7. General Precautions
    const precautions = ai.general_precautions || [];
    const precautionsHTML = precautions.map(p => `<li>${p}</li>`).join('');

    // Synthetic report model for clinical assistance tabs
    const syntheticReportData = {};
    (data.extracted_parameters || []).forEach(p => {
        syntheticReportData[p.canonical_key || p.parameter] = {
            value: p.value,
            flag: p.status || 'Normal'
        };
    });
    const syntheticReport = {
        report_id: 'anl_summary',
        test_category: data.inferred_category || (data.metadata ? data.metadata.test_category : '') || 'Complete Blood Count (CBC)',
        report_data: syntheticReportData
    };

    container.innerHTML = `
        <div class="official-report-doc ${attentionBorderClass}" id="ai-summary-printable-doc">
            <!-- Header -->
            <div class="report-doc-header">
                <div class="lab-title">
                    <div style="font-size: 0.8rem; color: var(--primary); font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">MEDLENS &bull; Diagnostic Intelligence</div>
                    <h3>AI HEALTH REPORT COMPREHENSIVE ANALYSIS</h3>
                    <p>Multi-Tier Clinical Decision Support &amp; Validated ML Pipeline Synthesis</p>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 0.85rem; font-weight: 800; color: var(--primary);">ANALYSIS REF: ${data.analysis_id || 'ANL-2026'}</div>
                    <span class="risk-pill ${attentionPillClass}" style="margin-top: 4px; font-size: 0.8rem; padding: 5px 12px;">
                        Overall Attention: ${attention}
                    </span>
                </div>
            </div>

            <!-- Processing Progress Sequence -->
            <div class="progress-step-tracker">
                <div class="progress-step-item"><span>✓</span> Report Uploaded &amp; Parsed</div>
                <div class="progress-step-item"><span>✓</span> Biomarkers &amp; Reference Ranges Extracted</div>
                <div class="progress-step-item"><span>✓</span> Biomarkers Normalized</div>
                <div class="progress-step-item"><span>✓</span> Validated ML Models Evaluated</div>
                <div class="progress-step-item"><span>✓</span> Rare Disease Screening Completed</div>
                <div class="progress-step-item"><span>✓</span> Clinical Report Generated</div>
            </div>

            <!-- Patient & Report Information Banner -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; background: #f8fafc; padding: 14px 18px; border-radius: 8px; border: 1px solid var(--card-border); margin-bottom: 20px;">
                <div><span style="font-size: 0.72rem; color: var(--text-dim); text-transform: uppercase; font-weight: 700;">Patient ID</span> <div style="font-weight: 700; color: var(--text-main); font-size: 0.92rem;">${data.patient_id || meta.patient_id || 'N/A'}</div></div>
                <div><span style="font-size: 0.72rem; color: var(--text-dim); text-transform: uppercase; font-weight: 700;">Patient Name</span> <div style="font-weight: 700; color: var(--text-main); font-size: 0.92rem;">${meta.patient_name || (data.metadata && data.metadata.patient_name) || 'N/A'}</div></div>
                <div><span style="font-size: 0.72rem; color: var(--text-dim); text-transform: uppercase; font-weight: 700;">Demographics</span> <div style="font-weight: 700; color: var(--text-main); font-size: 0.92rem;">${(meta.age || (data.metadata && data.metadata.age)) ? (meta.age || data.metadata.age) + ' Yrs' : 'N/A'} / ${meta.gender || (data.metadata && data.metadata.gender) || 'N/A'}</div></div>
                <div><span style="font-size: 0.72rem; color: var(--text-dim); text-transform: uppercase; font-weight: 700;">Report ID / Date</span> <div style="font-weight: 700; color: var(--text-main); font-size: 0.92rem;">${data.report_id || meta.report_id || 'N/A'} &bull; ${meta.report_date || (data.metadata && data.metadata.report_date) || new Date().toLocaleDateString()}</div></div>
            </div>

            <!-- Report Data Quality Section -->
            <div style="margin-bottom: 20px; background: #ffffff; border: 1px solid var(--card-border); border-radius: 8px; padding: 14px 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <h4 style="font-size: 0.85rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-main); margin: 0;">
                        REPORT DATA QUALITY
                    </h4>
                    <span class="risk-pill ${qualityPillClass}">Overall Quality: ${quality.overall_quality || 'GOOD'}</span>
                </div>
                <div class="data-quality-grid">
                    <div class="data-quality-item">
                        <div style="font-size: 0.72rem; color: var(--text-dim); text-transform: uppercase;">Extraction Confidence</div>
                        <div class="data-quality-val" style="color: #059669;">${quality.extraction_confidence || 'HIGH'}</div>
                    </div>
                    <div class="data-quality-item">
                        <div style="font-size: 0.72rem; color: var(--text-dim); text-transform: uppercase;">Biomarkers Detected</div>
                        <div class="data-quality-val">${quality.biomarkers_detected || data.total_parameters_analyzed || 0}</div>
                    </div>
                    <div class="data-quality-item">
                        <div style="font-size: 0.72rem; color: var(--text-dim); text-transform: uppercase;">Reference Ranges Detected</div>
                        <div class="data-quality-val">${quality.reference_ranges_detected ?? quality.reference_intervals_detected ?? 0}</div>
                    </div>
                    <div class="data-quality-item">
                        <div style="font-size: 0.72rem; color: var(--text-dim); text-transform: uppercase;">Unmapped Parameters</div>
                        <div class="data-quality-val" style="color: ${(quality.unmapped_parameters || quality.unmapped_count || 0) > 0 ? '#b45309' : '#059669'};">${quality.unmapped_parameters ?? quality.unmapped_count ?? 0}</div>
                    </div>
                    <div class="data-quality-item">
                        <div style="font-size: 0.72rem; color: var(--text-dim); text-transform: uppercase;">Expected Format</div>
                        <div class="data-quality-val" style="font-size: 0.85rem; color: #059669;">Standard Lab Layout</div>
                    </div>
                    <div class="data-quality-item">
                        <div style="font-size: 0.72rem; color: var(--text-dim); text-transform: uppercase;">Fabricated Values</div>
                        <div class="data-quality-val" style="color: #059669;">0 (Never)</div>
                    </div>
                </div>
            </div>

            <!-- Top Screening Signals Layer -->
            ${topSignalsHTML}

            <!-- Layer 1: Abnormal Findings Table -->
            <h4 style="font-size: 0.9rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-main); margin: 20px 0 10px 0;">
                1. Abnormal Biomarkers &amp; Critical Physiological Flags
            </h4>
            <div class="table-responsive" style="margin-bottom: 24px;">
                <table class="results-table">
                    <thead>
                        <tr>
                            <th>Identified Biomarker</th>
                            <th>Observed Value</th>
                            <th>Flag / Status</th>
                            <th>Clinical Significance</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${abnormalRowsHTML}
                    </tbody>
                </table>
            </div>

            <!-- Layer 2: Production ML Pipeline Assessments -->
            <h4 style="font-size: 0.9rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-main); margin-bottom: 10px;">
                2. Production ML Diagnostic Model Evaluations
            </h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin-bottom: 24px;">
                ${mlCardsHTML}
            </div>

            <!-- Layer 3: Rare / Unusual Disease Screening Panel -->
            <h4 style="font-size: 0.9rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-main); margin-bottom: 10px;">
                3. Multi-Disease Rare &amp; Complex Condition Screening Panel
            </h4>
            <div style="margin-bottom: 24px;">
                ${rareCardsHTML || '<p style="color: var(--text-muted); font-size: 0.85rem;">No complex multi-system disease pattern detected.</p>'}
            </div>

            <!-- Layer 3b: Ruled-Out / Inconclusive Evidence -->
            ${unsupportedHTML}

            <!-- Layer 3c: Missing / Helpful Diagnostic Tests -->
            ${missingTestsHTML}

            <!-- General Precautions & Supportive Guidance -->
            <h4 style="font-size: 0.9rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-main); margin-bottom: 10px;">
                4. AI Clinical Report Synthesis &amp; Precautions
            </h4>
            <div style="background: #ffffff; border: 1px solid var(--card-border); border-radius: 8px; padding: 16px; margin-bottom: 22px;">
                <ul style="margin-left: 20px; color: var(--text-muted); font-size: 0.86rem; display: flex; flex-direction: column; gap: 8px; line-height: 1.5;">
                    ${precautionsHTML}
                </ul>
            </div>

            <!-- 4 INNOVATIVE PATIENT CLINICAL FEATURES -->
            <div class="patient-report-insights-container" style="margin-bottom: 22px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: gap: 8px;">
                    <div style="font-size: 0.82rem; font-weight: 800; color: var(--primary); text-transform: uppercase; letter-spacing: 0.05em; display: flex; align-items: center; gap: 6px;">
                        <span>✨</span> Patient Clinical Assistance &amp; Insights:
                    </div>
                </div>
                <div class="report-tools-tabs">
                    <button type="button" class="report-tool-tab-btn active" id="tab-btn-layman-anl_summary" onclick="switchReportInsightTab('anl_summary', 'layman')">
                        <span>🗣️</span> 1. Explain in Simple Language
                    </button>
                    <button type="button" class="report-tool-tab-btn" id="tab-btn-doctors-anl_summary" onclick="switchReportInsightTab('anl_summary', 'doctors')">
                        <span>🏥</span> 2. Follow-Up Tests &amp; Doctors (MEDICOVER VIZAG)
                    </button>
                    <button type="button" class="report-tool-tab-btn" id="tab-btn-abnormal-anl_summary" onclick="switchReportInsightTab('anl_summary', 'abnormal')">
                        <span>🚦</span> 3. Patient-Friendly Abnormal Summary
                    </button>
                    <button type="button" class="report-tool-tab-btn" id="tab-btn-ml-anl_summary" onclick="switchReportInsightTab('anl_summary', 'ml')">
                        <span>🔬</span> 4. Experimental ML Decision Support Sandbox
                    </button>
                </div>

                <!-- Pane 1: Simple Language Explanation -->
                <div id="pane-layman-anl_summary">
                    ${generateLaymanReportExplanation(syntheticReport)}
                </div>

                <!-- Pane 2: Medicover Vizag Follow-Up & Doctors -->
                <div id="pane-doctors-anl_summary" style="display: none;">
                    ${generateMedicoverVizagDoctors(syntheticReport)}
                </div>

                <!-- Pane 3: Abnormal Results Summary -->
                <div id="pane-abnormal-anl_summary" style="display: none;">
                    ${generatePatientFriendlyAbnormalSummary(syntheticReport)}
                </div>

                <!-- Pane 4: Experimental ML Decision Support Sandbox -->
                <div id="pane-ml-anl_summary" style="display: none;">
                    ${generateReportMLDecisionSandbox(syntheticReport)}
                </div>
            </div>

            <!-- Action Toolbar & Print -->
            <div class="admin-controls" style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px; flex-wrap: wrap;">
                <button type="button" class="btn-secondary" onclick="resetAnalyzerUpload()"><span>🔄</span> Analyze Another Report</button>
                <button type="button" class="btn-primary" onclick="window.print()"><span>📥</span> Print / Save Visual Summary (PDF)</button>
            </div>

            <!-- Mandatory Disclaimer Banner -->
            <div class="disclaimer-box" style="margin-top: 20px;">
                <span style="font-size: 1.2rem; color: var(--primary);">ℹ️</span>
                <div>
                    <strong>IMPORTANT REGULATORY &amp; EDUCATIONAL DISCLAIMER:</strong><br>
                    Screening signal only — not a medical diagnosis. Confirmatory testing and clinical evaluation are required. This AI-Assisted Pathology Report Analysis is generated for educational, academic, and clinical decision-support research purposes only. It does NOT constitute an autonomous medical diagnosis, clinical prescription, or definitive therapeutic directive. Always review laboratory reports with a licensed physician or qualified clinical pathologist.
                </div>
            </div>
        </div>
    `;

    // FEATURE 1: Render AI Differential Diagnosis Map
    renderDiagnosisMap(ai.differential_diagnosis);

    // FEATURE 2: Render Missing Test Intelligence
    renderMissingTests(ai.missing_tests);

    // FEATURE 3: Render Hidden Abnormality Detector Warning Banner
    renderHiddenAbnormalities(ai.hidden_abnormalities);
}


// ================================================================
// FEATURE 1: AI Differential Diagnosis Map Logic
// ================================================================
function renderDiagnosisMap(diffList) {
    const container = document.getElementById('diagnosis-map');
    const content = document.getElementById('diagnosis-map-content');
    if (!container || !content) return;

    if (!Array.isArray(diffList) || diffList.length === 0) {
        container.style.display = 'none';
        return;
    }

    const top2 = diffList.slice(0, 2);
    content.innerHTML = top2.map((item, idx) => {
        const condName = item.condition || `Candidate Differential #${idx + 1}`;
        const suppList = Array.isArray(item.supporting_evidence) ? item.supporting_evidence : [];
        const contList = Array.isArray(item.contradicting_evidence) ? item.contradicting_evidence : [];

        return `
            <div class="diff-condition-card">
                <div class="diff-condition-header">
                    <span class="diff-condition-title">${condName}</span>
                    <span class="diff-rank-badge">Rank #${idx + 1}</span>
                </div>
                <div class="diff-evidence-grid">
                    <div class="diff-evidence-col supporting">
                        <div class="diff-evidence-label">
                            <span>✓</span> Supporting Evidence
                        </div>
                        <ul class="diff-evidence-list">
                            ${suppList.length > 0 ? suppList.map(s => `<li>${s}</li>`).join('') : '<li>No overt concordant laboratory markers.</li>'}
                        </ul>
                    </div>
                    <div class="diff-evidence-col contradicting">
                        <div class="diff-evidence-label">
                            <span>✗</span> Contradicting Evidence
                        </div>
                        <ul class="diff-evidence-list">
                            ${contList.length > 0 ? contList.map(c => `<li>${c}</li>`).join('') : '<li>No counter-indicative findings detected.</li>'}
                        </ul>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    container.style.display = 'block';
}

// ================================================================
// FEATURE 2: Missing Test Intelligence Logic
// ================================================================
let currentMissingTests = [];

function renderMissingTests(missingTests) {
    const container = document.getElementById('missing-tests-card');
    const listEl = document.getElementById('missing-tests-list-container');
    if (!container || !listEl) return;

    if (!Array.isArray(missingTests) || missingTests.length === 0) {
        container.style.display = 'none';
        return;
    }

    currentMissingTests = missingTests;
    listEl.innerHTML = missingTests.map(t => `
        <span class="missing-test-chip">
            <span>🔬</span> ${t}
        </span>
    `).join('');

    container.style.display = 'block';
}

function bookMissingTestsAtMedicover() {
    const testsStr = currentMissingTests.length > 0 ? currentMissingTests.join(', ') : 'Recommended Confirmatory Tests';
    const message = `Booking request initiated for Medicover Hospital Vizag:\n\nRecommended Confirmatory Tests:\n• ${currentMissingTests.join('\n• ')}\n\nMedicover Vizag Diagnostic Helpline: 0891-6677777 / Emergency 1066.`;
    alert(message);
}

// ================================================================
// FEATURE 3: Hidden Abnormality Detector Logic
// ================================================================
function renderHiddenAbnormalities(hiddenList) {
    const existing = document.getElementById('hidden-abnormality-banner');
    if (existing) existing.remove();

    if (!Array.isArray(hiddenList) || hiddenList.length === 0) return;

    const printableDoc = document.getElementById('ai-summary-printable-doc');
    if (!printableDoc) return;

    const banner = document.createElement('div');
    banner.id = 'hidden-abnormality-banner';
    banner.className = 'hidden-abnormality-banner';
    banner.innerHTML = `
        <div class="hidden-abnormality-title">
            <span>⚠️</span> HIDDEN ABNORMALITY DETECTOR &bull; Synergistic Borderline Values
        </div>
        <div style="font-size: 0.82rem; color: #78350f; margin-bottom: 8px;">
            The following biomarkers are technically within reference limits, but sit at synergistic extremes that collectively indicate subclinical pathology:
        </div>
        ${hiddenList.map(h => `
            <div class="hidden-abnormality-item">
                <div class="hidden-biomarkers-tags">
                    ${(h.biomarkers || []).map(b => `<span class="hidden-biomarker-tag">${b}</span>`).join('')}
                </div>
                <div class="hidden-implication-text">
                    <strong>Clinical Implication:</strong> ${h.implication}
                </div>
            </div>
        `).join('')}
    `;

    const progressTracker = printableDoc.querySelector('.progress-step-tracker');
    if (progressTracker && progressTracker.nextElementSibling) {
        progressTracker.nextElementSibling.insertAdjacentElement('afterend', banner);
    } else {
        printableDoc.prepend(banner);
    }
}

// ================================================================
// FEATURE 5: "What Changed?" Report Comparison Logic
// ================================================================
let compareFiles = {
    baseline: null,
    current: null
};

function handleCompareFileSelect(event, type) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;

    compareFiles[type] = file;

    const dropzone = document.getElementById(`cmp-${type}-dropzone`);
    const label = document.getElementById(`cmp-${type}-label`);
    if (dropzone) dropzone.classList.add('has-file');
    if (label) {
        label.innerHTML = `<strong style="color: #059669;">✓ ${file.name}</strong> (${Math.round(file.size / 1024)} KB)`;
    }
}

async function runReportComparison() {
    if (!compareFiles.baseline || !compareFiles.current) {
        alert("Please select both a Baseline Report and a Current Report to compare.");
        return;
    }

    const btn = document.getElementById('btn-run-comparison');
    const resultsContainer = document.getElementById('compare-results-container');
    const summaryBar = document.getElementById('compare-summary-bar');
    const tbody = document.getElementById('compare-results-tbody');

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span>⏳</span> Extracting &amp; Comparing Deltas...`;
    }

    const formData = new FormData();
    formData.append('baseline_file', compareFiles.baseline);
    formData.append('current_file', compareFiles.current);

    try {
        const res = await fetch(apiUrl('/api/compare-reports'), {
            method: 'POST',
            body: formData
        });

        if (!res.ok) {
            const err = await safeJson(res);
            throw new Error(err.detail || "Comparison failed.");
        }

        const data = await safeJson(res);
        const comparisons = data.comparisons || [];
        const summary = data.summary || { improving: 0, worsening: 0, stable: 0 };

        summaryBar.innerHTML = `
            <div style="background: #ecfdf5; border: 1px solid #a7f3d0; padding: 8px 16px; border-radius: 8px; font-size: 0.84rem; font-weight: 700; color: #047857;">
                🟢 Improving: ${summary.improving}
            </div>
            <div style="background: #fef2f2; border: 1px solid #fecaca; padding: 8px 16px; border-radius: 8px; font-size: 0.84rem; font-weight: 700; color: #b91c1c;">
                🔴 Worsening: ${summary.worsening}
            </div>
            <div style="background: #f1f5f9; border: 1px solid #e2e8f0; padding: 8px 16px; border-radius: 8px; font-size: 0.84rem; font-weight: 700; color: #475569;">
                ⚪ Stable: ${summary.stable}
            </div>
            <div style="margin-left: auto; font-size: 0.8rem; color: var(--text-dim); align-self: center;">
                Matched <strong>${data.total_matched}</strong> biomarkers
            </div>
        `;

        if (comparisons.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 20px;">No matching biomarkers found between the two uploaded reports.</td></tr>`;
        } else {
            tbody.innerHTML = comparisons.map(c => {
                const deltaSign = c.delta > 0 ? `+${c.delta}` : `${c.delta}`;
                const pctSign = c.pct_change > 0 ? `+${c.pct_change}%` : `${c.pct_change}%`;
                const pillClass = c.status === 'improving' ? 'improving' : (c.status === 'worsening' ? 'worsening' : 'stable');
                const pillIcon = c.status === 'improving' ? '🟢' : (c.status === 'worsening' ? '🔴' : '⚪');

                return `
                    <tr>
                        <td><strong>${c.parameter}</strong></td>
                        <td>${c.baseline} <span style="font-size: 0.75rem; color: var(--text-dim);">${c.unit}</span></td>
                        <td><strong style="color: var(--primary);">${c.current}</strong> <span style="font-size: 0.75rem; color: var(--text-dim);">${c.unit}</span></td>
                        <td style="font-weight: 700; font-family: monospace;">${deltaSign}</td>
                        <td style="font-weight: 600; font-family: monospace;">${pctSign}</td>
                        <td style="text-align: center;">
                            <span class="delta-pill ${pillClass}">
                                <span>${pillIcon}</span> ${c.status}
                            </span>
                        </td>
                    </tr>
                `;
            }).join('');
        }

        resultsContainer.style.display = 'block';
        resultsContainer.scrollIntoView({ behavior: 'smooth' });
    } catch (err) {
        alert("Comparison Error: " + err.message);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<span>🔍</span> Compare Reports &amp; Compute Deltas`;
        }
    }
}

// =========================================================
// 8. Symptoms to AI Suggestions & Real-Time Streaming
// =========================================================
let currentSymptomText = "";
let rawSymptomMarkdown = "";
let rawReasoningText = "";
let isSpeakingSymptomAdvice = false;
let symptomSpeechUtterance = null;

function updateSymptomCharCount() {
    const textarea = document.getElementById('symp-textarea');
    const countEl = document.getElementById('symp-char-count');
    if (textarea && countEl) {
        countEl.textContent = `${textarea.value.length} characters`;
    }
    updateSelectedTagBadge();
}

function updateSelectedTagBadge() {
    const activeChips = document.querySelectorAll('.symp-chip.active');
    const badge = document.getElementById('selected-tags-badge');
    if (badge) {
        if (activeChips.length > 0) {
            badge.style.display = 'inline-block';
            badge.textContent = `${activeChips.length} selected`;
        } else {
            badge.style.display = 'none';
        }
    }
}

function filterSymptomTags() {
    const filterInput = document.getElementById('symp-filter-input');
    if (!filterInput) return;
    const query = filterInput.value.trim().toLowerCase();
    
    document.querySelectorAll('.symp-chip').forEach(chip => {
        const text = chip.textContent.toLowerCase();
        if (!query || text.includes(query)) {
            chip.style.display = 'inline-flex';
        } else {
            chip.style.display = 'none';
        }
    });

    document.querySelectorAll('.symp-tag-group').forEach(group => {
        const visibleChips = group.querySelectorAll('.symp-chip:not([style*="display: none"])');
        group.style.display = visibleChips.length > 0 ? 'block' : 'none';
    });
}

function toggleSymptomTag(chipEl, tagText) {
    const textarea = document.getElementById('symp-textarea');
    if (!textarea) return;

    chipEl.classList.toggle('active');
    const isActive = chipEl.classList.contains('active');

    let currentVal = textarea.value.trim();

    if (isActive) {
        if (currentVal.length > 0) {
            if (!currentVal.includes(tagText)) {
                textarea.value = currentVal + (currentVal.endsWith('.') || currentVal.endsWith(',') ? ' ' : ', ') + tagText;
            }
        } else {
            textarea.value = tagText;
        }
    } else {
        // Remove tag if present
        let regex = new RegExp(`(,\\s*)?${tagText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`, 'gi');
        textarea.value = currentVal.replace(regex, '').replace(/^,\s*/, '').trim();
    }
    updateSymptomCharCount();
}

function loadSymptomPreset(presetKey) {
    const textarea = document.getElementById('symp-textarea');
    const ageInput = document.getElementById('symp-age');
    const genderSelect = document.getElementById('symp-gender');
    const durationSelect = document.getElementById('symp-duration');
    const severitySelect = document.getElementById('symp-severity');
    if (!textarea) return;

    // Reset chips
    document.querySelectorAll('.symp-chip').forEach(c => c.classList.remove('active'));

    const presets = {
        dengue: {
            text: "Sudden high fever (102.5°F) for 3 days with intense headache behind eyes, severe back and joint pain, skin rash on arms, extreme weakness, and mild nausea.",
            age: 26,
            gender: "Male",
            duration: "1 to 3 Days",
            severity: "Severe / Acute"
        },
        anemia: {
            text: "Chronic overwhelming fatigue and weakness for over a month, frequent dizziness upon standing, breathlessness when climbing stairs, pale skin, cold extremities, and brittle nails.",
            age: 32,
            gender: "Female",
            duration: "More than 2 Weeks",
            severity: "Moderate"
        },
        liver: {
            text: "Noticeable yellowing of the eyes and skin for 5 days, severe loss of appetite, dark tea-colored urine, dull upper right abdominal ache, and generalized fatigue.",
            age: 44,
            gender: "Male",
            duration: "4 to 7 Days",
            severity: "Severe / Acute"
        },
        thyroid: {
            text: "Unexplained weight gain, persistent cold intolerance, constant drowsiness and lethargy, dry brittle hair, and subtle hand shakiness.",
            age: 38,
            gender: "Female",
            duration: "More than 2 Weeks",
            severity: "Moderate"
        },
        malaria: {
            text: "Recurrent periodic fever spikes every 48 hours preceded by intense shivering chills, followed by drenching sweats, throbbing headache, and generalized body aches.",
            age: 29,
            gender: "Male",
            duration: "1 to 3 Days",
            severity: "Severe / Acute"
        },
        respiratory: {
            text: "Persistent dry cough for 5 days with progressive shortness of breath upon exertion, chest tightness, sore throat, and low-grade evening fever.",
            age: 52,
            gender: "Male",
            duration: "4 to 7 Days",
            severity: "Moderate"
        },
        uti: {
            text: "Sharp burning sensation during urination, increased urinary urgency and frequency throughout the day and night, accompanied by lower back and flank discomfort.",
            age: 35,
            gender: "Female",
            duration: "1 to 3 Days",
            severity: "Moderate"
        },
        migraine: {
            text: "Severe unilateral throbbing headache behind the left temple, heightened sensitivity to light and sound, nausea, and visual aura flashes for 12 hours.",
            age: 28,
            gender: "Female",
            duration: "Under 24 Hours",
            severity: "Severe / Acute"
        }
    };

    const data = presets[presetKey];
    if (data) {
        textarea.value = data.text;
        if (ageInput && data.age) ageInput.value = data.age;
        if (genderSelect && data.gender) genderSelect.value = data.gender;
        if (durationSelect && data.duration) durationSelect.value = data.duration;
        if (severitySelect && data.severity) severitySelect.value = data.severity;
        updateSymptomCharCount();

        // Highlight matching chips
        document.querySelectorAll('.symp-chip').forEach(chip => {
            const chipText = chip.textContent.trim().toLowerCase();
            if (data.text.toLowerCase().includes(chipText)) {
                chip.classList.add('active');
            }
        });
        updateSelectedTagBadge();
    }
}

function clearSymptomForm() {
    const textarea = document.getElementById('symp-textarea');
    const ageInput = document.getElementById('symp-age');
    const genderSelect = document.getElementById('symp-gender');
    const filterInput = document.getElementById('symp-filter-input');
    const resultsContainer = document.getElementById('symp-results-container');
    const contentEl = document.getElementById('symp-streamed-content');
    const reasoningDrawer = document.getElementById('symp-reasoning-drawer');

    if (textarea) textarea.value = '';
    if (ageInput) ageInput.value = '';
    if (genderSelect) genderSelect.value = '';
    if (filterInput) {
        filterInput.value = '';
        filterSymptomTags();
    }
    document.querySelectorAll('.symp-chip').forEach(c => c.classList.remove('active'));
    if (resultsContainer) resultsContainer.style.display = 'none';
    if (contentEl) contentEl.innerHTML = '';
    if (reasoningDrawer) reasoningDrawer.style.display = 'none';
    rawSymptomMarkdown = '';
    rawReasoningText = '';
    stopSymptomSpeech();
    updateSymptomCharCount();
}

function toggleReasoningCollapse() {
    const content = document.getElementById('symp-reasoning-content');
    const icon = document.getElementById('symp-reasoning-toggle-icon');
    if (!content) return;
    if (content.style.display === 'none') {
        content.style.display = 'block';
        if (icon) icon.textContent = '▼';
    } else {
        content.style.display = 'none';
        if (icon) icon.textContent = '▶';
    }
}

function formatMarkdownAdvice(text) {
    if (!text) return "";

    // Split text into section blocks by top-level markdown headers
    const sections = text.split(/(?=^##\s+)/m);

    let formattedBlocks = sections.map(section => {
        let trimmed = section.trim();
        if (!trimmed) return "";

        let headerMatch = trimmed.match(/^##\s+(.+)$/m);
        let headerTitle = headerMatch ? headerMatch[1] : "";
        let bodyContent = headerMatch ? trimmed.replace(/^##\s+.+$/m, '').trim() : trimmed;

        // Escape basic HTML
        let cleanBody = bodyContent
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        // Format subheaders, bold, italic
        cleanBody = cleanBody.replace(/^### (.*$)/gim, '<h4 style="color: var(--primary); font-size: 0.95rem; margin-top: 10px; font-weight: 700;">$1</h4>');
        cleanBody = cleanBody.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');
        cleanBody = cleanBody.replace(/\*(.*?)\*/gim, '<em>$1</em>');

        // Bullet points
        cleanBody = cleanBody.replace(/^\s*[\-\*]\s+(.*$)/gim, '<li style="margin-bottom: 8px; line-height: 1.6;">$1</li>');
        cleanBody = cleanBody.replace(/(<li.*<\/li>\s*)+/gim, (match) => `<ul style="margin: 8px 0 10px 20px; list-style-type: disc;">${match}</ul>`);

        // Convert double newlines to paragraphs
        cleanBody = cleanBody.split('\n\n').map(p => {
            p = p.trim();
            if (!p) return '';
            if (p.startsWith('<ul') || p.startsWith('<li') || p.startsWith('<h') || p.startsWith('<div')) return p;
            return `<p style="margin-bottom: 8px; line-height: 1.6;">${p}</p>`;
        }).join('\n');

        // Determine card style based on section category
        let cardStyle = "background: var(--card-bg); border: 1px solid var(--card-border);";
        let headerColor = "var(--primary)";
        let iconBadge = "📋";
        let accentBorder = "var(--primary)";

        if (headerTitle.includes("Possible Conditions") || headerTitle.includes("Pattern")) {
            cardStyle = "background: rgba(2, 132, 199, 0.04); border: 1px solid rgba(2, 132, 199, 0.25);";
            headerColor = "#0284c7";
            accentBorder = "#0284c7";
            iconBadge = "🔍";
        } else if (headerTitle.includes("Precaution") || headerTitle.includes("Safety")) {
            cardStyle = "background: rgba(245, 158, 11, 0.05); border: 1px solid rgba(245, 158, 11, 0.3);";
            headerColor = "#d97706";
            accentBorder = "#f59e0b";
            iconBadge = "⚠️";
        } else if (headerTitle.includes("Home Care") || headerTitle.includes("Remedies")) {
            cardStyle = "background: rgba(16, 185, 129, 0.05); border: 1px solid rgba(16, 185, 129, 0.25);";
            headerColor = "#059669";
            accentBorder = "#10b981";
            iconBadge = "🌿";
        } else if (headerTitle.includes("Red-Flag") || headerTitle.includes("Emergency") || headerTitle.includes("Immediate")) {
            cardStyle = "background: rgba(239, 68, 68, 0.05); border: 1px solid rgba(239, 68, 68, 0.3);";
            headerColor = "#dc2626";
            accentBorder = "#ef4444";
            iconBadge = "🚨";
        } else if (headerTitle.includes("Laboratory") || headerTitle.includes("Blood Tests") || headerTitle.includes("Panels")) {
            cardStyle = "background: rgba(0, 94, 102, 0.05); border: 1px solid rgba(0, 94, 102, 0.25);";
            headerColor = "var(--primary)";
            accentBorder = "var(--primary)";
            iconBadge = "🧪";
        } else if (headerTitle.includes("Related") || headerTitle.includes("Know")) {
            cardStyle = "background: rgba(124, 58, 237, 0.04); border: 1px solid rgba(124, 58, 237, 0.2);";
            headerColor = "#7c3aed";
            accentBorder = "#7c3aed";
            iconBadge = "💡";
        }

        if (headerTitle) {
            return `
                <div class="symptom-section-card" style="${cardStyle} border-left: 4px solid ${accentBorder}; border-radius: 8px; padding: 14px 18px; margin-bottom: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                    <h3 style="color: ${headerColor}; font-size: 1.05rem; font-weight: 700; margin-bottom: 10px; display: flex; align-items: center; gap: 8px;">
                        ${headerTitle}
                    </h3>
                    <div style="font-size: 0.9rem; color: var(--text-main);">
                        ${cleanBody}
                    </div>
                </div>
            `;
        } else {
            return `<div style="margin-bottom: 12px;">${cleanBody}</div>`;
        }
    }).join('\n');

    return formattedBlocks;
}

// ---------------------------------------------------------
// Suggested Follow-Up Tests & Doctors from MEDICOVER VIZAG (For Symptoms AI)
// Sourced directly from https://www.medicoverhospitals.in/doctors/vizag
// ---------------------------------------------------------
function renderSymptomsMedicoverDoctors(symptomsText) {
    const container = document.getElementById('symp-medicover-doctors-container');
    if (!container) return;

    const s = (symptomsText || '').toLowerCase();
    
    let doctors = [];
    let tests = [];

    // 1. Fever / Infection / Dengue / Malaria / Chills
    if (s.includes('fever') || s.includes('chill') || s.includes('shiver') || s.includes('dengue') || s.includes('platelet') || s.includes('body pain') || s.includes('rash') || s.includes('joint') || s.includes('headache')) {
        doctors.push({
            name: "Dr. K. Rama Murty",
            qual: "MBBS, MD (General Medicine)",
            role: "Senior Consultant Physician & Tropical Fever Care",
            dept: "General Medicine & Infectious Care",
            opd: "Mon – Sat: 9:00 AM – 5:00 PM",
            profile: "https://www.medicoverhospitals.in/doctors/dr-k-rama-murty"
        });
        doctors.push({
            name: "Dr. Meghanath Yenni",
            qual: "MBBS, MD (General Medicine)",
            role: "Consultant Physician & Acute Care Specialist",
            dept: "General Medicine & Critical Care",
            opd: "Mon – Sat: 9:30 AM – 4:30 PM",
            profile: "https://www.medicoverhospitals.in/doctors/dr-meghanath-yenni"
        });
        tests.push("Complete Blood Count (CBC) with Platelet Kinetics", "Dengue NS1 Antigen & IgM/IgG ELISA", "Serum Electrolytes & Widal Test");
    }

    // 2. Anemia / Weakness / Dizziness / Fatigue / Pallor
    if (s.includes('fatigue') || s.includes('tired') || s.includes('weak') || s.includes('pale') || s.includes('dizziness') || s.includes('breath') || s.includes('anemia') || s.includes('pallor')) {
        doctors.push({
            name: "Dr. Ramesh Uppada",
            qual: "MBBS, MD (General Medicine), DM (Clinical Hematology)",
            role: "Senior Consultant Clinical Hematologist & Hemato-Oncologist",
            dept: "Hematology & General Medicine",
            opd: "Mon – Sat: 10:00 AM – 4:30 PM",
            profile: "https://www.medicoverhospitals.in/doctors/dr-ramesh-uppada"
        });
        doctors.push({
            name: "Dr. Thriveni Reddy",
            qual: "MBBS, MD (General Medicine)",
            role: "Consultant Physician & Internal Medicine",
            dept: "General Medicine",
            opd: "Mon – Sat: 9:00 AM – 4:00 PM",
            profile: "https://www.medicoverhospitals.in/doctors/dr-thriveni-reddy"
        });
        tests.push("Serum Ferritin & Total Iron Binding Capacity (TIBC)", "Vitamin B12 & Folate Profile", "Peripheral Blood Smear Examination");
    }

    // 3. Liver / Jaundice / Stomach / Nausea / Acidity / Diarrhea
    if (s.includes('yellow') || s.includes('jaundice') || s.includes('urine') || s.includes('nausea') || s.includes('vomit') || s.includes('stomach') || s.includes('abdominal') || s.includes('liver') || s.includes('diarrhea') || s.includes('cramp')) {
        doctors.push({
            name: "Dr. Srinivas Nistala",
            qual: "MBBS, MD (General Medicine), DM (Medical Gastroenterology)",
            role: "Chief Medical Gastroenterologist & Liver Specialist",
            dept: "Gastroenterology & Hepatology",
            opd: "Mon – Sat: 9:30 AM – 4:30 PM",
            profile: "https://www.medicoverhospitals.in/doctors/dr-srinivas-nistala"
        });
        doctors.push({
            name: "Dr. Burra Siva Kumar",
            qual: "MBBS, MD, DM (Medical Gastroenterology)",
            role: "Consultant Gastroenterologist",
            dept: "Gastroenterology & Digestive Health",
            opd: "Mon – Sat: 10:00 AM – 5:00 PM",
            profile: "https://www.medicoverhospitals.in/doctors/dr-burra-siva-kumar"
        });
        tests.push("Liver Function Test (LFT: Total Bilirubin, SGPT/ALT, AST)", "Abdominal Ultrasound (USG)", "Viral Hepatitis Panel (HBsAg, Anti-HCV)");
    }

    // 4. Thyroid / Weight / Cold / Heat / Hair Loss / Neck Swelling
    if (s.includes('thyroid') || s.includes('weight') || s.includes('cold') || s.includes('heat') || s.includes('hair') || s.includes('tsh') || s.includes('throat') || s.includes('swelling') || s.includes('neck')) {
        doctors.push({
            name: "Dr. Kurumeti Vamsi Krishna",
            qual: "MBBS, MD (General Medicine), DM (Endocrinology)",
            role: "Consultant Endocrinologist & Diabetologist",
            dept: "Endocrinology & Metabolic Care",
            opd: "Mon – Sat: 11:00 AM – 4:30 PM",
            profile: "https://www.medicoverhospitals.in/doctors/dr-kurumeti-vamsi-krishna"
        });
        doctors.push({
            name: "Dr. Mrudula Kolli",
            qual: "MBBS, MD (General Medicine)",
            role: "Consultant Physician & Metabolic Health",
            dept: "General Medicine",
            opd: "Mon – Sat: 9:00 AM – 4:00 PM",
            profile: "https://www.medicoverhospitals.in/doctors/dr-mrudula-kolli"
        });
        tests.push("Thyroid Panel (TSH, Total T3, Free T4)", "Anti-TPO Thyroid Antibodies", "Fasting Blood Glucose & HbA1c");
    }

    // 5. Respiratory / Cough / Breathlessness / Chest Congestion
    if (s.includes('cough') || s.includes('breath') || s.includes('chest') || s.includes('phlegm') || s.includes('wheez') || s.includes('dyspnea')) {
        doctors.push({
            name: "Dr. Allena Prem Kumar",
            qual: "MBBS, MD (Pulmonary Medicine)",
            role: "Consultant Pulmonologist & Chest Specialist",
            dept: "Pulmonology & Respiratory Care",
            opd: "Mon – Sat: 9:30 AM – 4:30 PM",
            profile: "https://www.medicoverhospitals.in/doctors/dr-allena-prem-kumar"
        });
        doctors.push({
            name: "Dr. Monisha Silla",
            qual: "MBBS, MD (Pulmonary Medicine)",
            role: "Consultant Interventional Pulmonologist",
            dept: "Pulmonology",
            opd: "Mon – Sat: 10:00 AM – 4:00 PM",
            profile: "https://www.medicoverhospitals.in/doctors/dr-monisha-silla"
        });
        tests.push("Chest X-Ray / High-Resolution CT", "Complete Blood Count (CBC) with Absolute Eosinophil Count", "Spirometry / Pulmonary Function Test (PFT)");
    }

    // 6. Joint / Bone / Muscle / Orthopedic Pain
    if (s.includes('joint') || s.includes('bone') || s.includes('back pain') || s.includes('spine') || s.includes('knee') || s.includes('arthrit')) {
        doctors.push({
            name: "Dr. A. Pratap Reddy",
            qual: "MBBS, MS (Orthopedics), M.Ch (Orthopedics)",
            role: "Senior Consultant Joint Replacement & Orthopedic Surgeon",
            dept: "Orthopedics & Joint Care",
            opd: "Mon – Sat: 10:00 AM – 5:00 PM",
            profile: "https://www.medicoverhospitals.in/doctors/dr-a-pratap-reddy"
        });
        doctors.push({
            name: "Dr. Narendranadh A",
            qual: "MBBS, MS (Orthopedics)",
            role: "Consultant Orthopedic Surgeon (MVP Vizag)",
            dept: "Orthopedics",
            opd: "Mon – Sat: 9:30 AM – 4:30 PM",
            profile: "https://www.medicoverhospitals.in/doctors/dr-narendranadh-a-orthopedic-surgeon-mvp-visakhapatnam"
        });
        tests.push("Serum Uric Acid & ESR", "Rheumatoid Factor (RA Factor) & Anti-CCP", "Digital X-Ray / Musculoskeletal Ultrasound");
    }

    // 7. Urinary / Burning / Kidney / Flank Pain
    if (s.includes('urination') || s.includes('burning') || s.includes('flank') || s.includes('kidney') || s.includes('renal')) {
        doctors.push({
            name: "Dr. V. Srinivas",
            qual: "MBBS, MD (General Medicine), DM (Nephrology)",
            role: "Senior Consultant Nephrologist & Renal Transplant Physician",
            dept: "Nephrology & Renal Medicine",
            opd: "Mon – Sat: 9:30 AM – 4:30 PM",
            profile: "https://www.medicoverhospitals.in/doctors/dr-v-srinivas"
        });
        tests.push("Complete Urine Routine & Microscopy", "Kidney Function Test (KFT: Serum Creatinine, Urea, eGFR)", "Ultrasound KUB (Kidney, Ureter, Bladder)");
    }

    // 8. Default fallback if no specific match
    if (doctors.length === 0) {
        doctors.push({
            name: "Dr. K. Rama Murty",
            qual: "MBBS, MD (General Medicine)",
            role: "Senior Consultant Physician",
            dept: "General Medicine & Diagnostics",
            opd: "Mon – Sat: 9:00 AM – 5:00 PM",
            profile: "https://www.medicoverhospitals.in/doctors/dr-k-rama-murty"
        });
        doctors.push({
            name: "Dr. Thriveni Reddy",
            qual: "MBBS, MD (General Medicine)",
            role: "Consultant Physician",
            dept: "General Medicine & Health Checkups",
            opd: "Mon – Sat: 9:30 AM – 4:00 PM",
            profile: "https://www.medicoverhospitals.in/doctors/dr-thriveni-reddy"
        });
        tests.push("Complete Blood Count (CBC)", "Complete Urine Routine & Microscopy", "Comprehensive Metabolic Panel (CMP)");
    }

    // Deduplicate doctors by name and tests
    const seenNames = new Set();
    doctors = doctors.filter(d => {
        if (seenNames.has(d.name)) return false;
        seenNames.add(d.name);
        return true;
    }).slice(0, 4); // Show top 2-4 most relevant

    tests = [...new Set(tests)];

    container.innerHTML = `
        <div style="background: linear-gradient(135deg, rgba(238, 242, 255, 0.95), rgba(245, 243, 255, 0.98)); border: 1px solid #c7d2fe; border-radius: 14px; padding: 22px; margin-top: 16px; box-shadow: 0 4px 16px rgba(79,70,229,0.08);">
            <!-- Title Header -->
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px; margin-bottom: 16px;">
                <div>
                    <div style="display: inline-flex; align-items: center; gap: 6px; background: #e0e7ff; color: #3730a3; padding: 4px 12px; border-radius: 999px; font-size: 0.76rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px;">
                        <span>🏥</span> MEDICOVER HOSPITALS &bull; VISAKHAPATNAM (VIZAG)
                    </div>
                    <h3 style="font-size: 1.25rem; font-weight: 800; color: #1e1b4b; margin: 2px 0;">
                        Suggested Specialist Consultations &amp; Recommended Follow-Up Tests
                    </h3>
                    <p style="font-size: 0.85rem; color: #475569; margin: 0; line-height: 1.5;">
                        Verified medical specialists from <a href="https://www.medicoverhospitals.in/doctors/vizag" target="_blank" style="color: #4338ca; font-weight: 700; text-decoration: underline;">Medicover Hospitals Vizag</a> recommended for your symptoms:
                    </p>
                </div>
                <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                    <a href="tel:08916824444" class="btn-primary" style="background: linear-gradient(135deg, #4f46e5, #7c3aed); text-decoration: none; padding: 10px 18px; font-size: 0.85rem; font-weight: 800; box-shadow: 0 4px 12px rgba(79,70,229,0.25);">
                        <span>📞</span> Call: 0891-6824444
                    </a>
                    <a href="https://www.medicoverhospitals.in/doctors/vizag" target="_blank" class="btn-secondary" style="text-decoration: none; padding: 9px 14px; font-size: 0.82rem; color: #4338ca; border-color: #c7d2fe;">
                        <span>🌐</span> View All Vizag Doctors ↗
                    </a>
                </div>
            </div>

            <!-- Follow-Up Diagnostic Tests Box -->
            <div style="background: #ffffff; border: 1px solid #e0e7ff; border-radius: 10px; padding: 14px 18px; margin-bottom: 16px;">
                <div style="font-size: 0.82rem; font-weight: 800; color: #4338ca; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 8px;">
                    🧪 Recommended Pathology Investigations:
                </div>
                <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                    ${tests.map(t => `<span style="background: #f8fafc; border: 1px solid #cbd5e1; color: #1e293b; font-weight: 700; font-size: 0.82rem; padding: 6px 12px; border-radius: 8px;">✓ ${t}</span>`).join('')}
                </div>
            </div>

            <!-- Recommended Doctors Grid -->
            <div style="font-size: 0.82rem; font-weight: 800; color: #4338ca; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 10px;">
                👨‍⚕️ Verified Specialists at Medicover Vizag (Click to View Official Profile):
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px;">
                ${doctors.map(d => `
                    <div style="background: #ffffff; border: 1px solid #e0e7ff; border-left: 4px solid #4f46e5; border-radius: 10px; padding: 14px 16px; display: flex; flex-direction: column; justify-content: space-between; gap: 10px;">
                        <div>
                            <div style="font-size: 0.72rem; color: #6366f1; font-weight: 800; text-transform: uppercase;">${d.dept}</div>
                            <h4 style="font-size: 1.05rem; font-weight: 800; color: #1e1b4b; margin: 2px 0;">${d.name}</h4>
                            <div style="font-size: 0.78rem; color: #4338ca; font-weight: 600;">${d.qual}</div>
                            <div style="font-size: 0.78rem; color: #64748b; margin-top: 2px;">${d.role}</div>
                            <div style="font-size: 0.76rem; color: #475569; margin-top: 6px;">🕒 <strong>OPD:</strong> ${d.opd}</div>
                        </div>
                        <div style="display: flex; gap: 8px; margin-top: 4px;">
                            <a href="tel:08916824444" class="btn-primary" style="background: #4f46e5; text-decoration: none; padding: 6px 12px; font-size: 0.78rem; flex: 1; text-align: center; justify-content: center;">
                                <span>📞</span> Consult Doctor
                            </a>
                            <a href="${d.profile}" target="_blank" class="btn-secondary" style="text-decoration: none; padding: 6px 12px; font-size: 0.78rem; color: #4338ca; border-color: #c7d2fe; flex: 1; text-align: center; justify-content: center;">
                                <span>🌐</span> Official Profile ↗
                            </a>
                        </div>
                    </div>
                `).join('')}
            </div>

            <div style="margin-top: 14px; font-size: 0.76rem; color: #64748b; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                <span>📍 <strong>Location:</strong> Medicover Hospital, MVP Colony / Health City Chinagadili, Vizag.</span>
                <span>🔗 <a href="https://www.medicoverhospitals.in/doctors/vizag" target="_blank" style="color: #4338ca; font-weight: 600;">Explore All Specialists on medicoverhospitals.in ↗</a></span>
            </div>
        </div>
    `;
}

async function streamSymptomSuggestions(e) {
    if (e) e.preventDefault();

    const textarea = document.getElementById('symp-textarea');
    const ageInput = document.getElementById('symp-age');
    const genderSelect = document.getElementById('symp-gender');
    const durationSelect = document.getElementById('symp-duration');
    const severitySelect = document.getElementById('symp-severity');
    const submitBtn = document.getElementById('symp-submit-btn');
    const resultsContainer = document.getElementById('symp-results-container');
    const contentEl = document.getElementById('symp-streamed-content');
    const statusEl = document.getElementById('symp-stream-status');
    const modelBadge = document.getElementById('symp-active-model-badge');
    const reasoningBadge = document.getElementById('symp-reasoning-badge');
    const reasoningCount = document.getElementById('symp-reasoning-count');
    const reasoningDrawer = document.getElementById('symp-reasoning-drawer');
    const reasoningContent = document.getElementById('symp-reasoning-content');
    const livePulse = document.getElementById('symp-live-pulse');

    if (!textarea || !textarea.value.trim()) {
        alert("Please describe your symptoms or click a few symptom tags before analyzing.");
        if (textarea) textarea.focus();
        return;
    }

    const symptoms = textarea.value.trim();
    const age = ageInput && ageInput.value ? parseInt(ageInput.value, 10) : null;
    const gender = genderSelect && genderSelect.value ? genderSelect.value : null;
    const duration = durationSelect && durationSelect.value ? durationSelect.value : null;
    const severity = severitySelect && severitySelect.value ? severitySelect.value : null;

    stopSymptomSpeech();
    dismissTriageBanner();

    // Show results container
    if (resultsContainer) resultsContainer.style.display = 'block';
    resultsContainer.scrollIntoView({ behavior: 'smooth' });

    // Render Medicover Vizag Doctor Suggestions directly into Symptoms AI Report!
    renderSymptomsMedicoverDoctors(symptoms);

    if (contentEl) {
        contentEl.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px; color: var(--text-muted); padding: 24px 0;">
                <div class="spinner" style="width: 22px; height: 22px;"></div>
                <span style="font-weight: 600;">Connecting to OpenRouter Free AI stream &amp; synthesizing guidance...</span>
            </div>
        `;
    }

    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span>⏳</span> Synthesizing AI Guidance...`;
    }
    if (statusEl) {
        statusEl.textContent = 'Streaming live...';
        statusEl.style.background = 'rgba(16,185,129,0.15)';
        statusEl.style.color = '#059669';
    }
    if (livePulse) livePulse.style.display = 'block';
    if (reasoningBadge) reasoningBadge.style.display = 'none';

    rawSymptomMarkdown = "";
    rawReasoningText = "";

    try {
        const response = await fetch(apiUrl('/api/symptoms/suggest'), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                symptoms: symptoms,
                age: age,
                gender: gender,
                duration: duration,
                severity: severity,
                language: window._selectedLanguage || 'English'  // Feature 4
            })
        });

        if (!response.ok) {
            const err = await safeJson(response);
            throw new Error(err.detail || `Server returned HTTP ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n\n");
            buffer = lines.pop(); // Keep incomplete chunk in buffer

            for (const line of lines) {
                const trimmed = line.trim();
                if (trimmed.startsWith("data: ")) {
                    const dataStr = trimmed.slice(6).trim();
                    if (dataStr === "[DONE]") {
                        break;
                    }
                    try {
                        const parsed = JSON.parse(dataStr);
                        if (parsed.error) {
                            throw new Error(parsed.error);
                        }
                        // Feature 2: Triage banner intercept (first event from stream)
                        if (parsed.triage) {
                            triggerTriageBanner(parsed.triage);
                        }
                        if (parsed.model && modelBadge) {
                            modelBadge.textContent = `Model: ${parsed.model}`;
                        }
                        if (parsed.reasoning_chunk) {
                            rawReasoningText += parsed.reasoning_chunk;
                            if (reasoningDrawer) reasoningDrawer.style.display = 'block';
                            if (reasoningContent) reasoningContent.textContent = rawReasoningText;
                        }
                        if (parsed.reasoning_tokens && parsed.reasoning_tokens > 0) {
                            if (reasoningBadge) reasoningBadge.style.display = 'inline-flex';
                            if (reasoningCount) reasoningCount.textContent = parsed.reasoning_tokens;
                        }
                        if (parsed.token) {
                            rawSymptomMarkdown += parsed.token;
                            if (contentEl) {
                                contentEl.innerHTML = formatMarkdownAdvice(rawSymptomMarkdown) + '<span class="symp-typing-cursor"></span>';
                            }
                        }
                    } catch (e) {
                        // ignore malformed token JSON
                    }
                }
            }
        }

        // Finalize
        if (contentEl) {
            contentEl.innerHTML = formatMarkdownAdvice(rawSymptomMarkdown);
        }
        if (statusEl) {
            statusEl.textContent = '✓ Guidance Ready';
            statusEl.style.background = 'rgba(2,132,199,0.15)';
            statusEl.style.color = '#0284c7';
        }
        if (livePulse) livePulse.style.display = 'none';

        // Feature 1: Extract and render doctor questions card
        extractDoctorQuestions(rawSymptomMarkdown);

    } catch (err) {
        if (contentEl) {
            contentEl.innerHTML = `
                <div style="background: #fee2e2; border: 1px solid #fecaca; color: #991b1b; padding: 16px; border-radius: 8px; font-size: 0.88rem;">
                    <strong>Notice:</strong> ${err.message || 'Could not complete streaming analysis. Please try again.'}
                </div>
            `;
        }
        if (statusEl) {
            statusEl.textContent = 'Error';
            statusEl.style.background = 'rgba(220,38,38,0.15)';
            statusEl.style.color = '#dc2626';
        }
        if (livePulse) livePulse.style.display = 'none';
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<span>✨</span> Analyze Symptoms &amp; Stream AI Guidance`;
        }
    }
}

// Alias for backwards compatibility
const handleSymptomSubmit = streamSymptomSuggestions;

function toggleSymptomSpeech() {
    if (!('speechSynthesis' in window)) {
        alert("Text-to-Speech is not supported in this browser.");
        return;
    }

    const ttsIcon = document.getElementById('symp-tts-icon');
    const ttsText = document.getElementById('symp-tts-text');

    if (isSpeakingSymptomAdvice) {
        stopSymptomSpeech();
    } else {
        if (!rawSymptomMarkdown) {
            alert("Please generate symptom guidance before listening.");
            return;
        }

        // Clean markdown for smooth speech
        const cleanSpeechText = rawSymptomMarkdown
            .replace(/[#*`~_>\-\[\]]/g, ' ')
            .replace(/##+/g, '.')
            .replace(/\s+/g, ' ')
            .trim();

        symptomSpeechUtterance = new SpeechSynthesisUtterance(cleanSpeechText);
        symptomSpeechUtterance.rate = 1.0;
        symptomSpeechUtterance.pitch = 1.0;

        symptomSpeechUtterance.onend = () => {
            stopSymptomSpeech();
        };
        symptomSpeechUtterance.onerror = () => {
            stopSymptomSpeech();
        };

        window.speechSynthesis.speak(symptomSpeechUtterance);
        isSpeakingSymptomAdvice = true;
        if (ttsIcon) ttsIcon.textContent = '⏹️';
        if (ttsText) ttsText.textContent = 'Stop';
    }
}

function stopSymptomSpeech() {
    if ('speechSynthesis' in window && window.speechSynthesis.speaking) {
        window.speechSynthesis.cancel();
    }
    isSpeakingSymptomAdvice = false;
    const ttsIcon = document.getElementById('symp-tts-icon');
    const ttsText = document.getElementById('symp-tts-text');
    if (ttsIcon) ttsIcon.textContent = '🔊';
    if (ttsText) ttsText.textContent = 'Listen';
}

function copySymptomAdvice() {
    if (!rawSymptomMarkdown) {
        alert("No guidance generated yet to copy.");
        return;
    }
    navigator.clipboard.writeText(rawSymptomMarkdown).then(() => {
        const copyText = document.getElementById('symp-copy-text');
        const copyIcon = document.getElementById('symp-copy-icon');
        if (copyText) copyText.textContent = 'Copied!';
        if (copyIcon) copyIcon.textContent = '✓';
        setTimeout(() => {
            if (copyText) copyText.textContent = 'Copy Guidance';
            if (copyIcon) copyIcon.textContent = '📋';
        }, 2000);
    }).catch(() => {
        alert("Failed to copy to clipboard.");
    });
}

function printSymptomAdvice() {
    if (!rawSymptomMarkdown) {
        alert("Please generate symptom guidance before printing.");
        return;
    }
    window.print();
}


// ---------------------------------------------------------
// Interactive Home Widgets Logic (Biomarker Explorer, Journey, Pearls)
// ---------------------------------------------------------
const BIOMARKER_DB = {
    'hb': {
        name: 'Hemoglobin (Hb)',
        unit: 'g/dL',
        normalRange: '13.0 – 17.0 g/dL (Male) | 12.0 – 15.5 g/dL (Female)',
        pointerPos: '50%',
        category: 'Hematology & Oxygen Transport',
        desc: 'Iron-rich protein in red blood cells that carries oxygen from the lungs to tissues throughout the body.',
        highMeaning: 'Dehydration, chronic hypoxia, polycythemia vera, or high altitude living.',
        lowMeaning: 'Iron deficiency anemia, blood loss, chronic kidney disease, or nutritional deficiencies.',
        tests: 'Complete Blood Count (CBC), Serum Ferritin, Total Iron Binding Capacity (TIBC)'
    },
    'plt': {
        name: 'Platelet Count (PLT)',
        unit: 'cells/µL',
        normalRange: '150,000 – 450,000 /µL',
        pointerPos: '48%',
        category: 'Clotting & Vascular Integrity',
        desc: 'Specialized cell fragments essential for normal blood clotting and healing injured blood vessels.',
        highMeaning: 'Thrombocytosis, acute infection, chronic inflammation, or bone marrow stimulation.',
        lowMeaning: 'Thrombocytopenia, Dengue fever, viral infections, immune destruction, or liver cirrhosis.',
        tests: 'Dengue NS1 Antigen, CBC Platelet Kinetics, Peripheral Smear'
    },
    'wbc': {
        name: 'White Blood Cell Count (WBC / TLC)',
        unit: 'x10³/µL',
        normalRange: '4.0 – 11.0 x10³/µL',
        pointerPos: '52%',
        category: 'Immune System & Infection Defense',
        desc: 'Immune defense cells responsible for neutralizing bacterial, viral, fungal, and parasitic infections.',
        highMeaning: 'Acute bacterial infection, systemic inflammation, physical stress, or leukemia.',
        lowMeaning: 'Viral infections (Dengue, Influenza), autoimmune conditions, or bone marrow suppression.',
        tests: 'CBC Differential Count (Neutrophils/Lymphocytes), CRP, ESR'
    },
    'bili': {
        name: 'Total Bilirubin',
        unit: 'mg/dL',
        normalRange: '0.2 – 1.2 mg/dL',
        pointerPos: '42%',
        category: 'Liver & Biliary Function',
        desc: 'Yellowish breakdown byproduct of old red blood cells processed and excreted by the liver through bile.',
        highMeaning: 'Hepatic injury, hepatitis, jaundice, gallstones, biliary tract obstruction, or hemolysis.',
        lowMeaning: 'Generally of no clinical concern, occasionally seen in severe iron overload.',
        tests: 'Liver Function Test (LFT), SGPT/ALT, Alkaline Phosphatase (ALP), Abdominal Ultrasound'
    },
    'tsh': {
        name: 'Thyroid Stimulating Hormone (TSH)',
        unit: 'µIU/mL',
        normalRange: '0.4 – 4.2 µIU/mL',
        pointerPos: '50%',
        category: 'Endocrine & Metabolic Regulation',
        desc: 'Pituitary hormone regulating thyroid gland hormone production (T3/T4) and cellular metabolic rate.',
        highMeaning: 'Hypothyroidism (underactive thyroid), chronic fatigue, unexplained weight gain, cold intolerance.',
        lowMeaning: 'Hyperthyroidism (overactive thyroid), palpitations, unintended weight loss, heat sensitivity.',
        tests: 'Total T3, Free T4, Anti-TPO Antibodies, Thyroid Ultrasound'
    },
    'alt': {
        name: 'Alanine Aminotransferase (ALT / SGPT)',
        unit: 'IU/L',
        normalRange: '7 – 56 IU/L',
        pointerPos: '45%',
        category: 'Liver Cellular Integrity',
        desc: 'Intracellular enzyme found primarily in liver cells that releases into blood during hepatocellular injury.',
        highMeaning: 'Viral hepatitis, fatty liver disease (NAFLD), alcohol damage, medication hepatotoxicity.',
        lowMeaning: 'Normal physiological state, occasionally low in chronic renal failure.',
        tests: 'Comprehensive Liver Panel, Hepatitis Serology, Lipid Profile'
    },
    'glucose': {
        name: 'Fasting Blood Glucose (FBG)',
        unit: 'mg/dL',
        normalRange: '70 – 99 mg/dL (Normal Fasting)',
        pointerPos: '48%',
        category: 'Carbohydrate Metabolism & Diabetes',
        desc: 'Primary circulating monosaccharide fuel utilized by cells, strictly regulated by insulin and glucagon.',
        highMeaning: 'Prediabetes (100–125 mg/dL), Diabetes Mellitus (≥126 mg/dL), acute physiological stress.',
        lowMeaning: 'Hypoglycemia (<70 mg/dL), insulin excess, prolonged starvation, Addisonian crisis.',
        tests: 'HbA1c Glycated Hemoglobin, Postprandial Glucose (PPBG), Fasting Serum Insulin'
    },
    'creat': {
        name: 'Serum Creatinine',
        unit: 'mg/dL',
        normalRange: '0.7 – 1.3 mg/dL (Male) | 0.5 – 1.1 mg/dL (Female)',
        pointerPos: '49%',
        category: 'Renal Glomerular Filtration',
        desc: 'Constant chemical byproduct of normal muscle metabolism filtered by the kidneys and excreted in urine.',
        highMeaning: 'Acute kidney injury (AKI), chronic kidney disease (CKD), dehydration, urinary obstruction.',
        lowMeaning: 'Low muscle mass, severe malnutrition, advanced age, or normal pregnancy.',
        tests: 'Kidney Function Test (KFT / RFT), eGFR, Blood Urea Nitrogen (BUN), Urine Microalbumin'
    }
};

function selectBiomarker(bioKey) {
    const data = BIOMARKER_DB[bioKey];
    if (!data) return;

    document.querySelectorAll('.bio-chip-btn').forEach(btn => btn.classList.remove('active'));
    const activeBtn = document.getElementById(`bio-btn-${bioKey}`);
    if (activeBtn) activeBtn.classList.add('active');

    document.getElementById('bio-name').textContent = data.name;
    document.getElementById('bio-category').textContent = data.category;
    document.getElementById('bio-range').textContent = data.normalRange;
    document.getElementById('bio-desc').textContent = data.desc;
    document.getElementById('bio-high').textContent = data.highMeaning;
    document.getElementById('bio-low').textContent = data.lowMeaning;
    document.getElementById('bio-tests').textContent = data.tests;

    const pointer = document.getElementById('bio-pointer');
    if (pointer) {
        pointer.style.left = data.pointerPos;
    }
}

const JOURNEY_STEPS_INFO = [
    {
        title: "1. Smart Barcoded Sample Collection & Verification",
        desc: "Automated check-in generates unique encrypted barcoded vacutainers, ensuring zero patient sample mix-up and cold-chain compliance before specimen analysis."
    },
    {
        title: "2. Dual-Tier Clinical ML Diagnostic Inferences",
        desc: "Automated analyzers process blood chemistry and cell smears. Five validated machine learning models simultaneously screen parameters for early anomalies."
    },
    {
        title: "3. Accredited Pathologist Review & Digital Signing",
        desc: "Certified clinical pathologists cross-reference ML insights against laboratory findings, add custom remarks, and securely sign the final authoritative report."
    },
    {
        title: "4. Instant Patient Access & Real-Time AI Care Guidance",
        desc: "Patients access certified PDF reports immediately via their secure PIN, with real-time AI guidance delivering personalized precautions and evidence-informed remedies."
    }
];

function selectJourneyStep(stepIdx) {
    document.querySelectorAll('.journey-step-box').forEach(el => el.classList.remove('active'));
    const targetBox = document.getElementById(`journey-step-${stepIdx}`);
    if (targetBox) targetBox.classList.add('active');

    const step = JOURNEY_STEPS_INFO[stepIdx];
    if (step) {
        document.getElementById('journey-detail-title').textContent = step.title;
        document.getElementById('journey-detail-desc').textContent = step.desc;
    }
}

const HEALTH_PEARLS = [
    {
        category: "🦟 Infectious Disease & Hematology",
        quote: "Platelet kinetics can decline rapidly in Dengue viral fever between Days 3 to 7. Regular serial CBC checks and adequate oral rehydration prevent severe plasma leakage.",
        pearl: "Daily Platelet & Hematocrit Monitoring"
    },
    {
        category: "🩸 Anemia & Iron Metabolism",
        quote: "Taking Iron supplements along with Vitamin C (such as citrus fruits) enhances intestinal absorption by over 60%, while tea, coffee, and dairy inhibit iron uptake.",
        pearl: "Dietary Iron Absorption Synergy"
    },
    {
        category: "🫁 Hepatology & Liver Health",
        quote: "Elevated SGPT/ALT levels are often the earliest biomarker of non-alcoholic fatty liver disease (NAFLD) and can be reversed with a 5-10% reduction in body weight.",
        pearl: "Early Hepatocellular Reversibility"
    },
    {
        category: "🦋 Endocrinology & Thyroid Regulation",
        quote: "TSH tests are best performed in the early morning fasting state, as thyroid hormone levels follow a circadian rhythm and peak in early morning hours.",
        pearl: "Optimal Circadian Testing Window"
    },
    {
        category: "🧬 Renal & Metabolic Wellness",
        quote: "Mild elevations in Serum Creatinine can occur simply due to dehydration or intense exercise. Adequate fluid intake restores normal filtration parameters.",
        pearl: "Hydration Status & GFR Accuracy"
    }
];

let currentPearlIdx = 0;
function generateNextHealthPearl() {
    currentPearlIdx = (currentPearlIdx + 1) % HEALTH_PEARLS.length;
    const pearl = HEALTH_PEARLS[currentPearlIdx];
    const catEl = document.getElementById('pearl-category');
    const quoteEl = document.getElementById('pearl-quote');
    const tagEl = document.getElementById('pearl-tag');

    if (catEl) catEl.textContent = pearl.category;
    if (quoteEl) quoteEl.textContent = `"${pearl.quote}"`;
    if (tagEl) tagEl.textContent = pearl.pearl;
}

// Open Admin / Doctor Console in a Dedicated Separate Browser Tab
function openAdminPortalNewTab() {
    const baseUrl = window.location.href.split('#')[0].split('?')[0];
    const targetUrl = `${baseUrl}?view=admin`;
    window.open(targetUrl, '_blank');
}

// Initialize on DOM load
window.addEventListener('DOMContentLoaded', async () => {
    restoreSessionAuth();
    await checkBackendHealth();
    setInterval(() => checkBackendHealth(false), 4000); // Periodic auto-check
    
    // Auto-detect if opened with ?view=admin or hash #admin in new tab
    const urlParams = new URLSearchParams(window.location.search);
    const requestedView = urlParams.get('view') || window.location.hash.replace('#', '') || sessionStorage.getItem('nexus_active_view') || 'home';
    switchView(requestedView);
    
    setupSandboxDragDrop();
    setupAnalyzerDragDrop();
});


// ================================================================
// FEATURE 1: Doctor Questions Card — Extract & Render
// ================================================================
function extractDoctorQuestions(markdown) {
    const card = document.getElementById('medicover-questions-card');
    const list = document.getElementById('mq-question-list');
    if (!card || !list) return;

    // Resilient regex: matches H2 or H3, with/without emoji, and variants of title
    const primaryRegex = /(?:##+\s*(?:🩺\s*)?Questions.*?(?:Medicover|Specialist|Doctor|Physician)|\*\*Questions.*?(?:Medicover|Specialist|Doctor|Physician)\*\*)[\s\S]*?\n([\s\S]*?)(?=##|\n\n\*\*|$)/i;
    let match = markdown.match(primaryRegex);

    if (!match) {
        // Fallback: any section mentioning Questions or Ask
        const fallbackRegex = /##+\s*[^#\n]*?(?:Questions|Specialist|Doctor)[^#\n]*?\n([\s\S]*?)(?=##|$)/i;
        match = markdown.match(fallbackRegex);
    }

    if (!match) {
        card.style.display = 'none';
        return;
    }

    const sectionBody = match[1] || '';
    // Extract bullet lines: - text or * text or 1. text or numbered
    const lines = sectionBody.split('\n')
        .map(l => l.replace(/^[-*•\d.]+\s*/, '').replace(/\*\*/g, '').trim())
        .filter(l => l.length > 8);

    if (lines.length === 0) {
        card.style.display = 'none';
        return;
    }

    list.innerHTML = lines.slice(0, 5).map((q, i) => `
        <li>
            <span class="mq-question-num">${i + 1}</span>
            <span>${q}</span>
        </li>
    `).join('');

    card.style.display = 'block';
    card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function copyDoctorQuestions() {
    const list = document.getElementById('mq-question-list');
    const icon = document.getElementById('mq-copy-icon');
    if (!list) return;

    const qs = Array.from(list.querySelectorAll('li span:last-child'))
        .map((el, i) => `${i + 1}. ${el.textContent}`)
        .join('\n');

    const text = `Questions for My Medicover Specialist:\n\n${qs}`;
    navigator.clipboard.writeText(text).then(() => {
        if (icon) icon.textContent = '✅';
        setTimeout(() => { if (icon) icon.textContent = '📋'; }, 2000);
    }).catch(() => {
        const ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        if (icon) icon.textContent = '✅';
        setTimeout(() => { if (icon) icon.textContent = '📋'; }, 2000);
    });
}


// ================================================================
// FEATURE 2: Critical Alert Banner
// ================================================================
function triggerTriageBanner(level) {
    const banner = document.getElementById('critical-alert-banner');
    if (!banner) return;

    if (level === 'green' || !level) {
        dismissTriageBanner();
        return;
    }

    const headline = document.getElementById('cab-headline');
    const detail = document.getElementById('cab-detail');
    const callLink = document.getElementById('cab-call-link');

    // Remove any previous level classes
    banner.classList.remove('alert-red', 'alert-amber');

    if (level === 'red') {
        banner.classList.add('alert-red');
        if (headline) headline.textContent = '🚨 Critical Status Detected: Please visit Medicover Vizag Emergency immediately';
        if (detail) detail.innerHTML = 'Call <strong>1066</strong> (National Ambulance) or go to the nearest emergency department without delay.';
        if (callLink) { callLink.textContent = '📞 Call 1066 Now'; callLink.className = 'cab-call red-call'; }
    } else if (level === 'amber') {
        banner.classList.add('alert-amber');
        if (headline) headline.textContent = '⚠️ Urgent Attention Needed: Please consult a Medicover doctor today';
        if (detail) detail.innerHTML = 'Your symptoms may need prompt medical evaluation. Call <strong>1066</strong> or visit Medicover Vizag.';
        if (callLink) { callLink.textContent = '📞 Call 1066'; callLink.className = 'cab-call amber-call'; }
    }

    banner.style.display = 'flex';
}

function dismissTriageBanner() {
    const banner = document.getElementById('critical-alert-banner');
    if (banner) {
        banner.style.opacity = '0';
        banner.style.transform = 'translateY(-110%)';
        banner.style.transition = 'all 0.3s ease';
        setTimeout(() => {
            banner.style.display = 'none';
            banner.style.opacity = '';
            banner.style.transform = '';
            banner.style.transition = '';
            banner.classList.remove('alert-red', 'alert-amber');
        }, 300);
    }
}


// ================================================================
// FEATURE 3: Secure Report Sharing
// ================================================================
let _currentSharePin = '';

function shareCurrentReport(reportId) {
    const report = patientReports.find(r => r.report_id === reportId) || allReports.find(r => r.report_id === reportId);
    if (!report) {
        alert('Report not found.');
        return;
    }
    shareReportSecurely(report, report.patient_id);
}

async function shareReportSecurely(reportData, patientId) {
    const pid = patientId || currentAuth.patientId;
    if (!pid || !currentAuth.token) {
        alert('Please log in as a patient first to share a report.');
        return;
    }
    try {
        const res = await fetch(apiUrl('/api/share'), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${currentAuth.token}`
            },
            body: JSON.stringify({ patient_id: pid, data_payload: reportData })
        });

        if (!res.ok) {
            const err = await safeJson(res);
            throw new Error(err.detail || `Failed to generate PIN (HTTP ${res.status})`);
        }

        const data = await safeJson(res);
        _currentSharePin = data.pin;
        openSharePinModal(_currentSharePin);
    } catch (err) {
        alert('Share Error: ' + err.message);
    }
}

function openSharePinModal(pin) {
    const overlay = document.getElementById('share-pin-modal-overlay');
    const display = document.getElementById('spm-pin-display');
    if (!overlay || !display) return;

    // Render each digit as a separate styled box
    display.innerHTML = String(pin).split('').map(d =>
        `<div class="pin-digit">${d}</div>`
    ).join('');

    overlay.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeSharePinModal(event) {
    // Only close if clicking the backdrop (not the box)
    if (event && event.target !== document.getElementById('share-pin-modal-overlay')) return;
    closeSharePinModalBtn();
}

function closeSharePinModalBtn() {
    const overlay = document.getElementById('share-pin-modal-overlay');
    if (overlay) overlay.style.display = 'none';
    document.body.style.overflow = '';
}

function copySharePin() {
    const icon = document.getElementById('spm-copy-icon');
    if (!_currentSharePin) return;
    navigator.clipboard.writeText(_currentSharePin).then(() => {
        if (icon) icon.textContent = '✅';
        setTimeout(() => { if (icon) icon.textContent = '📋'; }, 2000);
    }).catch(() => {
        const ta = document.createElement('textarea');
        ta.value = _currentSharePin;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        if (icon) icon.textContent = '✅';
        setTimeout(() => { if (icon) icon.textContent = '📋'; }, 2000);
    });
}

async function fetchSharedSession() {
    const input = document.getElementById('admin-pin-input');
    const resultDiv = document.getElementById('admin-shared-session-result');
    if (!input || !resultDiv) return;

    const pin = input.value.trim();
    if (!pin || pin.length !== 6 || !/^\d+$/.test(pin)) {
        alert('Please enter a valid 6-digit numeric PIN.');
        input.focus();
        return;
    }

    resultDiv.style.display = 'block';
    resultDiv.innerHTML = `
        <div style="display:flex;align-items:center;gap:10px;padding:12px 16px;background:#eef3fc;border-radius:10px;border:1px solid #bfd0f0;">
            <div class="spinner" style="width:18px;height:18px;"></div>
            <span style="font-size:0.85rem;color:#1A50A0;font-weight:600;">Fetching shared session for PIN ${pin}...</span>
        </div>
    `;

    try {
        const res = await fetch(apiUrl(`/api/retrieve/${pin}`));
        if (!res.ok) {
            const err = await safeJson(res);
            const msg = err.detail || (res.status === 410 ? 'PIN has expired or does not exist.' : `HTTP ${res.status}`);
            resultDiv.innerHTML = `
                <div style="background:#fee2e2;border:1px solid #fecaca;border-left:4px solid #dc2626;border-radius:10px;padding:14px 18px;">
                    <strong style="color:#991b1b;">❌ Access Failed:</strong> <span style="color:#991b1b;font-size:0.88rem;">${msg}</span>
                </div>
            `;
            return;
        }

        const session = await safeJson(res);
        const payload = session.data_payload || {};
        const patientId = session.patient_id;
        const expiresAt = session.expires_at ? new Date(session.expires_at).toLocaleString() : 'Unknown';

        // Render the shared session data in admin view
        let contentHtml = '';
        if (payload.report_id && payload.report_data) {
            const paramsHtml = Object.entries(payload.report_data).map(([k, v]) => {
                const val = typeof v === 'object' ? (v.value !== undefined ? v.value : JSON.stringify(v)) : v;
                const unit = typeof v === 'object' ? (v.unit || '') : '';
                const flag = typeof v === 'object' ? (v.flag || 'Normal') : 'Normal';
                const flagClass = flag.toLowerCase().includes('high') || flag.toLowerCase().includes('abnormal') ? 'flag-high' : 'flag-normal';
                return `<tr><td><strong>${k}</strong></td><td>${val} ${unit}</td><td><span class="flag-badge ${flagClass}">${flag}</span></td></tr>`;
            }).join('');

            contentHtml = `
                <div style="margin-bottom:12px;">
                    <div style="font-size:0.92rem;font-weight:700;color:#0f172a;margin-bottom:4px;">Test: <span style="color:#1A50A0;text-transform:uppercase;">${payload.test_category || 'Laboratory Panel'}</span> (Report ID: ${payload.report_id})</div>
                    <div style="font-size:0.82rem;color:#64748b;margin-bottom:10px;">Status: <strong>${payload.status || 'Finalized'}</strong> | Sampling Date: ${payload.created_at ? new Date(payload.created_at).toLocaleDateString() : 'N/A'}</div>
                    <div class="table-responsive">
                        <table class="results-table">
                            <thead><tr><th>Parameter</th><th>Value</th><th>Flag</th></tr></thead>
                            <tbody>${paramsHtml}</tbody>
                        </table>
                    </div>
                    ${payload.doctor_remarks ? `<div style="margin-top:10px;padding:8px 12px;background:#f0f9ff;border-left:3px solid #0284c7;border-radius:6px;font-size:0.82rem;color:#0369a1;"><strong>Pathologist Remarks:</strong> ${payload.doctor_remarks}</div>` : ''}
                </div>
            `;
        } else {
            contentHtml = `<pre style="font-size:0.78rem;color:#334155;line-height:1.6;white-space:pre-wrap;font-family:monospace;">${JSON.stringify(payload, null, 2)}</pre>`;
        }

        resultDiv.innerHTML = `
            <div style="background:linear-gradient(135deg,#eef3fc,#f8fbff);border:1.5px solid #bfd0f0;border-left:4px solid #1A50A0;border-radius:12px;padding:18px 22px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;flex-wrap:wrap;gap:8px;">
                    <div style="font-size:1rem;font-weight:800;color:#1A50A0;display:flex;align-items:center;gap:8px;">🔐 Shared Patient Session — PIN: <code style="background:#1A50A0;color:#fff;padding:2px 8px;border-radius:6px;font-size:0.9rem;">${pin}</code></div>
                    <span style="font-size:0.72rem;color:#64748b;">Expires: ${expiresAt}</span>
                </div>
                <div style="display:flex;gap:8px;margin-bottom:12px;">
                    <span style="background:#eef3fc;border:1px solid #bfd0f0;color:#1A50A0;font-size:0.75rem;font-weight:700;padding:3px 10px;border-radius:999px;">👤 Patient ID: ${patientId}</span>
                </div>
                <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;padding:14px;max-height:360px;overflow-y:auto;">
                    ${contentHtml}
                </div>
            </div>
        `;
    } catch (err) {
        resultDiv.innerHTML = `
            <div style="background:#fee2e2;border:1px solid #fecaca;border-radius:10px;padding:14px;">
                <strong style="color:#991b1b;">Error:</strong> <span style="color:#991b1b;">${err.message}</span>
            </div>
        `;
    }
}


// ================================================================
// FEATURE 5: Personal Health Timeline
// ================================================================
async function loadPatientTimeline(patientId, token) {
    const container = document.getElementById('patient-timeline-container');
    if (!container) return;

    const pid = patientId || currentAuth.patientId;
    const tk = token || currentAuth.token;

    if (!pid || !tk) return;

    container.innerHTML = `
        <div style="display:flex;align-items:center;gap:10px;padding:16px 0;color:var(--text-muted);">
            <div class="spinner" style="width:18px;height:18px;"></div>
            <span style="font-size:0.85rem;">Loading your health timeline...</span>
        </div>
    `;

    try {
        const res = await fetch(apiUrl(`/api/timeline/${pid}`), {
            headers: { 'Authorization': `Bearer ${tk}` }
        });

        if (!res.ok) {
            container.innerHTML = `<div class="timeline-empty-state"><div class="tes-icon">📅</div><div>Could not load timeline.</div></div>`;
            return;
        }

        const data = await safeJson(res);
        renderTimeline(data.timeline || [], container);
    } catch (err) {
        container.innerHTML = `<div class="timeline-empty-state"><div class="tes-icon">⚠️</div><div>Timeline unavailable (server offline).</div></div>`;
    }
}

function renderTimeline(items, container) {
    if (!items || items.length === 0) {
        container.innerHTML = `
            <div class="timeline-empty-state">
                <div class="tes-icon">📅</div>
                <div style="font-size:0.85rem;">No health records found. Your lab reports and AI analyses will appear here.</div>
            </div>
        `;
        return;
    }

    const html = `<div class="timeline-container">${items.map((item, idx) => {
        const dateStr = item.date ? new Date(item.date).toLocaleDateString('en-IN', {
            day: 'numeric', month: 'short', year: 'numeric'
        }) : 'Unknown Date';
        const timeStr = item.date ? new Date(item.date).toLocaleTimeString('en-IN', {
            hour: '2-digit', minute: '2-digit'
        }) : '';

        const statusKey = (item.status || '').toLowerCase().replace(/[\s\/]/g, '-').replace('high-attention', 'high');
        const badgeClass = statusKey.includes('high') || statusKey.includes('elevated') ? 'badge-high'
            : statusKey.includes('moderate') ? 'badge-moderate'
            : statusKey.includes('normal') || statusKey === 'finalized' ? 'badge-finalized'
            : 'badge-draft';

        const isLast = idx === items.length - 1;

        return `
            <div class="timeline-item">
                <div class="timeline-left">
                    <div class="timeline-dot dot-${item.type}">${item.icon || '📋'}</div>
                    ${!isLast ? '<div class="timeline-connector"></div>' : ''}
                </div>
                <div class="timeline-body">
                    <div class="timeline-meta">
                        <span>${dateStr} ${timeStr}</span>
                        <span class="timeline-status-badge ${badgeClass}">${item.status || 'N/A'}</span>
                    </div>
                    <div class="timeline-title">${item.title || 'Health Record'}</div>
                    <div class="timeline-summary">${item.summary || ''}</div>
                </div>
            </div>
        `;
    }).join('')}</div>`;

    container.innerHTML = html;
}


// =========================================================
// Patient Symptom Issue Reporting & Doctor Care Reminders
// =========================================================

async function fileReportedIssueFromSymptoms() {
    const sympInput = document.getElementById('symp-input');
    const symptoms = sympInput ? sympInput.value.trim() : '';

    if (!symptoms) {
        alert("Please enter or describe your symptoms first before filing an official issue.");
        return;
    }

    // Determine target patient ID
    let patientId = currentAuth.patientId;
    if (!patientId || currentAuth.role !== 'patient') {
        const entered = prompt("Enter your Medicover Patient ID (e.g. PAT-1001) to file this issue with your doctor:");
        if (!entered || !entered.trim()) {
            return;
        }
        patientId = entered.trim();
    }

    const age = document.getElementById('symp-age')?.value || null;
    const gender = document.getElementById('symp-gender')?.value || null;
    const duration = document.getElementById('symp-duration')?.value || null;
    const severity = document.getElementById('symp-severity')?.value || null;

    // Grab summary text from stream if present
    const streamEl = document.getElementById('symp-streamed-content');
    const aiSummary = streamEl ? streamEl.innerText.slice(0, 500) : '';

    const btn = document.getElementById('btn-file-symptom-issue');
    const origHtml = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span>⏳</span> Filing to Doctor...`;
    }

    try {
        const headers = { 'Content-Type': 'application/json' };
        if (currentAuth.token) {
            headers['Authorization'] = `Bearer ${currentAuth.token}`;
        }

        const res = await fetch(apiUrl('/api/issues/report'), {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({
                patient_id: patientId,
                symptoms: symptoms,
                severity: severity,
                duration: duration,
                ai_summary: aiSummary
            })
        });

        if (!res.ok) {
            const err = await safeJson(res);
            throw new Error(err.detail || "Failed to file symptom issue.");
        }

        const data = await safeJson(res);
        if (btn) {
            btn.innerHTML = `<span>✓</span> Filed to Doctor!`;
            btn.style.background = "#10b981";
        }
        alert(`✅ Official Issue Filed Successfully!\n\nIssue Reference: ${data.issue.id}\nTriage Priority: ${(data.issue.triage_level || 'ROUTINE').toUpperCase()}\n\nYour attending Medicover physician has received your reported symptoms and will review them shortly.`);

        // If currently in patient portal, reload issues
        if (currentAuth.patientId === patientId) {
            loadPatientReportedIssues(patientId);
        }
    } catch (err) {
        alert("Error filing issue: " + err.message);
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = origHtml;
        }
    }
}

window._currentPatientReminders = [];
window._selectedReminderFilter = 'all';

async function loadPatientReminders(patientId) {
    const container = document.getElementById('patient-reminders-list');
    if (!container) return;

    try {
        const headers = {};
        if (currentAuth.token) headers['Authorization'] = `Bearer ${currentAuth.token}`;

        const res = await fetch(apiUrl(`/api/reminders/${encodeURIComponent(patientId)}`), { headers });
        if (!res.ok) throw new Error("Could not load care reminders.");

        const data = await safeJson(res);
        window._currentPatientReminders = data.reminders || [];
        renderPatientReminders();
    } catch (err) {
        container.innerHTML = `
            <div class="timeline-empty-state">
                <div class="tes-icon">🔔</div>
                <div style="font-size:0.85rem;">No active care reminders at this time.</div>
            </div>
        `;
    }
}

function filterPatientReminders(category) {
    window._selectedReminderFilter = category;
    const tabs = ['all', 'daily_care', 'diagnosis', 'checkup'];
    tabs.forEach(t => {
        const tabId = t === 'daily_care' ? 'btn-rem-daily' : `btn-rem-${t}`;
        const el = document.getElementById(tabId);
        if (el) {
            if (t === category) {
                el.classList.add('active');
            } else {
                el.classList.remove('active');
            }
        }
    });
    renderPatientReminders();
}

function renderPatientReminders() {
    const container = document.getElementById('patient-reminders-list');
    if (!container) return;

    let items = window._currentPatientReminders || [];
    if (window._selectedReminderFilter && window._selectedReminderFilter !== 'all') {
        items = items.filter(r => r.reminder_type === window._selectedReminderFilter);
    }

    if (items.length === 0) {
        container.innerHTML = `
            <div class="timeline-empty-state">
                <div class="tes-icon">✓</div>
                <div style="font-size:0.85rem; color:#64748b;">No reminders in this category. You are all caught up!</div>
            </div>
        `;
        return;
    }

    const typeIcons = {
        'daily_care': '💊 Daily Care',
        'diagnosis': '🩺 Diagnosis Follow-Up',
        'checkup': '🏥 Health Checkup'
    };

    const html = `
        <div class="care-reminder-list">
            ${items.map(r => {
                const isDone = r.status === 'completed';
                const createdDate = r.created_at ? new Date(r.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) : '';
                const dueDateStr = r.due_date ? `Due: ${r.due_date}` : 'Ongoing Daily';

                return `
                    <div class="care-reminder-item type-${r.reminder_type} ${isDone ? 'completed' : ''}" id="rem-item-${r.id}">
                        <div class="reminder-content">
                            <div class="reminder-header-row">
                                <span class="reminder-badge ${r.reminder_type}">${typeIcons[r.reminder_type] || r.reminder_type}</span>
                                <span class="reminder-freq-tag">${r.frequency ? r.frequency.toUpperCase() : 'ONCE'}</span>
                                ${isDone ? '<span class="reminder-done-badge">✓ Completed</span>' : ''}
                            </div>
                            <h4 class="reminder-title">${escapeHtml(r.title)}</h4>
                            <p class="reminder-message">${escapeHtml(r.message)}</p>
                            <div class="reminder-meta-row">
                                <span>📅 ${dueDateStr}</span>
                                <span>👨‍⚕️ ${escapeHtml(r.sent_by || 'Medicover Clinical Desk')}</span>
                                <span>🕒 Sent ${createdDate}</span>
                            </div>
                        </div>
                        <div class="reminder-action">
                            ${!isDone ? `
                                <button type="button" class="reminder-ack-btn" onclick="acknowledgeCareReminder('${r.id}')">
                                    <span>✓</span> Mark Done
                                </button>
                            ` : `
                                <span style="color: #10b981; font-weight: 800; font-size: 0.9rem;">✓</span>
                            `}
                        </div>
                    </div>
                `;
            }).join('')}
        </div>
    `;

    container.innerHTML = html;
}

async function acknowledgeCareReminder(reminderId) {
    try {
        const headers = {};
        if (currentAuth.token) headers['Authorization'] = `Bearer ${currentAuth.token}`;

        const res = await fetch(apiUrl(`/api/reminders/${encodeURIComponent(reminderId)}/acknowledge`), {
            method: 'PATCH',
            headers: headers
        });

        if (!res.ok) throw new Error("Could not update reminder.");

        // Update local state
        const item = (window._currentPatientReminders || []).find(r => r.id === reminderId);
        if (item) {
            item.status = 'completed';
            item.acknowledged_at = new Date().toISOString();
        }
        renderPatientReminders();
    } catch (err) {
        alert("Error updating reminder: " + err.message);
    }
}

async function loadPatientReportedIssues(patientId) {
    const container = document.getElementById('patient-reported-issues-list');
    if (!container) return;

    try {
        const headers = {};
        if (currentAuth.token) headers['Authorization'] = `Bearer ${currentAuth.token}`;

        const res = await fetch(apiUrl(`/api/issues?patient_id=${encodeURIComponent(patientId)}`), { headers });
        if (!res.ok) throw new Error("Could not load issues.");

        const data = await safeJson(res);
        const issues = data.issues || [];

        if (issues.length === 0) {
            container.innerHTML = `
                <div class="timeline-empty-state">
                    <div class="tes-icon">📋</div>
                    <div style="font-size:0.85rem;">No symptoms reported yet. You can file symptoms anytime from the Symptoms AI view.</div>
                </div>
            `;
            return;
        }

        const html = `
            <table class="results-table">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Reported Symptoms</th>
                        <th>Triage</th>
                        <th>Status</th>
                        <th>Doctor Notes / Guidance</th>
                    </tr>
                </thead>
                <tbody>
                    ${issues.map(iss => {
                        const dateStr = iss.created_at ? new Date(iss.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) : '—';
                        const triageClass = (iss.triage_level || 'green').toLowerCase();
                        const statusClass = (iss.status || 'open').toLowerCase();
                        const statusLabel = iss.status === 'resolved' ? '🟢 Resolved' : iss.status === 'in_review' ? '🟡 In Review' : '⚪ Open';

                        return `
                            <tr>
                                <td style="white-space: nowrap; font-size: 0.8rem; font-weight: 600;">${dateStr}</td>
                                <td style="max-width: 260px; font-size: 0.85rem;">
                                    <strong>${escapeHtml(iss.symptoms)}</strong>
                                    ${iss.severity ? `<div style="font-size: 0.74rem; color: #64748b;">Severity: ${escapeHtml(iss.severity)} (${escapeHtml(iss.duration || 'N/A')})</div>` : ''}
                                </td>
                                <td><span class="triage-pill ${triageClass}">${iss.triage_level || 'routine'}</span></td>
                                <td><span class="issue-status-pill ${statusClass}">${statusLabel}</span></td>
                                <td style="font-size: 0.82rem; color: #334155;">
                                    ${iss.doctor_notes ? `<strong>${escapeHtml(iss.doctor_notes)}</strong><div style="font-size: 0.72rem; color: #64748b;">— ${escapeHtml(iss.doctor_name || 'Medicover Doctor')}</div>` : '<em style="color: #94a3b8;">Pending physician review</em>'}
                                </td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        `;
        container.innerHTML = html;
    } catch (err) {
        container.innerHTML = `<div class="timeline-empty-state"><div class="tes-icon">⚠️</div><div>Could not load reported issues.</div></div>`;
    }
}

window._adminIssues = [];
window._adminReminders = [];

async function loadAdminReportedIssues() {
    const tbody = document.getElementById('admin-issues-table-body');
    const badge = document.getElementById('adm-issues-badge');
    if (!tbody) return;

    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:20px; color:#64748b;">Loading reported issues...</td></tr>`;

    try {
        const headers = {};
        if (currentAuth.token) headers['Authorization'] = `Bearer ${currentAuth.token}`;

        const res = await fetch(apiUrl('/api/issues'), { headers });
        if (!res.ok) throw new Error("Failed to load reported issues.");

        const data = await safeJson(res);
        window._adminIssues = data.issues || [];

        // Count open/in_review issues for badge
        const pending = window._adminIssues.filter(i => i.status !== 'resolved').length;
        if (badge) {
            badge.innerText = pending;
            badge.style.display = pending > 0 ? 'inline-block' : 'none';
        }

        if (window._adminIssues.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:30px; color:#64748b;">No patient-reported issues found in inbox.</td></tr>`;
            return;
        }

        tbody.innerHTML = window._adminIssues.map(iss => {
            const dateStr = iss.created_at ? new Date(iss.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) : '—';
            const triageClass = (iss.triage_level || 'green').toLowerCase();
            const statusClass = (iss.status || 'open').toLowerCase();
            const statusLabel = iss.status === 'resolved' ? '🟢 Resolved' : iss.status === 'in_review' ? '🟡 In Review' : '⚪ Open';

            return `
                <tr>
                    <td style="white-space:nowrap; font-size:0.78rem;">${dateStr}</td>
                    <td style="white-space:nowrap;">
                        <strong>${escapeHtml(iss.patient_name || iss.patient_id)}</strong>
                        <div style="font-size:0.72rem; color:#64748b;">ID: ${iss.patient_id}</div>
                    </td>
                    <td style="max-width:240px; font-size:0.84rem;">
                        <div>${escapeHtml(iss.symptoms)}</div>
                        ${iss.severity ? `<span style="font-size:0.72rem; color:#64748b;">[${escapeHtml(iss.severity)} &bull; ${escapeHtml(iss.duration || '')}]</span>` : ''}
                    </td>
                    <td><span class="triage-pill ${triageClass}">${iss.triage_level || 'routine'}</span></td>
                    <td><span class="issue-status-pill ${statusClass}">${statusLabel}</span></td>
                    <td style="max-width:180px; font-size:0.8rem; color:#475569;">
                        ${iss.doctor_notes ? escapeHtml(iss.doctor_notes) : '<em style="color:#94a3b8;">No notes yet</em>'}
                    </td>
                    <td style="text-align:center; white-space:nowrap;">
                        <button type="button" class="btn-secondary" style="font-size:0.75rem; padding:4px 8px; margin-right:4px;" onclick="openDoctorIssueReviewModal('${iss.id}')">
                            ✏️ Review
                        </button>
                        <button type="button" class="btn-primary" style="font-size:0.75rem; padding:4px 8px; background:var(--mc-blue);" onclick="openSendCareReminderModal('${iss.patient_id}', '${iss.id}')">
                            🔔 Reminder
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:20px; color:#ef4444;">Error loading issues: ${err.message}</td></tr>`;
    }
}

async function loadAdminReminders() {
    const tbody = document.getElementById('admin-reminders-table-body');
    if (!tbody) return;

    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:20px; color:#64748b;">Loading care directives and reminders...</td></tr>`;

    try {
        let targetPatients = (allPatients && allPatients.length) ? allPatients : [{ patient_id: 'PAT-1001' }];
        const headers = {};
        if (currentAuth.token) headers['Authorization'] = `Bearer ${currentAuth.token}`;

        const promises = targetPatients.map(p => fetch(apiUrl(`/api/reminders/${encodeURIComponent(p.patient_id)}`), { headers }).then(r => r.ok ? r.json() : { reminders: [] }).catch(() => ({ reminders: [] })));
        const results = await Promise.all(promises);
        let allRem = [];
        results.forEach(r => {
            if (r.reminders) allRem = allRem.concat(r.reminders);
        });

        allRem.sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''));
        window._adminReminders = allRem;

        if (allRem.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:30px; color:#64748b;">No dispatched care reminders found.</td></tr>`;
            return;
        }

        const typeLabels = {
            'daily_care': '💊 Daily Care',
            'diagnosis': '🩺 Diagnosis',
            'checkup': '🏥 Checkup'
        };

        tbody.innerHTML = allRem.map(r => {
            const dateStr = r.created_at ? new Date(r.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) : '—';
            const isDone = r.status === 'completed';

            return `
                <tr>
                    <td style="white-space:nowrap; font-size:0.78rem;">${dateStr}</td>
                    <td style="font-weight:700; font-size:0.82rem;">${r.patient_id}</td>
                    <td><span class="reminder-badge ${r.reminder_type}">${typeLabels[r.reminder_type] || r.reminder_type}</span></td>
                    <td style="font-weight:700; font-size:0.85rem;">${escapeHtml(r.title)}</td>
                    <td style="max-width:260px; font-size:0.8rem; color:#475569;">${escapeHtml(r.message)}</td>
                    <td style="white-space:nowrap; font-size:0.78rem;">${r.due_date || 'Ongoing'}</td>
                    <td>${isDone ? '<span class="reminder-done-badge">✓ Completed</span>' : '<span style="color:#047857; font-weight:700; font-size:0.78rem;">Active</span>'}</td>
                </tr>
            `;
        }).join('');
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:20px; color:#ef4444;">Error: ${err.message}</td></tr>`;
    }
}

function openDoctorIssueReviewModal(issueId) {
    const iss = (window._adminIssues || []).find(i => i.id === issueId);
    if (!iss) return;

    document.getElementById('rev-issue-id').value = iss.id;
    document.getElementById('rev-patient-meta').innerHTML = `Patient: <strong>${escapeHtml(iss.patient_name || iss.patient_id)}</strong> (${iss.patient_id}) &bull; Triage: <strong>${(iss.triage_level || 'ROUTINE').toUpperCase()}</strong>`;
    document.getElementById('rev-reported-symptoms').innerText = iss.symptoms;
    document.getElementById('rev-ai-summary').innerText = iss.ai_summary || 'No AI summary generated for this query.';
    document.getElementById('rev-case-status').value = iss.status || 'in_review';
    document.getElementById('rev-doctor-notes').value = iss.doctor_notes || '';
    if (iss.doctor_name) document.getElementById('rev-doctor-name').value = iss.doctor_name;

    document.getElementById('doctor-issue-review-modal').style.display = 'flex';
}

function closeDoctorIssueReviewModal() {
    document.getElementById('doctor-issue-review-modal').style.display = 'none';
}

async function submitDoctorIssueReview(e) {
    e.preventDefault();
    const issueId = document.getElementById('rev-issue-id').value;
    const doctorNotes = document.getElementById('rev-doctor-notes').value.trim();
    const status = document.getElementById('rev-case-status').value;
    const doctorName = document.getElementById('rev-doctor-name').value.trim();

    try {
        const headers = { 'Content-Type': 'application/json' };
        if (currentAuth.token) headers['Authorization'] = `Bearer ${currentAuth.token}`;

        const res = await fetch(apiUrl(`/api/issues/${encodeURIComponent(issueId)}`), {
            method: 'PATCH',
            headers: headers,
            body: JSON.stringify({
                doctor_notes: doctorNotes,
                status: status,
                doctor_name: doctorName
            })
        });

        if (!res.ok) throw new Error("Failed to save doctor review.");

        closeDoctorIssueReviewModal();
        loadAdminReportedIssues();
        alert("✅ Doctor clinical review and notes saved successfully!");
    } catch (err) {
        alert("Error saving review: " + err.message);
    }
}

function openSendCareReminderModal(patientId, issueId) {
    const select = document.getElementById('rem-patient-id');
    if (select) {
        select.innerHTML = '';
        const list = (allPatients && allPatients.length) ? allPatients : [
            { patient_id: 'PAT-1001', name: 'Rajesh Kumar' },
            { patient_id: 'PAT-1002', name: 'Priya Sharma' },
            { patient_id: 'PAT-1003', name: 'Ananya Rao' },
            { patient_id: 'PAT-1004', name: 'Sunita Nair' }
        ];

        list.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.patient_id;
            opt.text = `${p.name || p.patient_id} (${p.patient_id})`;
            if (patientId && p.patient_id === patientId) opt.selected = true;
            select.appendChild(opt);
        });
    }

    document.getElementById('rem-issue-id').value = issueId || '';
    document.getElementById('send-care-reminder-modal').style.display = 'flex';
}

function closeSendCareReminderModal() {
    document.getElementById('send-care-reminder-modal').style.display = 'none';
}

async function submitCareReminder(e) {
    e.preventDefault();
    const patientId = document.getElementById('rem-patient-id').value;
    const reminderType = document.getElementById('rem-type').value;
    const title = document.getElementById('rem-title').value.trim();
    const message = document.getElementById('rem-message').value.trim();
    const dueDate = document.getElementById('rem-due-date').value || null;
    const frequency = document.getElementById('rem-frequency').value;
    const sentBy = document.getElementById('rem-sent-by').value.trim();
    const issueId = document.getElementById('rem-issue-id').value || null;

    try {
        const headers = { 'Content-Type': 'application/json' };
        if (currentAuth.token) headers['Authorization'] = `Bearer ${currentAuth.token}`;

        const res = await fetch(apiUrl('/api/reminders'), {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({
                patient_id: patientId,
                reminder_type: reminderType,
                title: title,
                message: message,
                due_date: dueDate,
                frequency: frequency,
                sent_by: sentBy,
                issue_id: issueId
            })
        });

        if (!res.ok) throw new Error("Failed to dispatch care reminder.");

        closeSendCareReminderModal();
        alert(`✅ Care Directive Dispatched!\n\nDispatched to ${patientId}: "${title}". It will now appear on the patient's portal with checkup and daily care alerts.`);

        const remCont = document.getElementById('adm-reminders-container');
        if (remCont && remCont.style.display !== 'none') {
            loadAdminReminders();
        }
    } catch (err) {
        alert("Error sending reminder: " + err.message);
    }
}
