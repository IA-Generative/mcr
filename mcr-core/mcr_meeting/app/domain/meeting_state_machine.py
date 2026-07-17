from statemachine import State, StateMachine
from statemachine.exceptions import InvalidStateValue

from mcr_meeting.app.exceptions.exceptions import MeetingStateConflictException
from mcr_meeting.app.models import Meeting, MeetingStatus
from mcr_meeting.app.models.meeting_model import MeetingPlatforms


class VisioMeetingStateMachine(StateMachine):
    def __init__(self, meeting: Meeting | None = None):
        if meeting is None:
            super().__init__()
        else:
            super().__init__(model=meeting, start_value=meeting.status)

    # states
    NONE = State(MeetingStatus.NONE, initial=True)
    CAPTURE_PENDING = State(MeetingStatus.CAPTURE_PENDING)
    CAPTURE_BOT_IS_CONNECTING = State(MeetingStatus.CAPTURE_BOT_IS_CONNECTING)
    CAPTURE_BOT_CONNECTION_FAILED = State(MeetingStatus.CAPTURE_BOT_CONNECTION_FAILED)
    CAPTURE_IN_PROGRESS = State(MeetingStatus.CAPTURE_IN_PROGRESS)
    CAPTURE_FAILED = State(MeetingStatus.CAPTURE_FAILED)
    CAPTURE_DONE = State(MeetingStatus.CAPTURE_DONE)
    TRANSCRIPTION_PENDING = State(MeetingStatus.TRANSCRIPTION_PENDING)
    TRANSCRIPTION_IN_PROGRESS = State(MeetingStatus.TRANSCRIPTION_IN_PROGRESS)
    TRANSCRIPTION_DONE = State(MeetingStatus.TRANSCRIPTION_DONE)
    TRANSCRIPTION_FAILED = State(MeetingStatus.TRANSCRIPTION_FAILED)
    DELETED = State(MeetingStatus.DELETED, final=True)

    # transitions / events
    INIT_CAPTURE = NONE.to(CAPTURE_PENDING) | CAPTURE_BOT_CONNECTION_FAILED.to(
        CAPTURE_PENDING
    )
    START_CAPTURE_BOT = CAPTURE_BOT_IS_CONNECTING.to(CAPTURE_IN_PROGRESS)
    FAIL_CAPTURE_BOT = CAPTURE_BOT_IS_CONNECTING.to(CAPTURE_BOT_CONNECTION_FAILED)
    START_CAPTURE = CAPTURE_PENDING.to(CAPTURE_BOT_IS_CONNECTING)
    COMPLETE_CAPTURE = CAPTURE_IN_PROGRESS.to(CAPTURE_DONE)
    FAIL_CAPTURE = CAPTURE_IN_PROGRESS.to(CAPTURE_FAILED)
    INIT_TRANSCRIPTION = (
        CAPTURE_DONE.to(TRANSCRIPTION_PENDING)
        | CAPTURE_FAILED.to(TRANSCRIPTION_PENDING)
        | TRANSCRIPTION_FAILED.to(TRANSCRIPTION_PENDING)
    )
    FORCED_REQUEUE = (
        TRANSCRIPTION_IN_PROGRESS.to(TRANSCRIPTION_PENDING)
        | TRANSCRIPTION_FAILED.to(TRANSCRIPTION_PENDING)
        | TRANSCRIPTION_PENDING.to.itself()  # type: ignore[no-untyped-call]
    )
    START_TRANSCRIPTION = TRANSCRIPTION_PENDING.to(TRANSCRIPTION_IN_PROGRESS)
    COMPLETE_TRANSCRIPTION = TRANSCRIPTION_IN_PROGRESS.to(TRANSCRIPTION_DONE)
    FAIL_TRANSCRIPTION = TRANSCRIPTION_PENDING.to(
        TRANSCRIPTION_FAILED
    ) | TRANSCRIPTION_IN_PROGRESS.to(TRANSCRIPTION_FAILED)
    # Ignore mypy warning: from_.any() is dynamic DSL, not typed
    DELETE = DELETED.from_.any()  # type: ignore


