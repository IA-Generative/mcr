from mcr_meeting.app.configs.base import S3Settings

s3_settings = S3Settings()


def get_transcription_object_name(meeting_id: int, filename: str) -> str:
    return f"{s3_settings.S3_TRANSCRIPTION_FOLDER}/{meeting_id}/{filename}"
