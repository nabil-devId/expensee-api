# create class to save file to gcs
from google.cloud import storage
import logging

class GCSUploader:
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)
        self.logger = logging.getLogger(__name__)

    def upload_file(self, file_path: str, destination_blob_name: str) -> str:
        """
        Uploads a file to the GCS bucket.

        Args:
            file_path (str): Local path to the file to upload.
            destination_blob_name (str): The destination path in the bucket.

        Returns:
            str: The public URL of the uploaded file.
        """
        blob = self.bucket.blob(destination_blob_name)
        blob.upload_from_filename(file_path)
        self.logger.info(f"File {file_path} uploaded to {destination_blob_name}.")
        return f"gs://{self.bucket_name}/{destination_blob_name}"

    def upload_bytes(self, data: bytes, destination_blob_name: str, content_type: str = "application/octet-stream") -> str:
        """
        Uploads byte data to the GCS bucket.

        Args:
            data (bytes): The data to upload.
            destination_blob_name (str): The destination path in the bucket.
            content_type (str): The MIME type of the file.

        Returns:
            str: The public URL of the uploaded file.
        """
        blob = self.bucket.blob(destination_blob_name)
        blob.upload_from_string(data, content_type=content_type)
        self.logger.info(f"Bytes uploaded to {destination_blob_name}.")
        return f"gs://{self.bucket_name}/{destination_blob_name}"
