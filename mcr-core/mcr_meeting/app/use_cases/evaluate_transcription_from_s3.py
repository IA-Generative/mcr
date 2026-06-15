from mcr_meeting.app.domain.evaluation_zip import is_zip_filename
from mcr_meeting.app.exceptions.exceptions import BadRequestException
from mcr_meeting.app.infrastructure.celery import enqueue_evaluation_from_s3_task


def evaluate_transcription_from_s3(zip_name: str) -> None:

    if not is_zip_filename(zip_name):
        raise BadRequestException("zip_name must reference a .zip file.")
    enqueue_evaluation_from_s3_task(zip_name)
