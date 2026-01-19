from statemachine import State, StateMachine

from mcr_meeting.app.models import Meeting, MeetingStatus
from mcr_meeting.app.schemas.report_generation import ReportGenerationResponse
from mcr_meeting.app.statemachine_actions.meeting_actions import (
    after_complete_report_handler,
    after_init_transcription_handler,
    after_start_report_handler,
    after_transition_handler,
    update_status_handler,
)


# Tip: Run `make generate-graphs` to automatically generate all state machine diagrams
# and save them in the `mcr_meeting/app/state_machine/graph/` directory.
class RecordMeetingStateMachine(StateMachine):
    def __init__(self, meeting: Meeting | None = None):
        self.meeting: Meeting | None = meeting
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
    REPORT_PENDING = State(MeetingStatus.REPORT_PENDING)
    REPORT_DONE = State(MeetingStatus.REPORT_DONE)

    # -------------------------------------------------------------------------
    # TRANSITIONS / EVENTS
    # -------------------------------------------------------------------------
    FAIL_CAPTURE = CAPTURE_IN_PROGRESS.to(CAPTURE_FAILED)
    INIT_TRANSCRIPTION = (
        CAPTURE_IN_PROGRESS.to(TRANSCRIPTION_PENDING)
        | CAPTURE_FAILED.to(TRANSCRIPTION_PENDING)
        | TRANSCRIPTION_FAILED.to(TRANSCRIPTION_PENDING)
    )
    START_TRANSCRIPTION = TRANSCRIPTION_PENDING.to(TRANSCRIPTION_IN_PROGRESS)
    COMPLETE_TRANSCRIPTION = (
        TRANSCRIPTION_IN_PROGRESS.to(TRANSCRIPTION_DONE)
        | TRANSCRIPTION_DONE.to.itself(internal=True)  # type: ignore[no-untyped-call]
        | REPORT_DONE.to(TRANSCRIPTION_DONE)
    )
    FAIL_TRANSCRIPTION = TRANSCRIPTION_PENDING.to(
        TRANSCRIPTION_FAILED
    ) | TRANSCRIPTION_IN_PROGRESS.to(TRANSCRIPTION_FAILED)
    START_REPORT = TRANSCRIPTION_DONE.to(REPORT_PENDING)
    COMPLETE_REPORT = REPORT_PENDING.to(REPORT_DONE)

    # -------------------------------------------------------------------------
    # AFTER HOOKS (SIDE EFFECTS)
    # -------------------------------------------------------------------------
    def after_INIT_TRANSCRIPTION(self) -> None:
        if self.meeting is None:
            return
        after_init_transcription_handler(self.meeting, self.current_state_value)

    def after_START_TRANSCRIPTION(self) -> None:
        if self.meeting is None:
            return
        update_status_handler(self.meeting, self.current_state_value)

    def after_COMPLETE_TRANSCRIPTION(self) -> None:
        if self.meeting is None:
            return
        update_status_handler(self.meeting, self.current_state_value)

    def after_FAIL_TRANSCRIPTION(self) -> None:
        if self.meeting is None:
            return
        update_status_handler(self.meeting, self.current_state_value)

    def after_START_REPORT(self) -> None:
        if self.meeting is None:
            return
        after_start_report_handler(self.meeting, self.current_state_value)

    def after_COMPLETE_REPORT(self, report_response: ReportGenerationResponse) -> None:
        if self.meeting is None:
            return
        after_complete_report_handler(
            self.meeting, self.current_state_value, report_response
        )

    def after_transition(self) -> None:
        if self.meeting is None:
            return
        after_transition_handler(self.meeting.id, self.current_state_value)
