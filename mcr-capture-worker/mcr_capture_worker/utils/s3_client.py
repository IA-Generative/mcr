import boto3
from mypy_boto3_s3 import S3Client

from mcr_capture_worker.settings.settings import S3Settings

s3_settings = S3Settings()

# Create S3 client configured for MinIO/Scaleway
# For MinIO, we need to use http:// and disable SSL
# For Scaleway, we use https:// and enable SSL
endpoint_url = s3_settings.S3_ENDPOINT
use_ssl = endpoint_url.startswith("https://")

s3_client: S3Client = boto3.client(
    service_name="s3",
    use_ssl=use_ssl,
    endpoint_url=endpoint_url,
    aws_access_key_id=s3_settings.S3_ACCESS_KEY,
    aws_secret_access_key=s3_settings.S3_SECRET_KEY,
    region_name=s3_settings.S3_REGION,
)
