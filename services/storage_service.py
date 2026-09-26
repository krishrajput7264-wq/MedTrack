import os
import uuid
from werkzeug.utils import secure_filename
from config import Config
from services.aws_client import get_s3_client
import logging

logger = logging.getLogger("medtrack.storage")

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "docx", "txt"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

class StorageService:
    @staticmethod
    def save_file(file_storage, folder="reports"):
        """
        Saves uploaded file to AWS S3 if USE_AWS=True, else stores in local upload directory.
        Returns: (file_key, access_url)
        """
        if not file_storage or not file_storage.filename:
            return None, None

        orig_filename = secure_filename(file_storage.filename)
        ext = orig_filename.rsplit(".", 1)[1].lower() if "." in orig_filename else "bin"
        unique_name = f"{folder}/{uuid.uuid4().hex}_{orig_filename}"

        if Config.USE_AWS:
            try:
                s3 = get_s3_client()
                if s3:
                    s3.upload_fileobj(
                        file_storage,
                        Config.S3_BUCKET_NAME,
                        unique_name,
                        ExtraArgs={"ContentType": file_storage.content_type or "application/octet-stream"}
                    )
                    url = f"https://{Config.S3_BUCKET_NAME}.s3.{Config.AWS_REGION}.amazonaws.com/{unique_name}"
                    logger.info(f"File uploaded successfully to S3: {url}")
                    return unique_name, url
            except Exception as e:
                logger.error(f"S3 Upload failed, falling back to local storage: {e}")

        # Local fallback
        os.makedirs(os.path.join(Config.UPLOAD_FOLDER, folder), exist_ok=True)
        local_path = os.path.join(Config.UPLOAD_FOLDER, unique_name)
        file_storage.seek(0)
        file_storage.save(local_path)
        local_url = f"/uploads/{unique_name}"
        logger.info(f"File saved locally: {local_path}")
        return unique_name, local_url

    @staticmethod
    def get_download_url(file_key):
        """
        Generates presigned URL from S3 if live, or local URL.
        """
        if not file_key:
            return "#"
            
        if Config.USE_AWS:
            try:
                s3 = get_s3_client()
                if s3:
                    presigned = s3.generate_presigned_url(
                        "get_object",
                        Params={"Bucket": Config.S3_BUCKET_NAME, "Key": file_key},
                        ExpiresIn=3600
                    )
                    return presigned
            except Exception as e:
                logger.warning(f"Could not generate S3 presigned URL: {e}")

        return f"/uploads/{file_key}"