class RecordMeetingStateMachine(StateMachine):
    def __init__(self, meeting: Meeting | None = None):
        if meeting is None:
            super().__init__()
        else:
            super().__init__(model=meeting, start_value=meeting.status)

    # states
    CAPTURE_IN_PROGRESS = State(MeetingStatus.CAPTURE_IN_PROGRESS, initial=True)
    CAPTURE_FAILED = State(MeetingStatus.CAPTURE_FAILED)
    TRANSCRIPTION_PENDING = State(MeetingStatus.TRANSCRIPTION_PENDING)
    TRANSCRIPTION_IN_PROGRESS = State(MeetingStatus.TRANSCRIPTION_IN_PROGRESS)
    TRANSCRIPTION_DONE = State(MeetingStatus.TRANSCRIPTION_DONE)
    TRANSCRIPTION_FAILED = State(MeetingStatus.TRANSCRIPTION_FAILED)
    DELETED = State(MeetingStatus.DELETED, final=True)

    # transitions / events
    FAIL_CAPTURE = CAPTURE_IN_PROGRESS.to(CAPTURE_FAILED)
    INIT_TRANSCRIPTION = (
        CAPTURE_IN_PROGRESS.to(TRANSCRIPTION_PENDING)
        | CAPTURE_FAILED.to(TRANSCRIPTION_PENDING)
        | TRANSCRIPTION_FAILED.to(TRANSCRIPTION_PENDING)
    )
    FORCED_REQUEUE = (
        TRANSCRIPTION_IN_PROGRESS.to(TRANSCRIPTION_PENDING)
        | TRANSCRIPTION_FAILED.to(TRANSCRIPTION_PENDING)
        | TRANSCRIPTION_PENDING.to.itself()  # type: ignore[no-untyped-call]
    )
    START_TRANSCRIPTION = TRANSCRIPTION_PENDING.to(TRANSCRIPTION_IN_PROGRESS)
    COMPLETE_TRANSCRIPTION = TRANSCRIPTION_IN_PROGRESS.to(TRANSCRIPTION_DONE)
    FAIL_TRANSCRIPTION = TRANSCRIPTION_PENDING.to(
        TRANSCRIPTION_FAILED
    ) | TRANSCRIPTION_IN_PROGRESS.to(TRANSCRIPTION_FAILED)
    # Ignore mypy warning: from_.any() is dynamic DSL, not typed
    DELETE = DELETED.from_.any()  # type: ignore


class ImportMeetingStateMachine(StateMachine):
    def __init__(self, meeting: Meeting | None = None):
        if meeting is None:
            super().__init__()
        else:
            super().__init__(model=meeting, start_value=meeting.status)

    # states
    IMPORT_PENDING = State(MeetingStatus.IMPORT_PENDING, initial=True)
    TRANSCRIPTION_PENDING = State(MeetingStatus.TRANSCRIPTION_PENDING)
    TRANSCRIPTION_IN_PROGRESS = State(MeetingStatus.TRANSCRIPTION_IN_PROGRESS)
    TRANSCRIPTION_DONE = State(MeetingStatus.TRANSCRIPTION_DONE)
    TRANSCRIPTION_FAILED = State(MeetingStatus.TRANSCRIPTION_FAILED)
    DELETED = State(MeetingStatus.DELETED, final=True)

    # transitions / events
    INIT_TRANSCRIPTION = IMPORT_PENDING.to(
        TRANSCRIPTION_PENDING
    ) | TRANSCRIPTION_FAILED.to(TRANSCRIPTION_PENDING)
    FORCED_REQUEUE = (
        TRANSCRIPTION_IN_PROGRESS.to(TRANSCRIPTION_PENDING)
        | TRANSCRIPTION_FAILED.to(TRANSCRIPTION_PENDING)
        | TRANSCRIPTION_PENDING.to.itself()  # type: ignore[no-untyped-call]
    )
    START_TRANSCRIPTION = TRANSCRIPTION_PENDING.to(TRANSCRIPTION_IN_PROGRESS)
    COMPLETE_TRANSCRIPTION = TRANSCRIPTION_IN_PROGRESS.to(TRANSCRIPTION_DONE)
    FAIL_TRANSCRIPTION = TRANSCRIPTION_PENDING.to(
        TRANSCRIPTION_FAILED
    ) | TRANSCRIPTION_IN_PROGRESS.to(TRANSCRIPTION_FAILED)
    # Ignore mypy warning: from_.any() is dynamic DSL, not typed
    DELETE = DELETED.from_.any()  # type: ignore


def get_state_machine_for_meeting(
    meeting: Meeting,
) -> VisioMeetingStateMachine | RecordMeetingStateMachine | ImportMeetingStateMachine:
    match meeting.name_platform:
        case MeetingPlatforms.MCR_IMPORT:
            return _from_status(ImportMeetingStateMachine, meeting)
        case MeetingPlatforms.MCR_RECORD:
            return _from_status(RecordMeetingStateMachine, meeting)
        case _:
            return _from_status(VisioMeetingStateMachine, meeting)


def _from_status(
    cls: type[
        VisioMeetingStateMachine | RecordMeetingStateMachine | ImportMeetingStateMachine
    ],
    meeting: Meeting,
) -> VisioMeetingStateMachine | RecordMeetingStateMachine | ImportMeetingStateMachine:
    try:
        return cls(meeting)
    except InvalidStateValue as exc:
        raise MeetingStateConflictException(
            f"No state found for {meeting.status}"
        ) from exc
