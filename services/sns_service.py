import os
import json
import uuid
import datetime
import logging
from config import Config
from services.aws_client import get_sns_client

logger = logging.getLogger("medtrack.sns")

class NotificationService:
    """
    AWS SNS Notification Service with clean local fallback.
    Dispatches notifications for appointment bookings, confirmations, and diagnosis reports.
    """

    @staticmethod
    def _save_local_notification(recipient, subject, message, event_type):
        """Stores notifications locally so users can review triggered notifications in the UI."""
        os.makedirs(Config.DATA_DIR, exist_ok=True)
        notif_file = os.path.join(Config.DATA_DIR, "notifications.json")
        notifications = []
        if os.path.exists(notif_file):
            try:
                with open(notif_file, "r", encoding="utf-8") as f:
                    notifications = json.load(f)
            except Exception:
                notifications = []

        notif_item = {
            "NotificationID": f"notif_{uuid.uuid4().hex[:8]}",
            "Recipient": recipient,
            "Subject": subject,
            "Message": message,
            "EventType": event_type,
            "Timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "Status": "DELIVERED (SIMULATED)" if not Config.USE_AWS else "PUBLISHED_TO_SNS"
        }
        notifications.insert(0, notif_item)
        
        # Keep latest 50
        notifications = notifications[:50]
        with open(notif_file, "w", encoding="utf-8") as f:
            json.dump(notifications, f, indent=2)

        return notif_item

    @classmethod
    def get_recent_notifications(cls, limit=10):
        notif_file = os.path.join(Config.DATA_DIR, "notifications.json")
        if os.path.exists(notif_file):
            try:
                with open(notif_file, "r", encoding="utf-8") as f:
                    items = json.load(f)
                    return items[:limit]
            except Exception:
                return []
        return []

    @classmethod
    def send_appointment_notification(cls, appointment: dict, recipient_contact: str = None):
        """
        Sends an appointment booking/status update notification via AWS SNS (or local simulation).
        """
        subject = f"MedTrack: Appointment Confirmed - Dr. {appointment.get('DoctorName', 'Specialist')}"
        message = (
            f"Dear {appointment.get('PatientName', 'Patient')},\n\n"
            f"Your medical appointment with Dr. {appointment.get('DoctorName')} ({appointment.get('Department', 'General')}) "
            f"has been confirmed for {appointment.get('Date')} at {appointment.get('Time')}.\n\n"
            f"Appointment ID: {appointment.get('AppointmentID')}\n"
            f"Reason for Visit: {appointment.get('Reason', 'Routine Consultation')}\n"
            f"Location / Telehealth: MedTrack Central Clinic - Suite 4B\n\n"
            f"To modify or reschedule, please access your MedTrack Patient Portal."
        )

        recipient = recipient_contact or appointment.get("PatientEmail", "patient@medtrack.org")

        if Config.USE_AWS and Config.SNS_APPOINTMENT_TOPIC_ARN:
            try:
                sns = get_sns_client()
                if sns:
                    response = sns.publish(
                        TopicArn=Config.SNS_APPOINTMENT_TOPIC_ARN,
                        Message=message,
                        Subject=subject,
                        MessageAttributes={
                            "AppointmentID": {"DataType": "String", "StringValue": str(appointment.get("AppointmentID"))},
                            "PatientID": {"DataType": "String", "StringValue": str(appointment.get("PatientID"))}
                        }
                    )
                    logger.info(f"AWS SNS Appointment published. MessageId: {response.get('MessageId')}")
                    cls._save_local_notification(recipient, subject, message, "APPOINTMENT_BOOKED")
                    return response.get("MessageId")
            except Exception as e:
                logger.error(f"Failed to publish to AWS SNS: {e}")

        # Fallback simulation
        logger.info(f"[SIMULATED SNS] To: {recipient} | Subject: {subject}")
        notif = cls._save_local_notification(recipient, subject, message, "APPOINTMENT_BOOKED")
        return notif["NotificationID"]

    @classmethod
    def send_diagnosis_notification(cls, diagnosis: dict, patient_name: str, recipient_email: str):
        """
        Sends diagnosis report available notification to patient.
        """
        subject = f"MedTrack Alert: New Medical Diagnosis & Report Submitted"
        message = (
            f"Dear {patient_name},\n\n"
            f"Dr. {diagnosis.get('DoctorName', 'Your Doctor')} has uploaded a new diagnosis evaluation and medical report "
            f"for your consultation regarding {diagnosis.get('Condition', 'Medical Visit')}.\n\n"
            f"Diagnosis Summary: {diagnosis.get('Summary', 'Report uploaded.')}\n"
            f"Prescription / Treatment Plan: {diagnosis.get('Prescription', 'See attached report')}\n\n"
            f"Please log in to your MedTrack Portal to review complete notes and download test documents."
        )

        if Config.USE_AWS and Config.SNS_DIAGNOSIS_TOPIC_ARN:
            try:
                sns = get_sns_client()
                if sns:
                    response = sns.publish(
                        TopicArn=Config.SNS_DIAGNOSIS_TOPIC_ARN,
                        Message=message,
                        Subject=subject
                    )
                    logger.info(f"AWS SNS Diagnosis published. MessageId: {response.get('MessageId')}")
                    cls._save_local_notification(recipient_email, subject, message, "DIAGNOSIS_SUBMITTED")
                    return response.get("MessageId")
            except Exception as e:
                logger.error(f"Failed to publish to AWS SNS: {e}")

        logger.info(f"[SIMULATED SNS] To: {recipient_email} | Subject: {subject}")
        notif = cls._save_local_notification(recipient_email, subject, message, "DIAGNOSIS_SUBMITTED")
        return notif["NotificationID"]

    @classmethod
    def send_appointment_accepted_notification(cls, appointment: dict, recipient_contact: str = None):
        """Notifies patient that doctor has accepted their consultation application."""
        subject = f"MedTrack: Application Accepted by Dr. {appointment.get('DoctorName', 'Specialist')}"
        message = (
            f"Dear {appointment.get('PatientName', 'Patient')},\n\n"
            f"Great news! Dr. {appointment.get('DoctorName')} has reviewed and confirmed your consultation request.\n\n"
            f"• Date: {appointment.get('Date')}\n"
            f"• Time: {appointment.get('Time')}\n"
            f"• Department: {appointment.get('Department', 'Specialist Care')}\n"
            f"• Clinic Location: MedTrack Clinical Center, OPD Consultation Suite\n\n"
            f"Please arrive 10 minutes prior to your allocated slot with any prior medical records."
        )
        recipient = recipient_contact or appointment.get("PatientEmail", "patient@medtrack.org")
        logger.info(f"[SIMULATED SNS] To: {recipient} | Subject: {subject}")
        notif = cls._save_local_notification(recipient, subject, message, "APPOINTMENT_ACCEPTED")
        return notif["NotificationID"]

    @classmethod
    def send_appointment_declined_notification(cls, appointment: dict, reason: str = "Physician unavailable at requested time slot"):
        """Notifies patient if an appointment request could not be accommodated."""
        subject = f"MedTrack: Consultation Update for {appointment.get('Date')}"
        message = (
            f"Dear {appointment.get('PatientName', 'Patient')},\n\n"
            f"Regarding your consultation request with Dr. {appointment.get('DoctorName')} for {appointment.get('Date')} ({appointment.get('Time')}):\n\n"
            f"Update: The clinician is unable to accommodate this specific slot ({reason}).\n\n"
            f"Please visit the MedTrack portal to pick an alternate available slot or select another specialist."
        )
        recipient = appointment.get("PatientEmail", "patient@medtrack.org")
        logger.info(f"[SIMULATED SNS] To: {recipient} | Subject: {subject}")
        notif = cls._save_local_notification(recipient, subject, message, "APPOINTMENT_DECLINED")
        return notif["NotificationID"]

