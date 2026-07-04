// State
let currentUser = null;
let currentHoldTimer = null;
let currentHoldId = null;

// DOM Elements
const views = {
    loading: document.getElementById('view-loading'),
    auth: document.getElementById('view-auth'),
    patient: document.getElementById('view-patient'),
    doctor: document.getElementById('view-doctor'),
    admin: document.getElementById('view-admin')
};

// Utilities
function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        if (toast.parentElement) toast.remove();
    }, 3000);
}

function switchView(viewName) {
    Object.values(views).forEach(v => {
        v.classList.remove('active');
        v.classList.add('hidden');
    });
    views[viewName].classList.remove('hidden');
    views[viewName].classList.add('active');

    document.getElementById('navbar').classList.toggle('hidden', viewName === 'auth' || viewName === 'loading');
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
}

function formatTime(timeString) {
    return timeString.substring(0, 5); // HH:MM
}

function createBadge(level) {
    let className = 'badge-medium';
    if (level === 'Low') className = 'badge-low';
    if (level === 'High') className = 'badge-high';
    return `<span class="badge ${className}">${escapeHtml(level)}</span>`;
}

// Modal handling
function openModal(modalId) {
    document.getElementById(modalId).classList.remove('hidden');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.add('hidden');
}

document.querySelectorAll('.close-modal').forEach(btn => {
    btn.addEventListener('click', (e) => {
        e.target.closest('.modal').classList.add('hidden');
    });
});

// App Initialization
async function init() {
    const token = ApiClient.getToken();
    if (!token) {
        switchView('auth');
        return;
    }

    try {
        currentUser = await ApiClient.getMe();
        document.getElementById('nav-user-name').textContent = `Hello, ${currentUser.full_name} (${currentUser.role})`;

        if (currentUser.role === 'patient') {
            await initPatientDashboard();
        } else if (currentUser.role === 'doctor') {
            await initDoctorDashboard();
        } else if (currentUser.role === 'admin') {
            await initAdminDashboard();
        } else {
            switchView('auth');
        }
    } catch (err) {
        showToast('Failed to load user: ' + err.message, 'error');
        localStorage.removeItem('token');
        switchView('auth');
    }
}

document.getElementById('logout-btn').addEventListener('click', () => {
    localStorage.removeItem('token');
    currentUser = null;
    switchView('auth');
});

// --- Auth Flow ---
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.auth-form').forEach(f => {
            f.classList.remove('active');
            f.classList.add('hidden');
        });

        e.target.classList.add('active');
        const targetForm = document.getElementById(e.target.dataset.target);
        targetForm.classList.remove('hidden');
        targetForm.classList.add('active');
    });
});

document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;

    try {
        const res = await ApiClient.login(email, password);
        localStorage.setItem('token', res.access_token);
        showToast('Login successful');
        init();
    } catch (err) {
        showToast(err.message, 'error');
    }
});

document.getElementById('register-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = {
        full_name: document.getElementById('reg-name').value,
        email: document.getElementById('reg-email').value,
        password: document.getElementById('reg-password').value,
        role: document.getElementById('reg-role').value
    };

    try {
        await ApiClient.register(data);
        showToast('Registration successful! Please login.');
        document.querySelector('[data-target="login-form"]').click();
    } catch (err) {
        showToast(err.message, 'error');
    }
});

// --- Patient Flow ---
async function initPatientDashboard() {
    switchView('patient');
    await loadPatientAppointments();
}

async function loadPatientAppointments() {
    try {
        const appts = await ApiClient.getPatientAppointments();
        const container = document.getElementById('patient-appointments-list');
        container.innerHTML = '';

        if (appts.length === 0) {
            container.innerHTML = '<p class="text-muted">No appointments found.</p>';
            return;
        }

        appts.forEach(appt => {
            const card = document.createElement('div');
            card.className = 'card';
            let statusBadge = appt.status === 'booked' ? 'badge-booked' : (appt.status === 'completed' ? 'badge-completed' : 'badge-cancelled');

            card.innerHTML = `
                <div class="flex-between">
                    <h4>Dr. ID: ${escapeHtml(appt.doctor_id)}</h4>
                    <span class="badge ${statusBadge}">${escapeHtml(appt.status)}</span>
                </div>
                <p>Date: <strong>${formatDate(appt.appointment_date)}</strong> at <strong>${formatTime(appt.start_time)}</strong></p>
                <div class="mt-2 flex-gap">
                    <button class="btn btn-sm btn-secondary" onclick="viewPatientAppt(${appt.id})">Details</button>
                    ${appt.status === 'booked' ? `<button class="btn btn-sm btn-danger" onclick="cancelAppt(${appt.id})">Cancel</button>` : ''}
                </div>
            `;
            container.appendChild(card);
        });
    } catch (err) {
        showToast(err.message, 'error');
    }
}

