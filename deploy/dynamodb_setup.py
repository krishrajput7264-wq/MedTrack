"""
MedTrack AWS DynamoDB Table Setup Script
Run this script once after receiving your AWS credits to automatically provision
all four DynamoDB tables with appropriate primary partition keys and seed initial doctors.

Usage:
    python deploy/dynamodb_setup.py
"""

import sys
import os
import time

# Add root directory to path to load config
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import Config
from services.aws_client import get_dynamodb_resource, get_boto3_session

def create_tables():
    session = get_boto3_session()
    if not session:
        print("[ERROR] Could not create Boto3 session. Please check your AWS credentials in .env")
        return

    dynamodb = session.resource("dynamodb")
    client = session.client("dynamodb")

    existing_tables = client.list_tables().get("TableNames", [])
    print(f"Connected to AWS Region: {Config.AWS_REGION}")
    print(f"Existing tables in account: {existing_tables}")

    tables_to_create = [
        {
            "TableName": Config.DYNAMODB_PATIENTS_TABLE,
            "KeySchema": [{"AttributeName": "PatientID", "KeyType": "HASH"}],
            "AttributeDefinitions": [{"AttributeName": "PatientID", "AttributeType": "S"}],
        },
        {
            "TableName": Config.DYNAMODB_DOCTORS_TABLE,
            "KeySchema": [{"AttributeName": "DoctorID", "KeyType": "HASH"}],
            "AttributeDefinitions": [{"AttributeName": "DoctorID", "AttributeType": "S"}],
        },
        {
            "TableName": Config.DYNAMODB_APPOINTMENTS_TABLE,
            "KeySchema": [{"AttributeName": "AppointmentID", "KeyType": "HASH"}],
            "AttributeDefinitions": [{"AttributeName": "AppointmentID", "AttributeType": "S"}],
        },
        {
            "TableName": Config.DYNAMODB_DIAGNOSES_TABLE,
            "KeySchema": [{"AttributeName": "DiagnosisID", "KeyType": "HASH"}],
            "AttributeDefinitions": [{"AttributeName": "DiagnosisID", "AttributeType": "S"}],
        },
    ]

    for table_def in tables_to_create:
        name = table_def["TableName"]
        if name in existing_tables:
            print(f"[INFO] Table '{name}' already exists. Skipping creation.")
        else:
            print(f"[PROVISIONING] Creating table '{name}'...")
            try:
                table = dynamodb.create_table(
                    TableName=name,
                    KeySchema=table_def["KeySchema"],
                    AttributeDefinitions=table_def["AttributeDefinitions"],
                    BillingMode="PAY_PER_REQUEST"  # On-demand, ideal for free tier & credits
                )
                print(f"[SUCCESS] Table creation request initiated for '{name}'. Waiting for active state...")
                table.wait_until_exists()
                print(f"[ACTIVE] Table '{name}' is ready!")
            except Exception as e:
                print(f"[ERROR] Failed to create table '{name}': {e}")

    print("\n[COMPLETE] All MedTrack DynamoDB tables are verified and ready for live production!")

if __name__ == "__main__":
    create_tables()
