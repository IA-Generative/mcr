import boto3
from botocore.config import Config
from mypy_boto3_s3 import S3Client

from mcr_meeting.app.configs.base import RetrySettings, S3Settings

s3_settings = S3Settings()
_retry_settings = RetrySettings()

_boto_config = Config(
    connect_timeout=_retry_settings.S3_CONNECT_TIMEOUT,
    read_timeout=_retry_settings.S3_READ_TIMEOUT,
    retries={"total_max_attempts": 1},
)


endpoint_url = s3_settings.S3_ENDPOINT

if not endpoint_url.startswith(("http://", "https://")):
    endpoint_url = f"http://{endpoint_url}"

use_ssl = endpoint_url.startswith("https://")


s3_client: S3Client = boto3.client(
    service_name="s3",
    use_ssl=use_ssl,
    endpoint_url=endpoint_url,
    aws_access_key_id=s3_settings.S3_ACCESS_KEY,
    aws_secret_access_key=s3_settings.S3_SECRET_KEY,
    region_name=s3_settings.S3_REGION,
    config=_boto_config,
)


# Create an "external" client to generate the presigned URL
# This client cannot reach the server from inside the cluster, as it is using the S3_EXTERNAL_ENDPOINT
s3_external_client: S3Client = boto3.client(
    service_name="s3",
    use_ssl=use_ssl,
    endpoint_url=s3_settings.S3_EXTERNAL_ENDPOINT,
    aws_access_key_id=s3_settings.S3_ACCESS_KEY,
    aws_secret_access_key=s3_settings.S3_SECRET_KEY,
    region_name=s3_settings.S3_REGION,
    config=_boto_config,
)
