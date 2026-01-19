from io import BytesIO

from loguru import logger

from mcr_generation.app.configs.settings import S3Settings
from mcr_generation.app.utils.s3_client import s3_client

s3_settings = S3Settings()


def get_file_from_s3(object_name: str) -> BytesIO:
    try:
        response = s3_client.get_object(Bucket=s3_settings.S3_BUCKET, Key=object_name)

        return BytesIO(response["Body"].read())
    except Exception as e:
        logger.error("Error while getting audio from S3 bucket: {}", e)
        raise e
