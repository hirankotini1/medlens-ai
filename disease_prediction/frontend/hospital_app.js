/**
 * MedLens AI - Enterprise Hospital Workstation & Clinical Operations Client
 * Standalone frontend controller for hospital.html
 */

let currentStaff = {
    name: "Dr. Anita Roy",
    title: "Senior Consultant Physician, MD (Gen Med)",
    role: "doctor",
    email: "dr.anita@apex.medlens.io",
    empId: "DOC-4892",
    regNo: "NMC-MCI-48921-A",
    hospital: "Apex Multispeciality Hospital - Main Campus",
    tenantId: "tenant_medlens_apex",
    token: null
};

let isStaffAuthenticated = true; // Default to authenticated for instant preview or toggleable

// --------------------------------------------------------------------------
// 1. 60FPS GPU-ACCELERATED CARDIAC EKG CANVAS ENGINE
// --------------------------------------------------------------------------
function initEmergencyEkgCanvas() {
    const canvas = document.getElementById('emergency-ekg-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    function resizeCanvas() {
        const rect = canvas.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        canvas.width = (rect.width || 220) * dpr;
        canvas.height = (rect.height || 36) * dpr;
        ctx.scale(dpr, dpr);
    }
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    let progress = 0;
    const waveform = [
        { pos: 0.00, y: 0.00 }, { pos: 0.15, y: 0.00 },
        { pos: 0.20, y: -0.15 }, { pos: 0.25, y: 0.00 },
        { pos: 0.35, y: 0.00 }, { pos: 0.40, y: 0.10 },
        { pos: 0.43, y: -0.90 }, { pos: 0.47, y: 0.35 },
        { pos: 0.50, y: 0.00 }, { pos: 0.65, y: 0.00 },
        { pos: 0.75, y: -0.25 }, { pos: 0.85, y: 0.00 },
        { pos: 1.00, y: 0.00 }
    ];

    function getWaveY(t) {
        t = t % 1.0;
        for (let i = 0; i < waveform.length - 1; i++) {
            if (t >= waveform[i].pos && t <= waveform[i + 1].pos) {
                const segT = (t - waveform[i].pos) / (waveform[i + 1].pos - waveform[i].pos);
                return waveform[i].y + (waveform[i + 1].y - waveform[i].y) * segT;
            }
        }
        return 0;
    }

    let lastTime = performance.now();
    function animate(currentTime) {
        const delta = Math.min((currentTime - lastTime) / 1000, 0.1);
        lastTime = currentTime;
        progress = (progress + delta * 0.45) % 1.0;

        const rect = canvas.getBoundingClientRect();
        const width = rect.width || 220;
        const height = rect.height || 36;
        const midY = height / 2;
        const amp = (height / 2) - 4;

        ctx.clearRect(0, 0, width, height);

        // Baseline trace
        ctx.beginPath();
        ctx.strokeStyle = 'rgba(239, 68, 68, 0.18)';
        ctx.lineWidth = 1.5;
        for (let x = 0; x < width; x += 3) {
            const t = (x / width);
            const y = midY + getWaveY(t) * amp;
            if (x === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.stroke();

        // Active glowing cardiac pulse
        const headX = progress * width;
        const trailLength = width * 0.40;
        const startX = Math.max(0, headX - trailLength);

        const grad = ctx.createLinearGradient(startX, 0, headX, 0);
        grad.addColorStop(0, 'rgba(239, 68, 68, 0)');
        grad.addColorStop(0.7, 'rgba(239, 68, 68, 0.6)');
        grad.addColorStop(1, '#ef4444');

        ctx.beginPath();
        ctx.strokeStyle = grad;
        ctx.lineWidth = 2.5;
        ctx.shadowColor = '#ef4444';
        ctx.shadowBlur = 8;

        for (let x = startX; x <= headX; x += 2) {
            const t = (x / width);
            const y = midY + getWaveY(t) * amp;
            if (x === startX) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.stroke();

        // Neon tracer point
        const headY = midY + getWaveY(progress) * amp;
        ctx.beginPath();
        ctx.arc(headX, headY, 3.5, 0, Math.PI * 2);
        ctx.fillStyle = '#ffffff';
        ctx.shadowColor = '#ef4444';
        ctx.shadowBlur = 12;
        ctx.fill();

        ctx.shadowBlur = 0;
        requestAnimationFrame(animate);
    }
    requestAnimationFrame(animate);
}

// --------------------------------------------------------------------------
// 2. ROLE DEFINITIONS & ROLE SWITCHING (RBAC)
// --------------------------------------------------------------------------
const STAFF_PROFILES = {
    doctor: {
        name: "Dr. Anita Roy",
        title: "Senior Consultant Physician, MD",
        role: "doctor",
        roleBadge: "Attending Physician",
        badgeColor: "#0284c7",
        badgeBg: "#e0f2fe",
        email: "dr.anita@apex.medlens.io",
        empId: "DOC-4892",
        regNo: "NMC-MCI-48921-A",
        hospital: "Apex Multispeciality Hospital",
        tabName: "doctor"
    },
    receptionist: {
        name: "Rajesh Kumar",
        title: "OPD Front Desk Supervisor",
        role: "receptionist",
        roleBadge: "OPD Receptionist",
        badgeColor: "#059669",
        badgeBg: "#ecfdf5",
        email: "reception@apex.medlens.io",
        empId: "REC-1104",
        regNo: "DESK-A1",
        hospital: "Apex Multispeciality Hospital",
        tabName: "receptionist"
    },
    lab_staff: {
        name: "Vikram Seth",
        title: "Senior Pathology Technologist",
        role: "lab_staff",
        roleBadge: "Lab Technician",
        badgeColor: "#d97706",
        badgeBg: "#fef3c7",
        email: "pathology@apex.medlens.io",
        empId: "LAB-3390",
        regNo: "PATH-9921",
        hospital: "Apex Multispeciality Hospital",
        tabName: "lab_staff"
    },
    ward_manager: {
        name: "Sister Mary Varghese",
        title: "Head Nurse & Ward Supervisor",
        role: "ward_manager",
        roleBadge: "Ward & Bed Manager",
        badgeColor: "#7c3aed",
        badgeBg: "#f3e8ff",
        email: "ward.manager@apex.medlens.io",
        empId: "WRD-8821",
        regNo: "NUR-7721",
        hospital: "Apex Multispeciality Hospital",
        tabName: "ward_manager"
    },
    operations_manager: {
        name: "Alok Verma",
        title: "Chief of Hospital Operations",
        role: "operations_manager",
        roleBadge: "Operations Manager",
        badgeColor: "#4f46e5",
        badgeBg: "#eef2ff",
        email: "ops.head@apex.medlens.io",
        empId: "OPS-9012",
        regNo: "MGMT-2026",
        hospital: "Apex Multispeciality Hospital",
        tabName: "operations_manager"
    },
    owner: {
        name: "Dr. S. K. Mukherjee",
        title: "Medical Director & Hospital Owner",
        role: "owner",
        roleBadge: "Hospital Administrator",
        badgeColor: "#dc2626",
        badgeBg: "#fef2f2",
        email: "admin@apex.medlens.io",
        empId: "DIR-0001",
        regNo: "HOSP-ADMIN-01",
        hospital: "Apex Multispeciality Hospital",
        tabName: "owner"
    }
};

function switchRole(roleKey) {
    if (!STAFF_PROFILES[roleKey]) return;
    currentStaff = Object.assign({}, STAFF_PROFILES[roleKey]);
    isStaffAuthenticated = true;
    sessionStorage.setItem('medlens_standalone_staff', JSON.stringify(currentStaff));
    renderHospitalApp();
    showToast(`Switched active workstation view to: ${currentStaff.roleBadge} (${currentStaff.name})`);
}

function handleStaffLogin(e) {
    if (e) e.preventDefault();
    const roleKey = document.getElementById('login-staff-role')?.value || 'doctor';
    switchRole(roleKey);
}

function handleStaffLogout() {
    isStaffAuthenticated = false;
    sessionStorage.removeItem('medlens_standalone_staff');
    renderHospitalApp();
    showToast('Signed out of Hospital Workstation.');
}

// --------------------------------------------------------------------------
// 3. UI RENDERING & WORKSPACE TAB MANAGEMENT
// --------------------------------------------------------------------------
function renderHospitalApp() {
    const unauthContainer = document.getElementById('hospital-unauth-container');
    const authDashboard = document.getElementById('hospital-auth-dashboard');
    const roleBadge = document.getElementById('staff-nav-role-badge');
    const staffNameEl = document.getElementById('staff-nav-name');

    if (isStaffAuthenticated) {
        if (unauthContainer) unauthContainer.style.display = 'none';
        if (authDashboard) authDashboard.style.display = 'block';

        if (roleBadge) {
            roleBadge.style.display = 'inline-flex';
            roleBadge.style.background = currentStaff.badgeBg;
            roleBadge.style.color = currentStaff.badgeColor;
            roleBadge.innerText = currentStaff.roleBadge;
        }

        if (staffNameEl) {
            staffNameEl.style.display = 'inline-block';
            staffNameEl.innerText = `${currentStaff.name} (${currentStaff.empId})`;
        }

        // Update greeting in dashboard
        const headerTitle = document.getElementById('staff-workspace-title');
        if (headerTitle) {
            headerTitle.innerHTML = `${currentStaff.roleBadge} Workstation &bull; <span style="font-weight:400; color:#64748b; font-size:1rem;">${currentStaff.hospital}</span>`;
        }

        // Show appropriate role section
        showRoleWorkspace(currentStaff.role);

        // Update role button highlights
        document.querySelectorAll('.role-switcher-btn').forEach(btn => {
            const btnRole = btn.getAttribute('data-role');
            if (btnRole === currentStaff.role) {
                btn.classList.add('active-role-btn');
                btn.style.borderColor = currentStaff.badgeColor;
                btn.style.boxShadow = `0 2px 8px ${currentStaff.badgeBg}`;
            } else {
                btn.classList.remove('active-role-btn');
                btn.style.borderColor = '#e2e8f0';
                btn.style.boxShadow = 'none';
            }
        });
    } else {
        if (unauthContainer) unauthContainer.style.display = 'block';
        if (authDashboard) authDashboard.style.display = 'none';
        if (roleBadge) roleBadge.style.display = 'none';
        if (staffNameEl) staffNameEl.style.display = 'none';
    }
}

function showRoleWorkspace(roleKey) {
    const roles = ['doctor', 'receptionist', 'lab_staff', 'ward_manager', 'operations_manager', 'owner'];
    roles.forEach(r => {
        const pane = document.getElementById(`workspace-${r}`);
        if (pane) {
            pane.style.display = (r === roleKey) ? 'block' : 'none';
        }
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// --------------------------------------------------------------------------
// 4. ROLE SPECIFIC ACTIONS & CLINICAL WORKFLOWS
// --------------------------------------------------------------------------

// A. Doctor e-Prescription Authoring
function handleDoctorPrescriptionSign(e) {
    if (e) e.preventDefault();
    const patientName = document.getElementById('rx-patient-select')?.value || 'Aarav Patel (APX-2026-9921)';
    const drug1 = document.getElementById('rx-drug-1')?.value || 'Tab. Paracetamol 650mg';
    const dose1 = document.getElementById('rx-dose-1')?.value || '1-0-1 after food';
    const notes = document.getElementById('rx-notes')?.value || 'Bed rest, maintain hydration.';

    const receipt = document.getElementById('rx-signed-stamp-card');
    if (!receipt) return;
    receipt.style.display = 'block';
    receipt.innerHTML = `
        <div style="background:#f0fdf4; border:1px solid #86efac; border-radius:12px; padding:1.25rem; margin-top:1rem; box-shadow:0 4px 12px rgba(22,101,52,0.08);">
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #bbf7d0; padding-bottom:0.75rem; margin-bottom:0.75rem;">
                <div>
                    <span style="background:#dcfce7; color:#15803d; font-size:0.75rem; font-weight:800; padding:3px 8px; border-radius:4px;">NMC COMPLIANT DIGITAL RX SIGNED</span>
                    <h4 style="margin:4px 0 0 0; color:#14532d; font-size:1.1rem;">Official Prescription Dispatched to Patient Sanctuary</h4>
                </div>
                <div style="font-family:monospace; font-size:0.85rem; color:#166534; background:#ffffff; padding:4px 8px; border-radius:4px; border:1px solid #bbf7d0;">
                    SIG: ${Math.random().toString(36).substring(2, 10).toUpperCase()}
                </div>
            </div>
            <div style="font-size:0.9rem; color:#1e293b; line-height:1.5;">
                <strong>Patient:</strong> ${patientName}<br/>
                <strong>Prescribed Meds:</strong> ${drug1} (${dose1})<br/>
                <strong>Physician Sign-Off:</strong> ${currentStaff.name}, ${currentStaff.title}<br/>
                <strong>Registration Stamp:</strong> ${currentStaff.regNo} &bull; Apex Multispeciality Hospital
            </div>
        </div>
    `;
    showToast('Prescription digitally signed and synced with patient records!');
}

// B. Receptionist OPD Token Dispatch
let currentTokenCounter = 25;
function handleReceptionTokenSubmit(e) {
    if (e) e.preventDefault();
    const name = document.getElementById('opd-reg-name')?.value || 'New Patient';
    const phone = document.getElementById('opd-reg-phone')?.value || '+91 98765 00000';
    const dept = document.getElementById('opd-reg-dept')?.value || 'General Medicine';

    currentTokenCounter++;
    const queueTbody = document.getElementById('opd-queue-tbody');
    if (queueTbody) {
        const tr = document.createElement('tr');
        tr.style.cssText = "border-bottom:1px solid #f1f5f9;";
        tr.innerHTML = `
            <td style="padding:10px; font-weight:800; color:#0284c7;">#OPD-${currentTokenCounter}</td>
            <td style="padding:10px; font-weight:600; color:#0f172a;">${name}</td>
            <td style="padding:10px; color:#64748b;">${phone}</td>
            <td style="padding:10px; color:#334155;">${dept}</td>
            <td style="padding:10px;"><span style="background:#fef3c7; color:#d97706; font-size:0.75rem; font-weight:700; padding:2px 8px; border-radius:4px;">WAITING</span></td>
            <td style="padding:10px;"><button onclick="this.closest('tr').remove(); showToast('Patient called into Doctor consultation room');" class="btn-secondary" style="padding:4px 10px; font-size:0.8rem;">Call In →</button></td>
        `;
        queueTbody.prepend(tr);
    }

    showToast(`Issued Outpatient Token #OPD-${currentTokenCounter} for ${name}`);
}

// C. Ward Bed Allocation & Discharge
function toggleBedState(bedId, currentStatus) {
    const bedBox = document.getElementById(`bed-${bedId}`);
    if (!bedBox) return;

    if (currentStatus === 'occupied') {
        bedBox.style.background = '#ecfdf5';
        bedBox.style.borderColor = '#a7f3d0';
        bedBox.innerHTML = `
            <div style="font-weight:800; color:#065f46;">${bedId}</div>
            <div style="font-size:0.75rem; color:#059669; font-weight:700;">AVAILABLE</div>
            <button onclick="toggleBedState('${bedId}', 'available')" style="margin-top:6px; border:none; background:#059669; color:#fff; font-size:0.7rem; padding:2px 8px; border-radius:4px; cursor:pointer;">Admit</button>
        `;
        showToast(`Bed ${bedId} has been vacated and marked sanitized.`);
    } else {
        bedBox.style.background = '#fef2f2';
        bedBox.style.borderColor = '#fecaca';
        bedBox.innerHTML = `
            <div style="font-weight:800; color:#991b1b;">${bedId}</div>
            <div style="font-size:0.75rem; color:#dc2626; font-weight:700;">OCCUPIED</div>
            <button onclick="toggleBedState('${bedId}', 'occupied')" style="margin-top:6px; border:none; background:#dc2626; color:#fff; font-size:0.7rem; padding:2px 8px; border-radius:4px; cursor:pointer;">Discharge</button>
        `;
        showToast(`Patient admitted to bed ${bedId}.`);
    }
}

// D. Staff 7-Day Single Use Token Generator
function generateStaffInviteToken() {
    const roleSelect = document.getElementById('invite-role-select')?.value || 'doctor';
    const email = document.getElementById('invite-email')?.value || 'new.clinician@apex.medlens.io';
    const token = "INV-" + Math.random().toString(36).substring(2, 10).toUpperCase() + "-" + Date.now().toString().slice(-4);

    const tokenBox = document.getElementById('staff-invite-token-output');
    if (!tokenBox) return;
    tokenBox.style.display = 'block';
    tokenBox.innerHTML = `
        <div style="background:#ffffff; border:1px solid #cbd5e1; border-radius:10px; padding:1rem; margin-top:1rem;">
            <div style="font-size:0.8rem; font-weight:700; color:#64748b;">7-DAY SINGLE-USE INVITATION TOKEN:</div>
            <div style="font-family:monospace; font-size:1.15rem; font-weight:800; color:#0284c7; margin:6px 0;">${token}</div>
            <div style="font-size:0.85rem; color:#334155;">Role: <strong>${roleSelect}</strong> &bull; Assigned Email: <code>${email}</code></div>
            <button onclick="navigator.clipboard.writeText('${token}'); showToast('Token copied to clipboard!');" class="btn-secondary" style="margin-top:8px; padding:4px 10px; font-size:0.8rem;">📋 Copy Token</button>
        </div>
    `;
    showToast('Secure staff onboarding token generated.');
}

// --------------------------------------------------------------------------
// 5. TOAST NOTIFICATIONS
// --------------------------------------------------------------------------
function showToast(msg) {
    let toast = document.getElementById('hospital-global-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'hospital-global-toast';
        toast.style.cssText = "position:fixed; bottom:24px; right:24px; background:#0f172a; color:#ffffff; padding:12px 20px; border-radius:10px; font-size:0.9rem; font-weight:600; box-shadow:0 8px 24px rgba(0,0,0,0.2); z-index:9999; display:flex; align-items:center; gap:8px; transition:opacity 0.3s ease;";
        document.body.appendChild(toast);
    }
    toast.innerHTML = `<span>🏥</span> ${msg}`;
    toast.style.opacity = '1';
    toast.style.display = 'flex';
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => { toast.style.display = 'none'; }, 300);
    }, 3200);
}

// --------------------------------------------------------------------------
// 6. INITIALIZATION ON LOAD
// --------------------------------------------------------------------------
window.addEventListener('DOMContentLoaded', () => {
    // Start cardiac canvas
    setTimeout(initEmergencyEkgCanvas, 150);

    // Restore saved staff session if present
    const saved = sessionStorage.getItem('medlens_standalone_staff');
    if (saved) {
        try {
            currentStaff = JSON.parse(saved);
            isStaffAuthenticated = true;
        } catch (e) {}
    }

    renderHospitalApp();
});

