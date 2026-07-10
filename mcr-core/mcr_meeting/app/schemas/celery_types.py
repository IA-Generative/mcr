from enum import StrEnum

from celery.app.task import Task

# Monkey patch Task so generic params can be provided (official celery-types fix https://github.com/sbdchd/celery-types?tab=readme-ov-file#install)
Task.__class_getitem__ = classmethod(lambda cls, *args, **kwargs: cls)  # type: ignore[attr-defined]


class MCRCeleryTask(StrEnum):
    pass


class MCRTranscriptionTasks(MCRCeleryTask):
    BASE_NAME = "transcription_worker"

    TRANSCRIBE = f"{BASE_NAME}.transcribe"
    DIARIZE = f"{BASE_NAME}.diarize"
    TRANSCRIBE_CHUNKS = f"{BASE_NAME}.transcribe_chunks"
    FINALIZE_TRANSCRIPTION = f"{BASE_NAME}.finalize_transcription"
    MARK_TRANSCRIPTION_FAILED = f"{BASE_NAME}.mark_transcription_failed"
    EVALUATE = f"{BASE_NAME}.evaluate"
    EVALUATE_FROM_S3 = f"{BASE_NAME}.evaluate_from_s3"

    @classmethod
    def select_all_tasks(cls) -> str:
        return f"{cls.BASE_NAME}.*"


class MCRReportGenerationTasks(MCRCeleryTask):
    BASE_NAME = "generation_worker"

    REPORT = f"{BASE_NAME}.report"

    @classmethod
    def select_all_tasks(cls) -> str:
        return f"{cls.BASE_NAME}.*"