document.getElementById('search-doctors-btn').addEventListener('click', async () => {
    const spec = document.getElementById('search-specialisation').value;
    try {
        const doctors = await ApiClient.searchDoctors(spec);
        const container = document.getElementById('search-results');
        container.innerHTML = '<h4>Available Doctors</h4>';

        if (doctors.length === 0) {
            container.innerHTML += '<p class="text-muted">No doctors found.</p>';
            return;
        }

        doctors.forEach(doc => {
            const div = document.createElement('div');
            div.className = 'card mt-2';
            div.innerHTML = `
                <div class="flex-between">
                    <div>
                        <strong>Dr. ${escapeHtml(doc.doctor_name)}</strong>
                        <div class="text-sm text-muted">${escapeHtml(doc.specialisation)}</div>
                    </div>
                    <button class="btn btn-sm btn-primary" onclick="checkSlots(${doc.id})">Check Slots</button>
                </div>
            `;
            container.appendChild(div);
        });
    } catch (err) {
        showToast(err.message, 'error');
    }
});

async function checkSlots(doctorId) {
    const date = prompt("Enter date (YYYY-MM-DD)", new Date().toISOString().split('T')[0]);
    if (!date) return;

    try {
        const slots = await ApiClient.getDoctorSlots(doctorId, date);
        const container = document.getElementById('slots-container');
        container.classList.remove('hidden');
        container.innerHTML = `<h4>Slots for ${escapeHtml(date)}</h4><div class="slots-grid mt-2"></div>`;
        const grid = container.querySelector('.slots-grid');

        if (slots.length === 0) {
            grid.innerHTML = '<p class="text-muted">No slots available (Doctor might be on leave).</p>';
            return;
        }

        slots.forEach(slot => {
            const btn = document.createElement('button');
            btn.className = 'slot-btn';
            btn.textContent = formatTime(slot.start_time);
            btn.disabled = !slot.is_available;

            if (slot.is_available) {
                btn.onclick = () => holdSlot(doctorId, date, slot.start_time, btn);
            }
            grid.appendChild(btn);
        });
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function holdSlot(doctorId, date, time, btnElement) {
    try {
        const res = await ApiClient.holdSlot(doctorId, date, time);
        currentHoldId = res.hold_id;

        document.querySelectorAll('.slot-btn').forEach(b => b.classList.remove('selected'));
        btnElement.classList.add('selected');

        document.getElementById('booking-form-container').classList.remove('hidden');
        document.getElementById('booking-symptoms').value = '';

        // Start 5 min timer
        if (currentHoldTimer) clearInterval(currentHoldTimer);
        let seconds = 300;
        currentHoldTimer = setInterval(() => {
            seconds--;
            const m = Math.floor(seconds / 60).toString().padStart(2, '0');
            const s = (seconds % 60).toString().padStart(2, '0');
            document.getElementById('hold-timer').textContent = `${m}:${s}`;
            if (seconds <= 0) {
                clearInterval(currentHoldTimer);
                document.getElementById('booking-form-container').classList.add('hidden');
                showToast('Hold expired, please select slot again', 'warning');
            }
        }, 1000);

    } catch (err) {
        showToast(err.message, 'error');
    }
}

document.getElementById('confirm-booking-btn').addEventListener('click', async () => {
    const symptoms = document.getElementById('booking-symptoms').value;
    if (!symptoms) {
        showToast('Please enter your symptoms', 'warning');
        return;
    }

    try {
        await ApiClient.bookSlot(currentHoldId, symptoms);
        showToast('Appointment booked! Confirmation email sent.');
        clearInterval(currentHoldTimer);
        document.getElementById('booking-form-container').classList.add('hidden');
        document.getElementById('slots-container').classList.add('hidden');
        document.getElementById('search-results').innerHTML = '';
        await loadPatientAppointments();
    } catch (err) {
        showToast(err.message, 'error');
    }
});

async function cancelAppt(id) {
    if (!confirm('Cancel this appointment?')) return;
    try {
        await ApiClient.cancelAppointment(id);
        showToast('Appointment cancelled. Email notice sent.');
        await loadPatientAppointments();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function viewPatientAppt(id) {
    try {
        const appt = await ApiClient.getPatientAppointmentDetail(id);
        const body = document.getElementById('modal-appt-body');

        let html = `
            <p><strong>Status:</strong> <span class="badge badge-${appt.status === 'booked' ? 'booked' : 'completed'}">${escapeHtml(appt.status)}</span></p>
            <p><strong>Date:</strong> ${formatDate(appt.appointment_date)} ${formatTime(appt.start_time)}</p>
            <div class="mt-4">
                <h5>Your Symptoms:</h5>
                <p class="text-muted">${escapeHtml(appt.symptoms_text)}</p>
            </div>
        `;

        if (appt.status === 'completed' && appt.post_visit_summary) {
            html += `
                <div class="mt-4 p-4" style="background: rgba(16,185,129,0.1); border-radius: var(--radius-md); border-left: 4px solid var(--success);">
                    <h5>Post-Visit Summary</h5>
                    <p class="mt-2" style="white-space: pre-wrap;">${escapeHtml(appt.post_visit_summary)}</p>
                </div>
            `;
        } else if (appt.status === 'completed') {
            html += `<p class="mt-4 text-muted">Summary is being generated...</p>`;
        }

        body.innerHTML = html;
        openModal('modal-appointment-detail');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// --- Doctor Flow ---
async function initDoctorDashboard() {
    switchView('doctor');
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('doctor-schedule-date').value = today;
    await loadDoctorAppointments(today);
}

document.getElementById('load-schedule-btn').addEventListener('click', async () => {
    const date = document.getElementById('doctor-schedule-date').value;
    await loadDoctorAppointments(date);
});

async function loadDoctorAppointments(date) {
    try {
        let query = '';
        if (date) query = `?appointment_date=${date}`;

        const appts = await ApiClient.request(`/doctors/appointments${query}`);
        const container = document.getElementById('doctor-appointments-list');
        container.innerHTML = '';

        if (appts.length === 0) {
            container.innerHTML = '<p class="text-muted">No appointments for this date.</p>';
            document.getElementById('doctor-appt-detail').innerHTML = '<div class="placeholder-text">Select an appointment to view details</div>';
            return;
        }

        appts.forEach(appt => {
            const card = document.createElement('div');
            card.className = 'card';
            card.style.cursor = 'pointer';
            card.onclick = () => viewDoctorApptDetail(appt.id);

            card.innerHTML = `
                <div class="flex-between">
                    <strong>${formatTime(appt.start_time)}</strong>
                    <span class="badge badge-${appt.status === 'booked' ? 'booked' : 'completed'}">${escapeHtml(appt.status)}</span>
                </div>
                <div class="text-sm mt-2 text-muted">Patient ID: ${escapeHtml(appt.patient_id)}</div>
            `;
            container.appendChild(card);
        });
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function viewDoctorApptDetail(id) {
    try {
        const appt = await ApiClient.getDoctorAppointmentDetail(id);
        const container = document.getElementById('doctor-appt-detail');

        let html = `
            <div class="flex-between">
                <h3>Appointment #${appt.id}</h3>
                <span class="badge badge-${appt.status === 'booked' ? 'booked' : 'completed'}">${escapeHtml(appt.status)}</span>
            </div>
            <p class="text-muted mt-2">${formatDate(appt.appointment_date)} at ${formatTime(appt.start_time)}</p>
        `;

        if (appt.pre_visit_summary) {
            html += `
                <div class="card mt-4" style="background: rgba(59,130,246,0.1); border-left: 4px solid var(--accent-primary);">
                    <h4>AI Pre-Visit Brief ${createBadge(appt.urgency_level)}</h4>
                    <p class="mt-2 text-sm" style="white-space: pre-wrap;">${escapeHtml(appt.pre_visit_summary)}</p>
                </div>
            `;
        }

        html += `
            <div class="mt-4">
                <h5>Raw Symptoms</h5>
                <p class="text-muted text-sm">${escapeHtml(appt.symptoms_text)}</p>
            </div>
        `;

        if (appt.status === 'booked') {
            html += `
                <div class="mt-4">
                    <h5>Complete Visit</h5>
                    <div class="form-group mt-2">
                        <label>Clinical Notes</label>
                        <textarea id="doc-notes" rows="3" placeholder="Enter notes..."></textarea>
                    </div>
                    <div class="form-group">
                        <label>Prescription (Optional)</label>
                        <textarea id="doc-prescription" rows="2" placeholder="Medication details..."></textarea>
                    </div>
                    <button class="btn btn-primary w-100" onclick="completeVisit(${appt.id})">Submit &amp; Complete</button>
                </div>
            `;
        } else if (appt.status === 'completed') {
            html += `
                <div class="mt-4">
                    <h5>Clinical Notes</h5>
                    <p class="text-muted text-sm">${escapeHtml(appt.doctor_notes)}</p>
                    <h5>Prescription</h5>
                    <p class="text-muted text-sm">${escapeHtml(appt.prescription_text) || 'None'}</p>
                </div>
            `;
        }

        container.innerHTML = html;

    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function completeVisit(id) {
    const notes = document.getElementById('doc-notes').value;
    const prescription = document.getElementById('doc-prescription').value;

    if (!notes) {
        showToast('Clinical notes are required', 'warning');
        return;
    }

    try {
        await ApiClient.completeAppointment(id, notes, prescription);
        showToast('Visit completed! AI summary generating for patient.');
        viewDoctorApptDetail(id); // reload detail
        const date = document.getElementById('doctor-schedule-date').value;
        loadDoctorAppointments(date); // refresh list
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// --- Admin Flow ---
async function initAdminDashboard() {
    switchView('admin');
    await loadAdminDoctors();
    await loadAdminAppointments();
}

async function loadAdminDoctors() {
    try {
        const doctors = await ApiClient.getAdminDoctors();
        const container = document.getElementById('admin-doctors-list');
        container.innerHTML = '';

        doctors.forEach(doc => {
            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = `
                <div class="flex-between">
                    <strong>Dr. ${escapeHtml(doc.doctor_name)}</strong>
                    <div class="flex-gap">
                        <button class="btn btn-sm btn-secondary" onclick="openLeaveModal(${doc.id}, '${escapeHtml(doc.doctor_name).replace(/'/g, "\\'")}')">Mark Leave</button>
                    </div>
                </div>
                <div class="text-sm text-muted">${escapeHtml(doc.specialisation)} | ${formatTime(doc.working_hours_start)} - ${formatTime(doc.working_hours_end)}</div>
            `;
            container.appendChild(card);
        });
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function loadAdminAppointments() {
    try {
        const appts = await ApiClient.getAdminAppointments();
        const container = document.getElementById('admin-appointments-list');
        container.innerHTML = '';

        appts.slice(0, 10).forEach(appt => { // Just show recent 10 for minimalist view
            const card = document.createElement('div');
            card.className = 'card flex-between';
            card.innerHTML = `
                <div>
                    <div>Appt #${appt.id} (Doc ${escapeHtml(appt.doctor_id)} / Pat ${escapeHtml(appt.patient_id)})</div>
                    <div class="text-sm text-muted">${formatDate(appt.appointment_date)} ${formatTime(appt.start_time)}</div>
                </div>
                <span class="badge badge-${appt.status === 'booked' ? 'booked' : (appt.status === 'completed' ? 'completed' : 'cancelled')}">${escapeHtml(appt.status)}</span>
            `;
            container.appendChild(card);
        });
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// Add Doctor Flow (Admin)
document.getElementById('add-doctor-btn').addEventListener('click', () => {
    document.getElementById('new-doc-name').value = '';
    document.getElementById('new-doc-email').value = '';
    document.getElementById('new-doc-password').value = '';
    document.getElementById('new-doc-start').value = '09:00';
    document.getElementById('new-doc-end').value = '17:00';
    document.getElementById('new-doc-slot-duration').value = '30';
    openModal('modal-add-doctor');
});

document.getElementById('submit-add-doctor-btn').addEventListener('click', async () => {
    const name = document.getElementById('new-doc-name').value;
    const email = document.getElementById('new-doc-email').value;
    const password = document.getElementById('new-doc-password').value;
    const specialisation = document.getElementById('new-doc-specialisation').value;
    const start = document.getElementById('new-doc-start').value;
    const end = document.getElementById('new-doc-end').value;
    const slotDuration = document.getElementById('new-doc-slot-duration').value;

    if (!name || !email || !password) {
        showToast('Name, email, and password are required', 'warning');
        return;
    }

    try {
        // Step 1: create the underlying user account
        const user = await ApiClient.register({
            email,
            password,
            full_name: name,
            role: 'doctor'
        });

        // Step 2: create the doctor profile linked to that user
        // NOTE: verify these field names match your actual DoctorCreate
        // Pydantic schema in the backend (app/services or app/schemas).
        // If your schema uses different field names, update the object below.
        await ApiClient.createDoctor({
            user_id: user.id,
            specialisation: specialisation,
            working_hours_start: start,
            working_hours_end: end,
            slot_duration_minutes: parseInt(slotDuration, 10)
        });

        showToast('Doctor created successfully');
        closeModal('modal-add-doctor');
        await loadAdminDoctors();
    } catch (err) {
        showToast(err.message, 'error');
    }
});

// Leave Flow
let selectedLeaveDoctorId = null;
function openLeaveModal(id, name) {
    selectedLeaveDoctorId = id;
    document.getElementById('leave-doctor-name').textContent = 'Dr. ' + name;
    document.getElementById('leave-date').value = '';
    document.getElementById('leave-reason').value = '';
    openModal('modal-manage-leave');
}

document.getElementById('submit-leave-btn').addEventListener('click', async () => {
    const date = document.getElementById('leave-date').value;
    const reason = document.getElementById('leave-reason').value;
    if (!date) return showToast('Date required', 'warning');

    try {
        await ApiClient.markDoctorLeave(selectedLeaveDoctorId, date, reason);
        showToast('Leave marked successfully. Affected appointments cancelled & notified.');
        closeModal('modal-manage-leave');
    } catch (err) {
        showToast(err.message, 'error');
    }
});

// Boot
window.onload = init;