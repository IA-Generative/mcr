import boto3

from mcr_generation.app.configs.settings import S3Settings

s3_settings = S3Settings()

# Create S3 client configured for MinIO/Scaleway S3 bucket
endpoint_url = s3_settings.S3_ENDPOINT
use_ssl = endpoint_url.startswith("https://")

if not endpoint_url.startswith(("http://", "https://")):
    endpoint_url = f"http://{endpoint_url}"

s3_client = boto3.client(
    service_name="s3",
    use_ssl=use_ssl,
    endpoint_url=endpoint_url,
    aws_access_key_id=s3_settings.S3_ACCESS_KEY,
    aws_secret_access_key=s3_settings.S3_SECRET_KEY,
    region_name=s3_settings.S3_REGION,
)
