import zipfile
from io import BytesIO

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

from mcr_meeting.app.configs.base import ApiSettings, EvaluationSettings
from mcr_meeting.app.services.transcription_task_service import (
    create_evaluation_from_s3_task_service,
    create_evaluation_task_service,
)

api_settings = ApiSettings()
EVALUATION_SETTINGS = EvaluationSettings()
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

    filename = file.filename
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Corrupted file. Please upload a valid zip file.",
        )

    if not filename.endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Invalid file type. Please upload a zip file.",
        )

    zip_data = await file.read()

    with zipfile.ZipFile(BytesIO(zip_data), "r") as z:
        files = z.namelist()

        has_audio_dir = any(
            "raw_audios/" in f
            and any(
                f.endswith(f".{fmt}")
                for fmt in EVALUATION_SETTINGS.SUPPORTED_AUDIO_FORMATS
            )
            for f in files
        )
        has_ref_dir = any(
            "reference_transcripts/" in f and f.endswith(".json") for f in files
        )

    if not has_audio_dir or not has_ref_dir:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Zip file must contain 'raw_audios/' with "
                f"{' or '.join('.' + fmt for fmt in EVALUATION_SETTINGS.SUPPORTED_AUDIO_FORMATS)} files and "
                "'reference_transcripts/' with .json files at the root level."
            ),
        )

    create_evaluation_task_service(zip_bytes=zip_data)

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
    if not request.zip_name.endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="zip_name must reference a .zip file.",
        )

    create_evaluation_from_s3_task_service(zip_name=request.zip_name)

    return PlainTextResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content="Evaluation from S3 started... Result will be available shortly",
    )
