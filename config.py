import os
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "medtrack-dev-secret-key-2026-secure")
    
    # Toggle between Local Mock Mode and Live AWS Mode
    USE_AWS = os.getenv("USE_AWS", "False").strip().lower() in ("true", "1", "yes")

    # AWS Credentials and Region (supports AWS Academy session tokens)
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN", "")

    # DynamoDB Tables
    DYNAMODB_PATIENTS_TABLE = os.getenv("DYNAMODB_PATIENTS_TABLE", "MedTrack_Patients")
    DYNAMODB_DOCTORS_TABLE = os.getenv("DYNAMODB_DOCTORS_TABLE", "MedTrack_Doctors")
    DYNAMODB_APPOINTMENTS_TABLE = os.getenv("DYNAMODB_APPOINTMENTS_TABLE", "MedTrack_Appointments")
    DYNAMODB_DIAGNOSES_TABLE = os.getenv("DYNAMODB_DIAGNOSES_TABLE", "MedTrack_Diagnoses")

    # AWS SNS Topics
    SNS_APPOINTMENT_TOPIC_ARN = os.getenv("SNS_APPOINTMENT_TOPIC_ARN", "")
    SNS_DIAGNOSIS_TOPIC_ARN = os.getenv("SNS_DIAGNOSIS_TOPIC_ARN", "")

    # AWS S3 Storage for Reports
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "medtrack-medical-reports")

    # Local Storage Paths
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    DATA_DIR = os.path.join(BASE_DIR, "data")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max file upload
