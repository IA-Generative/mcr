from io import BytesIO

from botocore.exceptions import ClientError

from mcr_generation.app.configs.settings import S3Settings
from mcr_generation.app.exceptions.exceptions import (
    MCRGenerationException,
    TranscriptionFileNotFoundError,
)
from mcr_generation.app.utils.s3_client import s3_client

s3_settings = S3Settings()


def get_file_from_s3(object_name: str) -> BytesIO:
    try:
        response = s3_client.get_object(Bucket=s3_settings.S3_BUCKET, Key=object_name)
        return BytesIO(response["Body"].read())
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code in {"NoSuchKey", "404"}:
            raise TranscriptionFileNotFoundError(
                f"Transcription file not found in S3: {object_name}"
            ) from e
        raise MCRGenerationException(
            f"S3 download failed for {object_name}: {e}"
        ) from e
    except Exception as e:
        raise MCRGenerationException(
            f"S3 download failed for {object_name}: {e}"
        ) from e
