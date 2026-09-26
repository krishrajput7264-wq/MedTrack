import os
import json
import logging
import datetime
from config import Config
from services.aws_client import get_cloudwatch_client

# Configure standard logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("MedTrack")

class CloudWatchAuditLogger:
    """
    Structured audit logger.
    Logs locally and optionally emits CloudWatch custom metrics/logs when USE_AWS=True.
    """
    @staticmethod
    def log_event(event_type: str, user_id: str, role: str, details: dict):
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        payload = {
            "timestamp": timestamp,
            "event_type": event_type,
            "user_id": user_id,
            "role": role,
            "details": details
        }
        
        # Log to application stdout / file
        logger.info(f"[AUDIT] {event_type} - User: {user_id} ({role}) - {json.dumps(details)}")

        # If AWS mode is on, publish custom metric
        if Config.USE_AWS:
            try:
                cw = get_cloudwatch_client()
                if cw:
                    cw.put_metric_data(
                        Namespace="MedTrack/Application",
                        MetricData=[
                            {
                                "MetricName": event_type,
                                "Dimensions": [
                                    {"Name": "Role", "Value": role}
                                ],
                                "Value": 1.0,
                                "Unit": "Count"
                            }
                        ]
                    )
            except Exception as e:
                logger.warning(f"Could not push metric to CloudWatch: {e}")

        # Record in local audit file for review
        try:
            os.makedirs(Config.DATA_DIR, exist_ok=True)
            audit_file = os.path.join(Config.DATA_DIR, "audit_trail.jsonl")
            with open(audit_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload) + "\n")
        except Exception as err:
            logger.error(f"Failed to record local audit trail: {err}")
