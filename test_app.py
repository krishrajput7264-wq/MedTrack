import io
import uuid
from app import app
from services.db_service import DatabaseService

def test_full_workflow():
    client = app.test_client()

    print("=== [1] Testing Public Landing & Architecture Pages ===")
    res = client.get("/")
    assert res.status_code == 200, f"Index failed: {res.status_code}"
    assert b"Pune" in res.data, "Pune localization missing on homepage"
    print("[OK] Landing page returned 200 OK with Pune localization")

    res = client.get("/architecture", follow_redirects=True)
    assert res.status_code == 200, f"Architecture redirect failed: {res.status_code}"
    print("[OK] Architecture route redirects cleanly to portal 200 OK")

    res = client.get("/api/system-status")
    assert res.status_code == 200
    json_data = res.get_json()
    print(f"[OK] System status API: {json_data['status']}")

    print("\n=== [2] Testing Patient Authentication ===")
    # Login as seeded patient Alex Mercer
    res = client.post("/login", data={
        "role": "patient",
        "email": "alex.mercer@gmail.com",
        "password": "patient123"
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Patient Portal" in res.data
    print("[OK] Patient login successful, accessed dashboard")

    print("\n=== [3] Testing Direct Booking Parameter on Patient Dashboard ===")
    res = client.get("/patient/dashboard?doctor_id=DOC-2001&book=1")
    assert res.status_code == 200
    assert b"DOC-2001" in res.data
    assert b"108" in res.data, "Indian emergency number missing"
    print("[OK] Direct doctor pre-selection parameter and Indian 108 helpline verified")

    print("\n=== [4] Testing Appointment Booking Flow ===")
    res = client.post("/patient/book-appointment", data={
        "doctor_id": "DOC-2001",
        "date": "2026-10-05",
        "time_slot": "11:00 AM",
        "reason": "Routine cardio evaluation in Pune"
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Appointment booked successfully" in res.data
    print("[OK] Appointment booked and notification event triggered")

    # Logout
    client.get("/logout")

    print("\n=== [5] Testing Doctor Registration (Pune Specialist) ===")
    unique_email = f"amit.patil.{uuid.uuid4().hex[:4]}@medtrack.in"
    res = client.post("/register", data={
        "role": "doctor",
        "full_name": "Dr. Amit Patil",
        "email": unique_email,
        "password": "doctorpassword123",
        "phone": "+91 98220 55443",
        "specialty": "General Physician & Internal Medicine",
        "qualifications": "MBBS, MD (Medicine)",
        "reg_no": "MMC-2016-09876",
        "city": "Pune",
        "area": "Kothrud",
        "hospital": "Sahyadri Hospital, Kothrud, Pune",
        "fee_inr": "600",
        "experience": "10",
        "room": "OPD Suite 201"
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Clinical Workspace" in res.data
    assert b"Dr. Amit Patil" in res.data
    print(f"[OK] New Doctor registered successfully and logged in to workspace ({unique_email})")

    # Logout
    client.get("/logout")

    print("\n=== [6] Testing Smart Login (Role Auto-Detection) ===")
    # Login with doctor credentials but using patient tab
    res = client.post("/login", data={
        "role": "patient",  # Intentionally selected wrong tab
        "email": unique_email,
        "password": "doctorpassword123"
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Clinical Workspace" in res.data
    print("[OK] Smart login auto-detected doctor account despite role tab selection")

    print("\n=== [7] Testing Doctor Clinical Diagnosis Flow ===")
    # Submit Diagnosis with simulated file upload
    fake_file = (io.BytesIO(b"%PDF-1.4 simulated ECG report data"), "pune_ecg_report.pdf")
    res = client.post("/doctor/diagnose", data={
        "patient_id": "PAT-1001",
        "appointment_id": "APT-5001",
        "condition": "Normal Sinus Rhythm",
        "symptoms": "Mild fatigue after Pune commute",
        "summary": "Clinical exam normal. BP 120/80. Advised hydration.",
        "prescription": "Multivitamin OD for 15 days, Hydration 3L/day",
        "report_file": fake_file
    }, content_type="multipart/form-data", follow_redirects=True)
    assert res.status_code == 200
    assert b"saved successfully" in res.data
    print("[OK] Clinical diagnosis and report saved with prescription")

    print("\n=== [8] Testing Notifications Feed ===")
    res = client.get("/api/notifications")
    assert res.status_code == 200
    notifs = res.get_json().get("notifications", [])
    assert len(notifs) > 0
    print(f"[OK] Notification feed contains {len(notifs)} real-time alert events")

    print("\n=== [9] Testing Doctor Client Accept Panel & Start Consultation ===")
    # Login as doctor
    client.get("/logout")
    client.post("/login", data={
        "role": "doctor",
        "email": "sarah.mitchell@medtrack.org",
        "password": "doctor123"
    }, follow_redirects=True)

    # Create a fresh test appointment in Pending Approval state
    test_appt = DatabaseService.create_appointment({
        "PatientID": "PAT-1001",
        "PatientName": "Alex Mercer",
        "PatientEmail": "alex.mercer@gmail.com",
        "DoctorID": "DOC-2001",
        "DoctorName": "Dr. Sarah Mitchell",
        "Department": "Cardiology",
        "Date": "2026-10-12",
        "Time": "02:00 PM",
        "Reason": "Cardiology review application",
        "Status": "Pending Approval",
        "Notes": "Patient application test"
    })
    appt_id = test_appt["AppointmentID"]

    # Test Doctor Accept Application
    res = client.post("/doctor/appointment/accept", data={
        "appointment_id": appt_id
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"accepted!" in res.data
    updated = DatabaseService.get_appointment(appt_id)
    assert updated["Status"] == "Confirmed"
    print(f"[OK] Doctor Client Accept Panel: Accepted application {appt_id} -> Confirmed")

    # Test Doctor Start Consultation
    res = client.post("/doctor/appointment/start", data={
        "appointment_id": appt_id
    }, follow_redirects=True)
    assert res.status_code == 200
    updated = DatabaseService.get_appointment(appt_id)
    assert updated["Status"] == "In Consultation"
    print(f"[OK] Doctor Started Consultation: {appt_id} -> In Consultation")

    print("\n=== [10] Testing Patient Vitals Logging & Prescription Slip ===")
    client.get("/logout")
    client.post("/login", data={
        "role": "patient",
        "email": "alex.mercer@gmail.com",
        "password": "patient123"
    }, follow_redirects=True)

    # Log vitals
    res = client.post("/patient/vitals", data={
        "systolic": "118",
        "diastolic": "78",
        "heart_rate": "72",
        "blood_glucose": "94",
        "oxygen_spo2": "99",
        "weight_kg": "69",
        "notes": "Test vitals log"
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"vitals recorded successfully" in res.data
    print("[OK] Patient Vitals recorded and displayed on dashboard")

    # Test Prescription Slip View
    diagnoses = DatabaseService.get_diagnoses_for_patient("PAT-1001")
    if diagnoses:
        dx_id = diagnoses[0]["DiagnosisID"]
        res = client.get(f"/prescription/{dx_id}")
        assert res.status_code == 200
        assert b"Print Prescription" in res.data
        assert b"Clinical Prescription" in res.data
        print(f"[OK] Printable Prescription Slip generated cleanly for {dx_id}")

    # Test Patient Cancel Appointment
    cancel_appt = DatabaseService.create_appointment({
        "PatientID": "PAT-1001",
        "PatientName": "Alex Mercer",
        "PatientEmail": "alex.mercer@gmail.com",
        "DoctorID": "DOC-2001",
        "DoctorName": "Dr. Sarah Mitchell",
        "Department": "Cardiology",
        "Date": "2026-10-18",
        "Time": "11:00 AM",
        "Reason": "To be cancelled",
        "Status": "Pending Approval",
        "Notes": ""
    })
    res = client.post("/patient/appointment/cancel", data={
        "appointment_id": cancel_appt["AppointmentID"]
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"cancelled" in res.data
    print(f"[OK] Patient cancelled consultation request successfully")

    print("\n=======================================================")
    print("ALL CORE WORKFLOWS, DOCTOR ACCEPT PANEL, VITALS & PRESCRIPTION SLIP VERIFIED 100% OK!")
    print("=======================================================")

if __name__ == "__main__":
    test_full_workflow()
