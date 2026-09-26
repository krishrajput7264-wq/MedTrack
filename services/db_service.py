import os
import json
import uuid
import datetime
import logging
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from services.aws_client import get_dynamodb_resource
from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger("medtrack.db")

class DatabaseService:
    """
    Unified Database abstraction layer.
    If Config.USE_AWS is True, queries AWS DynamoDB.
    Otherwise, reads and writes to local JSON stores in Config.DATA_DIR.
    """

    @classmethod
    def _init_local_db(cls):
        """Pre-seeds realistic data if local data files are missing."""
        os.makedirs(Config.DATA_DIR, exist_ok=True)
        
        doctors_file = os.path.join(Config.DATA_DIR, "doctors.json")
        patients_file = os.path.join(Config.DATA_DIR, "patients.json")
        appointments_file = os.path.join(Config.DATA_DIR, "appointments.json")
        diagnoses_file = os.path.join(Config.DATA_DIR, "diagnoses.json")

        if not os.path.exists(doctors_file):
            default_doctors = [
                {
                    "DoctorID": "DOC-2001",
                    "FullName": "Dr. Sarah Mitchell",
                    "Email": "sarah.mitchell@medtrack.org",
                    "PasswordHash": generate_password_hash("doctor123"),
                    "Specialty": "Cardiology",
                    "Department": "Cardiovascular Medicine",
                    "Qualifications": "MD, FACC, Harvard Medical School",
                    "ExperienceYears": 14,
                    "AvailableSlots": ["09:00 AM", "10:30 AM", "02:00 PM", "04:30 PM"],
                    "Rating": 4.9,
                    "Room": "Clinic Wing A, Suite 302"
                },
                {
                    "DoctorID": "DOC-2002",
                    "FullName": "Dr. Marcus Vance",
                    "Email": "marcus.vance@medtrack.org",
                    "PasswordHash": generate_password_hash("doctor123"),
                    "Specialty": "Neurology",
                    "Department": "Neurological Sciences",
                    "Qualifications": "MD, PhD, Johns Hopkins University",
                    "ExperienceYears": 11,
                    "AvailableSlots": ["10:00 AM", "11:30 AM", "01:30 PM", "03:45 PM"],
                    "Rating": 4.8,
                    "Room": "Neurology Pavilion, Suite 105"
                },
                {
                    "DoctorID": "DOC-2003",
                    "FullName": "Dr. Emily Chen",
                    "Email": "emily.chen@medtrack.org",
                    "PasswordHash": generate_password_hash("doctor123"),
                    "Specialty": "Pediatrics & Family Medicine",
                    "Department": "Pediatrics",
                    "Qualifications": "MD, Stanford University",
                    "ExperienceYears": 9,
                    "AvailableSlots": ["08:30 AM", "11:00 AM", "02:30 PM", "05:00 PM"],
                    "Rating": 4.95,
                    "Room": "Family Health Center, Suite 210"
                },
                {
                    "DoctorID": "DOC-2004",
                    "FullName": "Dr. Rajesh Kothari",
                    "Email": "rajesh.kothari@medtrack.org",
                    "PasswordHash": generate_password_hash("doctor123"),
                    "Specialty": "Orthopedics & Sports Medicine",
                    "Department": "Orthopedic Surgery",
                    "Qualifications": "MS, MCh Ortho, AIIMS",
                    "ExperienceYears": 16,
                    "AvailableSlots": ["09:30 AM", "12:00 PM", "03:00 PM"],
                    "Rating": 4.85,
                    "Room": "Surgical Tower, Suite 401"
                }
            ]
            cls._write_json(doctors_file, default_doctors)

        if not os.path.exists(patients_file):
            default_patients = [
                {
                    "PatientID": "PAT-1001",
                    "FullName": "Alex Mercer",
                    "Email": "alex.mercer@gmail.com",
                    "PasswordHash": generate_password_hash("patient123"),
                    "DateOfBirth": "1992-05-14",
                    "Gender": "Male",
                    "BloodGroup": "O+",
                    "Phone": "+1 (555) 234-8901",
                    "EmergencyContact": "Elena Mercer (+1 555-908-1123)",
                    "Allergies": "Penicillin, Sulfa drugs",
                    "ChronicConditions": "Mild Hypertension",
                    "CreatedAt": "2026-01-10T10:00:00Z"
                }
            ]
            cls._write_json(patients_file, default_patients)

        if not os.path.exists(appointments_file):
            default_appointments = [
                {
                    "AppointmentID": "APT-5001",
                    "PatientID": "PAT-1001",
                    "PatientName": "Alex Mercer",
                    "DoctorID": "DOC-2001",
                    "DoctorName": "Dr. Sarah Mitchell",
                    "Department": "Cardiovascular Medicine",
                    "Date": "2026-09-24",
                    "Time": "10:30 AM",
                    "Reason": "Follow-up blood pressure check & ECG review",
                    "Status": "Scheduled",
                    "Notes": "Patient reported slight dizziness during morning workouts.",
                    "CreatedAt": "2026-09-20T14:30:00Z"
                },
                {
                    "AppointmentID": "APT-5000",
                    "PatientID": "PAT-1001",
                    "PatientName": "Alex Mercer",
                    "DoctorID": "DOC-2001",
                    "DoctorName": "Dr. Sarah Mitchell",
                    "Department": "Cardiovascular Medicine",
                    "Date": "2026-08-15",
                    "Time": "09:00 AM",
                    "Reason": "Initial Cardiovascular Consultation",
                    "Status": "Completed",
                    "Notes": "Routine cardiovascular assessment completed.",
                    "CreatedAt": "2026-08-10T09:15:00Z"
                }
            ]
            cls._write_json(appointments_file, default_appointments)

        if not os.path.exists(diagnoses_file):
            default_diagnoses = [
                {
                    "DiagnosisID": "DX-7001",
                    "AppointmentID": "APT-5000",
                    "PatientID": "PAT-1001",
                    "DoctorID": "DOC-2001",
                    "DoctorName": "Dr. Sarah Mitchell",
                    "Condition": "Stage 1 Essential Hypertension",
                    "Symptoms": "Elevated systolic pressure, occasional tension headaches",
                    "Summary": "Resting BP observed at 134/88. Cardiac auscultation normal. Advised lifestyle modifications and light cardio exercise.",
                    "Prescription": "Amlodipine 5mg OD (morning), Low sodium diet (<2000mg/day), Hydration 2.5L/day",
                    "ReportFileName": "ECG_Assessment_Aug2026.pdf",
                    "ReportFileKey": "",
                    "ReportUrl": "",
                    "Date": "2026-08-15",
                    "CreatedAt": "2026-08-15T11:00:00Z"
                }
            ]
            cls._write_json(diagnoses_file, default_diagnoses)

    @staticmethod
    def _read_json(filepath):
        if not os.path.exists(filepath):
            return []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    @staticmethod
    def _write_json(filepath, data):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    # ----------------------------------------------------
    # PATIENT METHODS
    # ----------------------------------------------------
    @classmethod
    def register_patient(cls, data: dict):
        cls._init_local_db()
        patient_id = f"PAT-{uuid.uuid4().hex[:6].upper()}"
        data["PatientID"] = patient_id
        data["CreatedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if "Password" in data:
            data["PasswordHash"] = generate_password_hash(data.pop("Password"))

        if Config.USE_AWS:
            try:
                db = get_dynamodb_resource()
                table = db.Table(Config.DYNAMODB_PATIENTS_TABLE)
                table.put_item(Item=data)
                return data
            except Exception as e:
                logger.error(f"DynamoDB PutItem Patient error: {e}")

        # Local mode
        filepath = os.path.join(Config.DATA_DIR, "patients.json")
        patients = cls._read_json(filepath)
        patients.append(data)
        cls._write_json(filepath, patients)
        return data

    @classmethod
    def get_patient_by_email(cls, email: str):
        cls._init_local_db()
        email = email.strip().lower()
        if Config.USE_AWS:
            try:
                db = get_dynamodb_resource()
                table = db.Table(Config.DYNAMODB_PATIENTS_TABLE)
                response = table.scan(FilterExpression=Attr("Email").eq(email))
                items = response.get("Items", [])
                return items[0] if items else None
            except Exception as e:
                logger.error(f"DynamoDB scan error: {e}")

        patients = cls._read_json(os.path.join(Config.DATA_DIR, "patients.json"))
        for p in patients:
            if p.get("Email", "").strip().lower() == email:
                return p
        return None

    @classmethod
    def get_patient_by_id(cls, patient_id: str):
        cls._init_local_db()
        if Config.USE_AWS:
            try:
                db = get_dynamodb_resource()
                table = db.Table(Config.DYNAMODB_PATIENTS_TABLE)
                response = table.get_item(Key={"PatientID": patient_id})
                return response.get("Item")
            except Exception as e:
                logger.error(f"DynamoDB GetItem error: {e}")

        patients = cls._read_json(os.path.join(Config.DATA_DIR, "patients.json"))
        for p in patients:
            if p.get("PatientID") == patient_id:
                return p
        return None

    @classmethod
    def list_patients(cls):
        cls._init_local_db()
        if Config.USE_AWS:
            try:
                db = get_dynamodb_resource()
                table = db.Table(Config.DYNAMODB_PATIENTS_TABLE)
                return table.scan().get("Items", [])
            except Exception as e:
                logger.error(f"DynamoDB list_patients error: {e}")
        return cls._read_json(os.path.join(Config.DATA_DIR, "patients.json"))

    # ----------------------------------------------------
    # DOCTOR METHODS
    # ----------------------------------------------------
    @classmethod
    def get_doctor_by_email(cls, email: str):
        cls._init_local_db()
        email = email.strip().lower()
        if Config.USE_AWS:
            try:
                db = get_dynamodb_resource()
                table = db.Table(Config.DYNAMODB_DOCTORS_TABLE)
                response = table.scan(FilterExpression=Attr("Email").eq(email))
                items = response.get("Items", [])
                return items[0] if items else None
            except Exception as e:
                logger.error(f"DynamoDB doctor scan error: {e}")

        doctors = cls._read_json(os.path.join(Config.DATA_DIR, "doctors.json"))
        for d in doctors:
            if d.get("Email", "").strip().lower() == email:
                return d
        return None

    @classmethod
    def get_doctor_by_id(cls, doctor_id: str):
        cls._init_local_db()
        if Config.USE_AWS:
            try:
                db = get_dynamodb_resource()
                table = db.Table(Config.DYNAMODB_DOCTORS_TABLE)
                response = table.get_item(Key={"DoctorID": doctor_id})
                return response.get("Item")
            except Exception as e:
                logger.error(f"DynamoDB doctor GetItem error: {e}")

        doctors = cls._read_json(os.path.join(Config.DATA_DIR, "doctors.json"))
        for d in doctors:
            if d.get("DoctorID") == doctor_id:
                return d
        return None

    @classmethod
    def register_doctor(cls, data: dict):
        cls._init_local_db()
        doctor_id = f"DOC-{uuid.uuid4().hex[:4].upper()}"
        data["DoctorID"] = doctor_id
        data["CreatedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if "Password" in data:
            data["PasswordHash"] = generate_password_hash(data.pop("Password"))
        if "Rating" not in data:
            data["Rating"] = 5.0
        if "AvailableSlots" not in data or not data["AvailableSlots"]:
            data["AvailableSlots"] = ["10:00 AM", "11:30 AM", "02:30 PM", "04:30 PM", "06:00 PM"]
        if "City" not in data:
            data["City"] = "Pune"
        if "Area" not in data:
            data["Area"] = "Deccan, Pune"
        if "FeeINR" not in data:
            data["FeeINR"] = 700

        if Config.USE_AWS:
            try:
                db = get_dynamodb_resource()
                table = db.Table(Config.DYNAMODB_DOCTORS_TABLE)
                table.put_item(Item=data)
                return data
            except Exception as e:
                logger.error(f"DynamoDB PutItem Doctor error: {e}")

        filepath = os.path.join(Config.DATA_DIR, "doctors.json")
        doctors = cls._read_json(filepath)
        doctors.append(data)
        cls._write_json(filepath, doctors)
        return data

    @classmethod
    def list_doctors(cls):
        cls._init_local_db()
        if Config.USE_AWS:
            try:
                db = get_dynamodb_resource()
                table = db.Table(Config.DYNAMODB_DOCTORS_TABLE)
                return table.scan().get("Items", [])
            except Exception as e:
                logger.error(f"DynamoDB list_doctors error: {e}")
        return cls._read_json(os.path.join(Config.DATA_DIR, "doctors.json"))

    # ----------------------------------------------------
    # APPOINTMENT METHODS
    # ----------------------------------------------------
    @classmethod
    def create_appointment(cls, data: dict):
        cls._init_local_db()
        appt_id = f"APT-{uuid.uuid4().hex[:6].upper()}"
        data["AppointmentID"] = appt_id
        data["CreatedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        data["Status"] = data.get("Status", "Scheduled")

        if Config.USE_AWS:
            try:
                db = get_dynamodb_resource()
                table = db.Table(Config.DYNAMODB_APPOINTMENTS_TABLE)
                table.put_item(Item=data)
                return data
            except Exception as e:
                logger.error(f"DynamoDB PutItem Appointment error: {e}")

        filepath = os.path.join(Config.DATA_DIR, "appointments.json")
        appointments = cls._read_json(filepath)
        appointments.insert(0, data)
        cls._write_json(filepath, appointments)
        return data

    @classmethod
    def get_appointment(cls, appointment_id: str):
        cls._init_local_db()
        if Config.USE_AWS:
            try:
                db = get_dynamodb_resource()
                table = db.Table(Config.DYNAMODB_APPOINTMENTS_TABLE)
                return table.get_item(Key={"AppointmentID": appointment_id}).get("Item")
            except Exception as e:
                logger.error(f"DynamoDB appointment error: {e}")

        appointments = cls._read_json(os.path.join(Config.DATA_DIR, "appointments.json"))
        for a in appointments:
            if a.get("AppointmentID") == appointment_id:
                return a
        return None

    @classmethod
    def update_appointment_status(cls, appointment_id: str, status: str, notes: str = None):
        cls._init_local_db()
        if Config.USE_AWS:
            try:
                db = get_dynamodb_resource()
                table = db.Table(Config.DYNAMODB_APPOINTMENTS_TABLE)
                expr = "SET #s = :status"
                names = {"#s": "Status"}
                vals = {":status": status}
                if notes:
                    expr += ", Notes = :notes"
                    vals[":notes"] = notes
                table.update_item(
                    Key={"AppointmentID": appointment_id},
                    UpdateExpression=expr,
                    ExpressionAttributeNames=names,
                    ExpressionAttributeValues=vals
                )
                return True
            except Exception as e:
                logger.error(f"DynamoDB update status error: {e}")

        filepath = os.path.join(Config.DATA_DIR, "appointments.json")
        appointments = cls._read_json(filepath)
        for a in appointments:
            if a.get("AppointmentID") == appointment_id:
                a["Status"] = status
                if notes:
                    a["Notes"] = notes
                cls._write_json(filepath, appointments)
                return True
        return False

    @classmethod
    def get_appointments_for_patient(cls, patient_id: str):
        cls._init_local_db()
        if Config.USE_AWS:
            try:
                db = get_dynamodb_resource()
                table = db.Table(Config.DYNAMODB_APPOINTMENTS_TABLE)
                res = table.scan(FilterExpression=Attr("PatientID").eq(patient_id))
                items = res.get("Items", [])
                items.sort(key=lambda x: x.get("Date", ""), reverse=True)
                return items
            except Exception as e:
                logger.error(f"DynamoDB appointments query error: {e}")

        appointments = cls._read_json(os.path.join(Config.DATA_DIR, "appointments.json"))
        filtered = [a for a in appointments if a.get("PatientID") == patient_id]
        filtered.sort(key=lambda x: x.get("Date", ""), reverse=True)
        return filtered

    @classmethod
    def get_appointments_for_doctor(cls, doctor_id: str):
        cls._init_local_db()
        if Config.USE_AWS:
            try:
                db = get_dynamodb_resource()
                table = db.Table(Config.DYNAMODB_APPOINTMENTS_TABLE)
                res = table.scan(FilterExpression=Attr("DoctorID").eq(doctor_id))
                items = res.get("Items", [])
                items.sort(key=lambda x: x.get("Date", ""), reverse=True)
                return items
            except Exception as e:
                logger.error(f"DynamoDB doctor appointments query error: {e}")

        appointments = cls._read_json(os.path.join(Config.DATA_DIR, "appointments.json"))
        filtered = [a for a in appointments if a.get("DoctorID") == doctor_id]
        filtered.sort(key=lambda x: x.get("Date", ""), reverse=True)
        return filtered

    # ----------------------------------------------------
    # DIAGNOSIS METHODS
    # ----------------------------------------------------
    @classmethod
    def create_diagnosis(cls, data: dict):
        cls._init_local_db()
        diag_id = f"DX-{uuid.uuid4().hex[:6].upper()}"
        data["DiagnosisID"] = diag_id
        data["CreatedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if not data.get("Date"):
            data["Date"] = datetime.date.today().isoformat()

        if Config.USE_AWS:
            try:
                db = get_dynamodb_resource()
                table = db.Table(Config.DYNAMODB_DIAGNOSES_TABLE)
                table.put_item(Item=data)
                return data
            except Exception as e:
                logger.error(f"DynamoDB PutItem Diagnosis error: {e}")

        filepath = os.path.join(Config.DATA_DIR, "diagnoses.json")
        diagnoses = cls._read_json(filepath)
        diagnoses.insert(0, data)
        cls._write_json(filepath, diagnoses)
        return data

    @classmethod
    def get_diagnoses_for_patient(cls, patient_id: str):
        cls._init_local_db()
        if Config.USE_AWS:
            try:
                db = get_dynamodb_resource()
                table = db.Table(Config.DYNAMODB_DIAGNOSES_TABLE)
                res = table.scan(FilterExpression=Attr("PatientID").eq(patient_id))
                items = res.get("Items", [])
                items.sort(key=lambda x: x.get("Date", ""), reverse=True)
                return items
            except Exception as e:
                logger.error(f"DynamoDB diagnoses query error: {e}")

        diagnoses = cls._read_json(os.path.join(Config.DATA_DIR, "diagnoses.json"))
        filtered = [d for d in diagnoses if d.get("PatientID") == patient_id]
        filtered.sort(key=lambda x: x.get("Date", ""), reverse=True)
        return filtered

    @classmethod
    def get_diagnoses_for_doctor(cls, doctor_id: str):
        cls._init_local_db()
        if Config.USE_AWS:
            try:
                db = get_dynamodb_resource()
                table = db.Table(Config.DYNAMODB_DIAGNOSES_TABLE)
                res = table.scan(FilterExpression=Attr("DoctorID").eq(doctor_id))
                items = res.get("Items", [])
                items.sort(key=lambda x: x.get("Date", ""), reverse=True)
                return items
            except Exception as e:
                logger.error(f"DynamoDB doctor diagnoses query error: {e}")

        diagnoses = cls._read_json(os.path.join(Config.DATA_DIR, "diagnoses.json"))
        filtered = [d for d in diagnoses if d.get("DoctorID") == doctor_id]
        filtered.sort(key=lambda x: x.get("Date", ""), reverse=True)
        return filtered

    @classmethod
    def get_diagnosis_by_id(cls, diagnosis_id: str):
        cls._init_local_db()
        if Config.USE_AWS:
            try:
                db = get_dynamodb_resource()
                table = db.Table(Config.DYNAMODB_DIAGNOSES_TABLE)
                return table.get_item(Key={"DiagnosisID": diagnosis_id}).get("Item")
            except Exception as e:
                logger.error(f"DynamoDB get diagnosis error: {e}")

        diagnoses = cls._read_json(os.path.join(Config.DATA_DIR, "diagnoses.json"))
        for d in diagnoses:
            if d.get("DiagnosisID") == diagnosis_id:
                return d
        return None

    @classmethod
    def get_patient_vitals(cls, patient_id: str):
        """Returns vitals records for a patient or sensible clinical defaults."""
        vitals_file = os.path.join(Config.DATA_DIR, "vitals.json")
        default_vitals = [
            {
                "VitalsID": "VIT-101",
                "PatientID": patient_id,
                "Systolic": 120,
                "Diastolic": 80,
                "BloodPressure": "120/80 mmHg",
                "HeartRate": 74,
                "BloodGlucose": 98,
                "OxygenSpO2": 99,
                "WeightKg": 68.5,
                "RecordedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M"),
                "Notes": "Normal baseline resting vitals"
            }
        ]
        if not os.path.exists(vitals_file):
            cls._write_json(vitals_file, default_vitals)
            return default_vitals

        all_vitals = cls._read_json(vitals_file)
        patient_v = [v for v in all_vitals if v.get("PatientID") == patient_id]
        if not patient_v:
            # Seed default for this patient
            patient_v = [{
                "VitalsID": f"VIT-{uuid.uuid4().hex[:6].upper()}",
                "PatientID": patient_id,
                "Systolic": 120,
                "Diastolic": 80,
                "BloodPressure": "120/80 mmHg",
                "HeartRate": 74,
                "BloodGlucose": 98,
                "OxygenSpO2": 99,
                "WeightKg": 68.5,
                "RecordedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M"),
                "Notes": "Normal baseline resting vitals"
            }]
            all_vitals.extend(patient_v)
            cls._write_json(vitals_file, all_vitals)
        patient_v.sort(key=lambda x: x.get("RecordedAt", ""), reverse=True)
        return patient_v

    @classmethod
    def save_patient_vitals(cls, patient_id: str, data: dict):
        """Records new health vitals for a patient."""
        vitals_file = os.path.join(Config.DATA_DIR, "vitals.json")
        all_vitals = cls._read_json(vitals_file) if os.path.exists(vitals_file) else []

        systolic = int(data.get("systolic", 120))
        diastolic = int(data.get("diastolic", 80))
        entry = {
            "VitalsID": f"VIT-{uuid.uuid4().hex[:6].upper()}",
            "PatientID": patient_id,
            "Systolic": systolic,
            "Diastolic": diastolic,
            "BloodPressure": f"{systolic}/{diastolic} mmHg",
            "HeartRate": int(data.get("heart_rate", 72)),
            "BloodGlucose": int(data.get("blood_glucose", 95)),
            "OxygenSpO2": int(data.get("oxygen_spo2", 98)),
            "WeightKg": float(data.get("weight_kg", 70.0)),
            "RecordedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "Notes": data.get("notes", "Routine self-logged vitals")
        }
        all_vitals.insert(0, entry)
        cls._write_json(vitals_file, all_vitals)
        return entry

