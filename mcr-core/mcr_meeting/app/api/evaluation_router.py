from fastapi import (
    APIRouter,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from mcr_meeting.app.configs.base import ApiSettings
from mcr_meeting.app.domain.evaluation_zip import is_zip_filename
from mcr_meeting.app.use_cases.evaluate_transcription_from_s3 import (
    evaluate_transcription_from_s3,
)
from mcr_meeting.app.use_cases.evaluate_transcription_from_zip import (
    evaluate_transcription_from_zip,
)

api_settings = ApiSettings()
router = APIRouter(prefix=api_settings.TRANSCRIPTION_API_PREFIX)


class EvaluationFromS3Request(BaseModel):
    zip_name: str


@router.post(
    "/evaluation-from-zip",
    tags=["ASR Evaluation"],
    status_code=status.HTTP_202_ACCEPTED,
)
async def evaluate_transcription_from_zip_async(
    file: UploadFile = File(...),
) -> Response:
    """
    Evaluate ASR model from a zip file containing audio files and reference transcripts.
    The zip file should be as structured as follow:
    ```
    <any_name>.zip
        ├── raw_audios/
        │   ├── audio1.mp3 (or .wav, ...)
        │   ├── audio2.mp3 (or .wav, ...)
        │   └── ...
        └── reference_transcripts/
            ├── audio1.json
            ├── audio2.json
            └── ...
    ```
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Corrupted file. Please upload a valid zip file.",
        )

    if not is_zip_filename(file.filename):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Invalid file type. Please upload a zip file.",
        )

    zip_data = await file.read()
    evaluate_transcription_from_zip(zip_bytes=zip_data)

    return PlainTextResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content="Evaluation started... Result will be available shortly",
    )


@router.post(
    "/evaluation-from-s3",
    tags=["ASR Evaluation"],
    status_code=status.HTTP_202_ACCEPTED,
)
async def evaluate_transcription_from_s3_async(
    request: EvaluationFromS3Request,
) -> Response:
    """
    Evaluate ASR model from a zip file stored in S3.
    The zip file should follow the same structure as the `/evaluation-from-zip` endpoint.

    The `zip_name` parameter should be the S3 object key of the zip file.
    ```
    Default dataset:
    clean_dataset.zip
    noisy_dataset.zip
    ```
    """
    evaluate_transcription_from_s3(zip_name=request.zip_name)

    return PlainTextResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content="Evaluation from S3 started... Result will be available shortly",
    )
