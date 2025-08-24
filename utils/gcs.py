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

    def download_bytes_from_uri(self, gcs_uri: str) -> bytes:
        """
        Downloads a file's content as bytes from a GCS URI.

        Args:
            gcs_uri (str): The GCS URI of the file (e.g., gs://bucket_name/blob_name).

        Returns:
            bytes: The content of the file.

        Raises:
            ValueError: If the GCS URI is invalid.
            google.cloud.exceptions.NotFound: If the blob does not exist.
        """
        if not gcs_uri.startswith("gs://"):
            raise ValueError("Invalid GCS URI. Must start with 'gs://'.")
        
        try:
            # Remove 'gs://' prefix
            path_without_scheme = gcs_uri[5:]
            # Split into bucket and blob name
            bucket_name, blob_name = path_without_scheme.split('/', 1)
        except ValueError:
            raise ValueError("Invalid GCS URI format. Expected 'gs://expense_project/receipt_image/blob_name'.")

        # If the URI's bucket is different from the initialized one, get the correct bucket
        if bucket_name != self.bucket_name:
            bucket_to_download_from = self.client.bucket(bucket_name)
        else:
            bucket_to_download_from = self.bucket
            
        blob = bucket_to_download_from.blob(blob_name)
        
        try:
            data = blob.download_as_bytes()
            self.logger.info(f"File {blob_name} from bucket {bucket_name} downloaded successfully.")
            return data
        except Exception as e:
            self.logger.error(f"Failed to download {blob_name} from bucket {bucket_name}: {e}")
            raise
