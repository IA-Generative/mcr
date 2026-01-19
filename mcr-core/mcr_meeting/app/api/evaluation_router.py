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

from mcr_meeting.app.configs.base import ApiSettings
from mcr_meeting.app.services.transcription_task_service import (
    create_evaluation_task_service,
)

api_settings = ApiSettings()
router = APIRouter(prefix=api_settings.TRANSCRIPTION_API_PREFIX)


@router.post(
    "/evaluation", tags=["ASR Evaluation"], status_code=status.HTTP_202_ACCEPTED
)
async def evaluate_transcription_from_zip_async(
    file: UploadFile = File(...),
) -> Response:
    """
    Evaluate ASR model from a zip file containing audio files and reference transcripts.
    The zip file should be as structured as follow:
    ```
    inputs.zip
        ├── raw_audios/
        │   ├── audio1.mp3
        │   ├── audio2.mp3
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
            f.startswith("inputs/raw_audios/") and f.endswith(".mp3") for f in files
        )
        has_ref_dir = any(
            f.startswith("inputs/reference_transcripts/") and f.endswith(".json")
            for f in files
        )

    if not has_audio_dir or not has_ref_dir:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Zip file must contain 'raw_audios/' with .mp3 files and "
                "'reference_transcripts/' with .json files at the root level."
            ),
        )

    create_evaluation_task_service(zip_bytes=zip_data)

    return PlainTextResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content="Evaluation started... Result will be available shortly",
    )
