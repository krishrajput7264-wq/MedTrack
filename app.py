import os
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify, send_from_directory
)
from werkzeug.security import check_password_hash
from config import Config
from services.db_service import DatabaseService
from services.sns_service import NotificationService
from services.storage_service import StorageService, allowed_file
from services.cloudwatch_logger import CloudWatchAuditLogger, logger

app = Flask(__name__)
app.config.from_object(Config)

# Ensure upload and data directories exist
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(Config.DATA_DIR, exist_ok=True)

# --------------------------------------------------------
# AUTHENTICATION DECORATORS
# --------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in to proceed.", "warning")
                return redirect(url_for("login"))
            if session.get("role") != required_role:
                flash(f"Access restricted. This section requires {required_role.capitalize()} privileges.", "danger")
                if session.get("role") == "patient":
                    return redirect(url_for("patient_dashboard"))
                else:
                    return redirect(url_for("doctor_dashboard"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --------------------------------------------------------
# CONTEXT PROCESSOR
# --------------------------------------------------------
@app.context_processor
def inject_global_context():
    return {
        "current_user_id": session.get("user_id"),
        "current_user_name": session.get("user_name"),
        "current_role": session.get("role"),
        "use_aws": Config.USE_AWS,
        "aws_region": Config.AWS_REGION
    }

# --------------------------------------------------------
# CORE APPLICATION ROUTES
# --------------------------------------------------------
@app.route("/")
def index():
    doctors = DatabaseService.list_doctors()
    return render_template("index.html", doctors=doctors)

@app.route("/architecture")
def architecture():
    """Redirect to main portal."""
    return redirect(url_for("index"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        if session.get("role") == "doctor":
            return redirect(url_for("doctor_dashboard"))
        return redirect(url_for("patient_dashboard"))

    if request.method == "POST":
        role = request.form.get("role", "patient").strip().lower()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = None
        actual_role = role
        # Smart role detection: check preferred role first, fallback to the other
        if role == "doctor":
            user = DatabaseService.get_doctor_by_email(email)
            if not user:
                fallback = DatabaseService.get_patient_by_email(email)
                if fallback:
                    user = fallback
                    actual_role = "patient"
        else:
            user = DatabaseService.get_patient_by_email(email)
            if not user:
                fallback = DatabaseService.get_doctor_by_email(email)
                if fallback:
                    user = fallback
                    actual_role = "doctor"

        if user and check_password_hash(user.get("PasswordHash", ""), password):
            session["user_id"] = user.get("DoctorID") if actual_role == "doctor" else user.get("PatientID")
            session["user_name"] = user.get("FullName")
            session["role"] = actual_role
            session["email"] = user.get("Email")

            CloudWatchAuditLogger.log_event(
                "USER_LOGIN_SUCCESS",
                session["user_id"],
                actual_role,
                {"email": email, "ip": request.remote_addr}
            )

            # Check for redirect to booking flow
            doctor_id = request.args.get("doctor_id") or request.form.get("doctor_id")
            next_url = request.args.get("next")
            if actual_role == "patient" and doctor_id:
                flash(f"Welcome back, {user.get('FullName')}! Please select your appointment slot.", "success")
                return redirect(url_for("patient_dashboard", doctor_id=doctor_id, book="1"))
            if next_url:
                flash(f"Welcome back, {user.get('FullName')}!", "success")
                return redirect(next_url)

            flash(f"Welcome back, {user.get('FullName')}!", "success")
            if actual_role == "doctor":
                return redirect(url_for("doctor_dashboard"))
            return redirect(url_for("patient_dashboard"))
        else:
            CloudWatchAuditLogger.log_event(
                "USER_LOGIN_FAILED",
                email,
                role,
                {"ip": request.remote_addr, "reason": "Invalid credentials"}
            )
            flash("Invalid email or password. Please verify your credentials and try again.", "danger")

    # Pass doctor list for demo login autofill
    doctors = DatabaseService.list_doctors()
    return render_template("login.html", doctors=doctors)

@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        if session.get("role") == "doctor":
            return redirect(url_for("doctor_dashboard"))
        return redirect(url_for("patient_dashboard"))

    if request.method == "POST":
        role = request.form.get("role", "patient").strip().lower()

        if role == "doctor":
            full_name = request.form.get("full_name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            phone = request.form.get("phone", "").strip()
            specialty = request.form.get("specialty", "").strip()
            qualifications = request.form.get("qualifications", "").strip()
            reg_no = request.form.get("reg_no", "").strip()
            city = request.form.get("city", "Pune").strip()
            area = request.form.get("area", "").strip()
            hospital = request.form.get("hospital", "").strip()
            fee_inr = request.form.get("fee_inr", "700").strip()
            experience = request.form.get("experience", "5").strip()
            room = request.form.get("room", "OPD Suite 101").strip()

            if not full_name or not email or not password or not specialty:
                flash("Please fill in all required doctor registration fields.", "warning")
                return render_template("register.html")

            existing = DatabaseService.get_doctor_by_email(email)
            if existing:
                flash("A clinician account with this email already exists. Please sign in.", "warning")
                return redirect(url_for("login", role="doctor"))

            try:
                fee_val = int(fee_inr)
            except ValueError:
                fee_val = 700

            try:
                exp_val = int(experience)
            except ValueError:
                exp_val = 5

            doctor_data = {
                "FullName": full_name if full_name.startswith("Dr.") else f"Dr. {full_name}",
                "Email": email,
                "Password": password,
                "Phone": phone or "+91 98220 00000",
                "Specialty": specialty,
                "Department": specialty,
                "Qualifications": qualifications or "MBBS, MD",
                "RegNo": reg_no or "MMC-REG-PENDING",
                "City": city or "Pune",
                "Area": area or "Pune City",
                "Hospital": hospital or "MedTrack Clinical Network, Pune",
                "FeeINR": fee_val,
                "ExperienceYears": exp_val,
                "Room": room,
                "Rating": 5.0,
                "AvailableSlots": ["09:30 AM", "11:30 AM", "02:30 PM", "05:00 PM"]
            }

            created = DatabaseService.register_doctor(doctor_data)
            CloudWatchAuditLogger.log_event(
                "DOCTOR_REGISTRATION",
                created["DoctorID"],
                "doctor",
                {"email": email, "name": full_name, "reg_no": reg_no}
            )

            # Log doctor in immediately
            session["user_id"] = created["DoctorID"]
            session["user_name"] = created["FullName"]
            session["role"] = "doctor"
            session["email"] = created["Email"]

            flash(f"Welcome {created['FullName']}! Your clinical practice profile ({created['DoctorID']}) is now active.", "success")
            return redirect(url_for("doctor_dashboard"))

        else:
            # Patient registration flow
            full_name = request.form.get("full_name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            dob = request.form.get("dob", "")
            gender = request.form.get("gender", "")
            blood_group = request.form.get("blood_group", "")
            phone = request.form.get("phone", "")
            emergency_contact = request.form.get("emergency_contact", "")
            allergies = request.form.get("allergies", "None reported")
            chronic = request.form.get("chronic_conditions", "None reported")

            if not full_name or not email or not password:
                flash("Please fill in all required fields.", "warning")
                return render_template("register.html")

            # Check existing patient
            existing = DatabaseService.get_patient_by_email(email)
            if existing:
                flash("An account with this email already exists. Please log in.", "warning")
                return redirect(url_for("login"))

            patient_data = {
                "FullName": full_name,
                "Email": email,
                "Password": password,
                "DateOfBirth": dob,
                "Gender": gender,
                "BloodGroup": blood_group,
                "Phone": phone,
                "EmergencyContact": emergency_contact,
                "Allergies": allergies,
                "ChronicConditions": chronic
            }

            created = DatabaseService.register_patient(patient_data)
            CloudWatchAuditLogger.log_event(
                "PATIENT_REGISTRATION",
                created["PatientID"],
                "patient",
                {"email": email, "name": full_name}
            )

            # Automatically log the newly registered patient in
            session["user_id"] = created["PatientID"]
            session["user_name"] = created["FullName"]
            session["role"] = "patient"
            session["email"] = created["Email"]

            flash(f"Registration successful! Welcome {created['FullName']}. Your Patient ID is {created['PatientID']}.", "success")
            return redirect(url_for("patient_dashboard"))

    return render_template("register.html")

@app.route("/logout")
def logout():
    uid = session.get("user_id", "ANONYMOUS")
    role = session.get("role", "UNKNOWN")
    CloudWatchAuditLogger.log_event("USER_LOGOUT", uid, role, {})
    session.clear()
    flash("You have been securely logged out.", "info")
    return redirect(url_for("index"))

# --------------------------------------------------------
# PATIENT PORTAL ROUTES
# --------------------------------------------------------
@app.route("/patient/dashboard")
@login_required
@role_required("patient")
def patient_dashboard():
    patient_id = session.get("user_id")
    patient = DatabaseService.get_patient_by_id(patient_id)
    appointments = DatabaseService.get_appointments_for_patient(patient_id)
    diagnoses = DatabaseService.get_diagnoses_for_patient(patient_id)
    doctors = DatabaseService.list_doctors()
    vitals = DatabaseService.get_patient_vitals(patient_id)

    return render_template(
        "patient_dashboard.html",
        patient=patient,
        appointments=appointments,
        diagnoses=diagnoses,
        doctors=doctors,
        vitals=vitals,
        preselected_doctor_id=request.args.get("doctor_id", ""),
        auto_book=request.args.get("book", "")
    )

@app.route("/patient/book-appointment", methods=["POST"])
@login_required
@role_required("patient")
def book_appointment():
    patient_id = session.get("user_id")
    patient = DatabaseService.get_patient_by_id(patient_id)
    doctor_id = request.form.get("doctor_id")
    date = request.form.get("date")
    time_slot = request.form.get("time_slot")
    reason = request.form.get("reason", "General Consultation").strip()

    doctor = DatabaseService.get_doctor_by_id(doctor_id)
    if not doctor or not date or not time_slot:
        flash("Invalid booking details. Please select a doctor, date, and slot.", "danger")
        return redirect(url_for("patient_dashboard"))

    # Initial status is Pending Approval for doctor review
    appointment_data = {
        "PatientID": patient_id,
        "PatientName": patient.get("FullName", session.get("user_name")),
        "PatientEmail": patient.get("Email"),
        "PatientPhone": patient.get("Phone"),
        "DoctorID": doctor_id,
        "DoctorName": doctor.get("FullName"),
        "Department": doctor.get("Department", doctor.get("Specialty")),
        "Date": date,
        "Time": time_slot,
        "Reason": reason,
        "Status": "Pending Approval",
        "Notes": "New application submitted by patient."
    }

    created = DatabaseService.create_appointment(appointment_data)

    # Trigger AWS SNS / Simulated Notification
    notif_id = NotificationService.send_appointment_notification(created)

    # CloudWatch audit
    CloudWatchAuditLogger.log_event(
        "APPOINTMENT_BOOKED",
        patient_id,
        "patient",
        {
            "appointment_id": created["AppointmentID"],
            "doctor_id": doctor_id,
            "date": date,
            "notification_id": notif_id
        }
    )

    flash(f"Appointment booked successfully with {doctor.get('FullName')}! Your consultation application is pending physician review.", "success")
    return redirect(url_for("patient_dashboard"))

@app.route("/patient/appointment/cancel", methods=["POST"])
@login_required
@role_required("patient")
def cancel_appointment():
    patient_id = session.get("user_id")
    appointment_id = request.form.get("appointment_id")
    appt = DatabaseService.get_appointment(appointment_id)
    if appt and appt.get("PatientID") == patient_id:
        DatabaseService.update_appointment_status(appointment_id, "Cancelled", "Cancelled by patient.")
        CloudWatchAuditLogger.log_event("APPOINTMENT_CANCELLED", patient_id, "patient", {"appointment_id": appointment_id})
        flash("Your appointment application has been cancelled.", "info")
    else:
        flash("Could not cancel appointment.", "danger")
    return redirect(url_for("patient_dashboard"))

@app.route("/patient/vitals", methods=["POST"])
@login_required
@role_required("patient")
def save_vitals():
    patient_id = session.get("user_id")
    try:
        data = {
            "systolic": request.form.get("systolic", 120),
            "diastolic": request.form.get("diastolic", 80),
            "heart_rate": request.form.get("heart_rate", 72),
            "blood_glucose": request.form.get("blood_glucose", 95),
            "oxygen_spo2": request.form.get("oxygen_spo2", 98),
            "weight_kg": request.form.get("weight_kg", 70),
            "notes": request.form.get("notes", "Self-recorded vitals")
        }
        DatabaseService.save_patient_vitals(patient_id, data)
        flash("Daily health vitals recorded successfully!", "success")
    except Exception as e:
        flash(f"Error logging vitals: {e}", "danger")
    return redirect(url_for("patient_dashboard"))

@app.route("/api/patient/vitals")
@login_required
def api_patient_vitals():
    pid = session.get("user_id")
    vitals = DatabaseService.get_patient_vitals(pid)
    return jsonify({"success": True, "vitals": vitals})

@app.route("/prescription/<diagnosis_id>")
@login_required
def view_prescription(diagnosis_id):
    dx = DatabaseService.get_diagnosis_by_id(diagnosis_id)
    if not dx:
        flash("Prescription record not found.", "warning")
        return redirect(url_for("index"))

    uid = session.get("user_id")
    role = session.get("role")
    if role == "patient" and dx.get("PatientID") != uid:
        flash("Unauthorized access to medical record.", "danger")
        return redirect(url_for("patient_dashboard"))

    patient = DatabaseService.get_patient_by_id(dx.get("PatientID"))
    doctor = DatabaseService.get_doctor_by_id(dx.get("DoctorID"))
    return render_template("prescription.html", dx=dx, patient=patient, doctor=doctor)

# --------------------------------------------------------
# DOCTOR PORTAL ROUTES
# --------------------------------------------------------
@app.route("/doctor/dashboard")
@login_required
@role_required("doctor")
def doctor_dashboard():
    doctor_id = session.get("user_id")
    doctor = DatabaseService.get_doctor_by_id(doctor_id)
    appointments = DatabaseService.get_appointments_for_doctor(doctor_id)
    diagnoses = DatabaseService.get_diagnoses_for_doctor(doctor_id)
    patients = DatabaseService.list_patients()

    # Pre-categorize appointments for clean tab management
    pending_appts = [a for a in appointments if a.get("Status") in ["Pending Approval", "Requested"]]
    confirmed_appts = [a for a in appointments if a.get("Status") in ["Confirmed", "Scheduled", "In Consultation"]]
    completed_appts = [a for a in appointments if a.get("Status") == "Completed"]

    return render_template(
        "doctor_dashboard.html",
        doctor=doctor,
        appointments=appointments,
        pending_appts=pending_appts,
        confirmed_appts=confirmed_appts,
        completed_appts=completed_appts,
        diagnoses=diagnoses,
        patients=patients
    )

@app.route("/doctor/appointment/accept", methods=["POST"])
@login_required
@role_required("doctor")
def doctor_accept_appointment():
    doctor_id = session.get("user_id")
    appointment_id = request.form.get("appointment_id")
    appt = DatabaseService.get_appointment(appointment_id)
    if not appt:
        flash("Appointment request not found.", "danger")
        return redirect(url_for("doctor_dashboard"))

    DatabaseService.update_appointment_status(appointment_id, "Confirmed", "Application accepted by physician.")
    appt["Status"] = "Confirmed"
    NotificationService.send_appointment_accepted_notification(appt)
    CloudWatchAuditLogger.log_event("APPOINTMENT_ACCEPTED", doctor_id, "doctor", {"appointment_id": appointment_id})
    flash(f"Application from {appt.get('PatientName')} accepted! Appointment confirmed for {appt.get('Date')} at {appt.get('Time')}.", "success")
    return redirect(url_for("doctor_dashboard"))

@app.route("/doctor/appointment/decline", methods=["POST"])
@login_required
@role_required("doctor")
def doctor_decline_appointment():
    doctor_id = session.get("user_id")
    appointment_id = request.form.get("appointment_id")
    reason = request.form.get("reason", "Physician schedule conflict / slot unavailable").strip()
    appt = DatabaseService.get_appointment(appointment_id)
    if not appt:
        flash("Appointment not found.", "danger")
        return redirect(url_for("doctor_dashboard"))

    DatabaseService.update_appointment_status(appointment_id, "Declined", reason)
    appt["Status"] = "Declined"
    NotificationService.send_appointment_declined_notification(appt, reason)
    CloudWatchAuditLogger.log_event("APPOINTMENT_DECLINED", doctor_id, "doctor", {"appointment_id": appointment_id, "reason": reason})
    flash(f"Application from {appt.get('PatientName')} declined. Patient notified.", "info")
    return redirect(url_for("doctor_dashboard"))

@app.route("/doctor/appointment/start", methods=["POST"])
@login_required
@role_required("doctor")
def doctor_start_consultation():
    doctor_id = session.get("user_id")
    appointment_id = request.form.get("appointment_id")
    appt = DatabaseService.get_appointment(appointment_id)
    if appt:
        DatabaseService.update_appointment_status(appointment_id, "In Consultation", "Consultation in active progress.")
        CloudWatchAuditLogger.log_event("CONSULTATION_STARTED", doctor_id, "doctor", {"appointment_id": appointment_id})
        flash(f"Consultation session with {appt.get('PatientName')} is now active.", "info")
    return redirect(url_for("doctor_dashboard"))

@app.route("/doctor/appointment/update", methods=["POST"])
@login_required
@role_required("doctor")
def update_appointment():
    doctor_id = session.get("user_id")
    appointment_id = request.form.get("appointment_id")
    new_status = request.form.get("status")
    notes = request.form.get("notes", "").strip()

    if not appointment_id or not new_status:
        flash("Invalid request parameters.", "danger")
        return redirect(url_for("doctor_dashboard"))

    success = DatabaseService.update_appointment_status(appointment_id, new_status, notes)
    if success:
        CloudWatchAuditLogger.log_event(
            "APPOINTMENT_STATUS_UPDATED",
            doctor_id,
            "doctor",
            {"appointment_id": appointment_id, "new_status": new_status}
        )
        flash(f"Appointment {appointment_id} marked as {new_status}.", "success")
    else:
        flash("Could not update appointment.", "danger")

    return redirect(url_for("doctor_dashboard"))

@app.route("/doctor/diagnose", methods=["POST"])
@login_required
@role_required("doctor")
def submit_diagnosis():
    doctor_id = session.get("user_id")
    doctor = DatabaseService.get_doctor_by_id(doctor_id)

    patient_id = request.form.get("patient_id")
    appointment_id = request.form.get("appointment_id", "")
    condition = request.form.get("condition", "").strip()
    symptoms = request.form.get("symptoms", "").strip()
    summary = request.form.get("summary", "").strip()
    prescription = request.form.get("prescription", "").strip()

    patient = DatabaseService.get_patient_by_id(patient_id)
    if not patient or not condition or not summary:
        flash("Please provide patient, diagnosed condition, and clinical summary.", "warning")
        return redirect(url_for("doctor_dashboard"))

    # File report upload handling (AWS S3 or Local)
    report_file = request.files.get("report_file")
    file_key = ""
    file_url = ""
    filename = ""

    if report_file and report_file.filename:
        if allowed_file(report_file.filename):
            filename = report_file.filename
            file_key, file_url = StorageService.save_file(report_file, folder="reports")
        else:
            flash("Invalid file format. Allowed: PDF, JPG, PNG, DOCX, TXT.", "danger")
            return redirect(url_for("doctor_dashboard"))

    diagnosis_data = {
        "PatientID": patient_id,
        "PatientName": patient.get("FullName"),
        "DoctorID": doctor_id,
        "DoctorName": doctor.get("FullName", session.get("user_name")),
        "AppointmentID": appointment_id,
        "Condition": condition,
        "Symptoms": symptoms,
        "Summary": summary,
        "Prescription": prescription,
        "ReportFileName": filename,
        "ReportFileKey": file_key,
        "ReportUrl": file_url
    }

    created = DatabaseService.create_diagnosis(diagnosis_data)

    # If linked to an appointment, automatically mark it as Completed
    if appointment_id:
        DatabaseService.update_appointment_status(appointment_id, "Completed", f"Diagnosis recorded: {condition}")

    # Send Notification via SNS
    recipient_email = patient.get("Email", "patient@medtrack.org")
    notif_id = NotificationService.send_diagnosis_notification(created, patient.get("FullName"), recipient_email)

    # CloudWatch event
    CloudWatchAuditLogger.log_event(
        "DIAGNOSIS_SUBMITTED",
        doctor_id,
        "doctor",
        {
            "diagnosis_id": created["DiagnosisID"],
            "patient_id": patient_id,
            "has_file": bool(file_key),
            "notification_id": notif_id
        }
    )

    flash(f"Clinical diagnosis & prescription saved successfully! Patient notified via SNS.", "success")
    return redirect(url_for("doctor_dashboard"))

# --------------------------------------------------------
# STATIC MEDIA & UPLOAD SERVING
# --------------------------------------------------------
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    """Serves locally stored reports when not using S3."""
    return send_from_directory(Config.UPLOAD_FOLDER, filename)

# --------------------------------------------------------
# API ENDPOINTS (FOR DYNAMIC UI UPDATES)
# --------------------------------------------------------
@app.route("/api/notifications")
def api_notifications():
    items = NotificationService.get_recent_notifications(limit=10)
    return jsonify({"success": True, "notifications": items})

@app.route("/api/system-status")
def api_system_status():
    return jsonify({
        "status": "HEALTHY",
        "cloud_mode": "AWS LIVE" if Config.USE_AWS else "LOCAL MOCK (AWS-READY)",
        "region": Config.AWS_REGION,
        "dynamodb": "CONNECTED" if Config.USE_AWS else "SIMULATED_JSON_ENGINE",
        "sns": "ACTIVE" if Config.USE_AWS else "LOCAL_EMITTER",
        "s3": Config.S3_BUCKET_NAME if Config.USE_AWS else "LOCAL_UPLOADS_DIR",
        "doctor_count": len(DatabaseService.list_doctors()),
        "patient_count": len(DatabaseService.list_patients())
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
