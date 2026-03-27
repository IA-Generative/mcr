from enum import StrEnum
from typing import Any, NamedTuple, TypedDict

from celery.app.task import Task

# Monkey patch Task so generic params can be provided (official celery-types fix https://github.com/sbdchd/celery-types?tab=readme-ov-file#install)
Task.__class_getitem__ = classmethod(lambda cls, *args, **kwargs: cls)  # type: ignore[attr-defined]


class CelerySignalArgs(TypedDict):
    task_id: int
    args: list[Any]  # type: ignore[explicit-any]


class TranscriptionTaskArgs(NamedTuple):
    meeting_id: int
    owner_keycloak_uuid: str


def extract_transcription_task_args(  # type: ignore[explicit-any]
    kwargs: dict[str, Any],
    sender: Any | None = None,
) -> TranscriptionTaskArgs:
    args: list[Any] | None = None  # type: ignore[explicit-any]

    if "args" in kwargs and kwargs["args"]:
        args = kwargs["args"]
    elif (
        sender is not None
        and hasattr(sender, "request")
        and hasattr(sender.request, "args")
        and sender.request.args
    ):
        args = sender.request.args

    if args is None or len(args) < 2:
        raise ValueError(
            "Unable to extract meeting_id and owner_keycloak_uuid from signal args"
        )

    return TranscriptionTaskArgs(
        meeting_id=args[0],
        owner_keycloak_uuid=args[1],
    )


class MCRCeleryTask(StrEnum):
    pass


class MCRTranscriptionTasks(MCRCeleryTask):
    BASE_NAME = "transcription_worker"

    TRANSCRIBE = f"{BASE_NAME}.transcribe"
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
