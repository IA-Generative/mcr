from enum import StrEnum

from celery.app.task import Task

# # Monkey patch Task so generic params can be provided (offical celery-types fix https://github.com/sbdchd/celery-types?tab=readme-ov-file#install)
Task.__class_getitem__ = classmethod(lambda cls, *args, **kwargs: cls)  # type: ignore[attr-defined]


class MCRTranscriptionTasks(StrEnum):
    BASE_NAME = "transcription_worker"

    TRANSCRIBE = f"{BASE_NAME}.transcribe"
    EVALUATE = f"{BASE_NAME}.evaluate"

    @classmethod
    def select_all_tasks(cls) -> str:
        return f"{cls.BASE_NAME}.*"


class MCRReportGenerationTasks(StrEnum):
    BASE_NAME = "generation_worker"

    REPORT = f"{BASE_NAME}.report"

    @classmethod
    def select_all_tasks(cls) -> str:
        return f"{cls.BASE_NAME}.*"
