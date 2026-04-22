from enum import StrEnum
from typing import Any, NamedTuple

from celery.app.task import Task

# # Monkey patch Task so generic params can be provided (offical celery-types fix https://github.com/sbdchd/celery-types?tab=readme-ov-file#install)
Task.__class_getitem__ = classmethod(lambda cls, *args, **kwargs: cls)  # type: ignore[attr-defined]


class ReportTaskArgs(NamedTuple):
    meeting_id: int
    owner_keycloak_uuid: str | None


def extract_report_task_args(
    kwargs: dict[str, Any],
    sender: Any | None = None,
) -> ReportTaskArgs:
    args: list[Any] | None = None
    task_kwargs: dict[str, Any] | None = None

    if "args" in kwargs and kwargs["args"]:
        args = kwargs["args"]
    elif (
        sender is not None
        and hasattr(sender, "request")
        and hasattr(sender.request, "args")
        and sender.request.args
    ):
        args = sender.request.args

    if "kwargs" in kwargs and kwargs["kwargs"]:
        task_kwargs = kwargs["kwargs"]
    elif (
        sender is not None
        and hasattr(sender, "request")
        and hasattr(sender.request, "kwargs")
        and sender.request.kwargs
    ):
        task_kwargs = sender.request.kwargs

    if args is None or len(args) < 1:
        raise ValueError("Unable to extract meeting_id from signal args")

    owner_keycloak_uuid: str | None = None
    if task_kwargs is not None:
        owner_keycloak_uuid = task_kwargs.get("owner_keycloak_uuid")

    return ReportTaskArgs(
        meeting_id=args[0],
        owner_keycloak_uuid=owner_keycloak_uuid,
    )


class MCRTranscriptionTasks(StrEnum):
    BASE_NAME = "transcription_worker"

    TRANSCRIBE = f"{BASE_NAME}.transcribe"
    EVALUATE = f"{BASE_NAME}.evaluate"

    @classmethod
    def select_all_tasks(cls) -> str:
        return f"{cls.BASE_NAME}.*"


class ReportTypes(StrEnum):
    DECISION_RECORD = "DECISION_RECORD"
    DETAILED_SYNTHESIS = "DETAILED_SYNTHESIS"


class MCRReportGenerationTasks(StrEnum):
    BASE_NAME = "generation_worker"

    REPORT = f"{BASE_NAME}.report"

    @classmethod
    def select_all_tasks(cls) -> str:
        return f"{cls.BASE_NAME}.*"
