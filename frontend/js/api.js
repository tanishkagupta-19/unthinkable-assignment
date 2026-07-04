const API_URL = '/api';

class ApiClient {
    static getToken() {
        return localStorage.getItem('token');
    }

    static async request(endpoint, options = {}) {
        const token = this.getToken();
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        // Handle URL encoded form data (for OAuth token endpoint)
        let body = options.body;
        if (options.isForm) {
            headers['Content-Type'] = 'application/x-www-form-urlencoded';
            body = new URLSearchParams(options.body).toString();
        } else if (body) {
            body = JSON.stringify(body);
        }

        const response = await fetch(`${API_URL}${endpoint}`, {
            ...options,
            headers,
            body
        });

        const data = await response.json();

        if (!response.ok) {
            let errorMsg = 'API request failed';
            if (data.detail) {
                if (typeof data.detail === 'string') {
                    errorMsg = data.detail;
                } else if (Array.isArray(data.detail)) {
                    errorMsg = data.detail.map(e => `${e.loc[e.loc.length - 1]}: ${e.msg}`).join(', ');
                } else {
                    errorMsg = JSON.stringify(data.detail);
                }
            }
            throw new Error(errorMsg);
        }

        return data;
    }

    // Auth
    static login(email, password) {
        return this.request('/auth/login', {
            method: 'POST',
            body: { email, password }
        });
    }

    static register(data) {
        return this.request('/auth/register', {
            method: 'POST',
            body: data
        });
    }

    static getMe() {
        return this.request('/auth/me');
    }

    // Patients
    static searchDoctors(specialisation = '') {
        const query = specialisation ? `?specialisation=${specialisation}` : '';
        return this.request(`/patients/doctors${query}`);
    }

    static getDoctorSlots(doctorId, date) {
        return this.request(`/patients/doctors/${doctorId}/slots?appointment_date=${date}`);
    }

    static holdSlot(doctorId, date, time) {
        return this.request('/patients/appointments/hold', {
            method: 'POST',
            body: { doctor_id: doctorId, appointment_date: date, start_time: time }
        });
    }

    static bookSlot(holdId, symptomsText) {
        return this.request('/patients/appointments/book', {
            method: 'POST',
            body: { hold_id: holdId, symptoms_text: symptomsText }
        });
    }

    static getPatientAppointments() {
        return this.request('/patients/appointments');
    }

    static getPatientAppointmentDetail(id) {
        return this.request(`/patients/appointments/${id}`);
    }

    static cancelAppointment(id) {
        return this.request(`/patients/appointments/${id}/cancel`, { method: 'PUT' });
    }

    // Doctors
    static getDoctorProfile() {
        return this.request('/doctors/profile');
    }

    static getDoctorAppointments() {
        return this.request('/doctors/appointments');
    }

    static getDoctorAppointmentDetail(id) {
        return this.request(`/doctors/appointments/${id}`);
    }

    static completeAppointment(id, notes, prescription) {
        return this.request(`/doctors/appointments/${id}/complete`, {
            method: 'PUT',
            body: { doctor_notes: notes, prescription_text: prescription }
        });
    }

    // Admin
    static getAdminDoctors() {
        return this.request('/admin/doctors');
    }

    static createDoctor(data) {
        return this.request('/admin/doctors', {
            method: 'POST',
            body: data
        });
    }

    static markDoctorLeave(doctorId, date, reason) {
        return this.request(`/admin/doctors/${doctorId}/leave`, {
            method: 'POST',
            body: { leave_date: date, reason: reason }
        });
    }

    static getAdminAppointments() {
        return this.request('/admin/appointments');
    }
}