from mcr_capture_worker.services.meeting_monitors.abstract_meeting_monitor import (
    MeetingMonitor,
)


class WebexNodeMeetingMonitor(MeetingMonitor):
    """Monitor for the Webex Node subprocess capture path.

    Participant count is pushed in from SDK events via update_participant_count,
    rather than scraped from the DOM.
    """

    def __init__(self) -> None:
        super().__init__()
        self._participant_count: int = 0

    def update_participant_count(self, count: int) -> None:
        self._participant_count = count

    async def _get_participant_count(self) -> int:
        return self._participant_count
