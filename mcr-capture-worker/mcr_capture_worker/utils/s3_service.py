from mcr_capture_worker.settings.settings import S3Settings

s3_settings = S3Settings()


def get_audio_object_prefix(meeting_id: str) -> str:
    return f"{s3_settings.S3_AUDIO_FOLDER}/{meeting_id}/"


def get_trace_object_prefix(meeting_id: str) -> str:
    return f"{s3_settings.S3_TRACE_FOLDER}/{meeting_id}/"
