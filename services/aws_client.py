import boto3
import logging
from config import Config

logger = logging.getLogger("medtrack.aws")

def get_boto3_session():
    """
    Creates and returns a boto3 Session.
    Supports explicit API keys, AWS Academy session tokens,
    or falls back to EC2 IAM Role instance profile credentials.
    """
    session_kwargs = {
        "region_name": Config.AWS_REGION
    }
    
    if Config.AWS_ACCESS_KEY_ID and Config.AWS_SECRET_ACCESS_KEY:
        session_kwargs["aws_access_key_id"] = Config.AWS_ACCESS_KEY_ID
        session_kwargs["aws_secret_access_key"] = Config.AWS_SECRET_ACCESS_KEY
        if Config.AWS_SESSION_TOKEN:
            session_kwargs["aws_session_token"] = Config.AWS_SESSION_TOKEN

    try:
        return boto3.Session(**session_kwargs)
    except Exception as e:
        logger.error(f"Failed to create Boto3 session: {e}")
        return None

def get_dynamodb_resource():
    """Returns DynamoDB Service Resource."""
    session = get_boto3_session()
    if session:
        return session.resource("dynamodb")
    return None

def get_sns_client():
    """Returns SNS Client."""
    session = get_boto3_session()
    if session:
        return session.client("sns")
    return None

def get_s3_client():
    """Returns S3 Client."""
    session = get_boto3_session()
    if session:
        return session.client("s3")
    return None

def get_cloudwatch_client():
    """Returns CloudWatch Client."""
    session = get_boto3_session()
    if session:
        return session.client("cloudwatch")
    return None
