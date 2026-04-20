from playwright.async_api import Page

from mcr_capture_worker.models.meeting_model import Meeting, MeetingPlatform
from mcr_capture_worker.services.meeting_monitors.abstract_meeting_monitor import (
    MeetingMonitor,
)
from mcr_capture_worker.services.meeting_monitors.comu_monitor import (
    ComuMeetingMonitor,
)
from mcr_capture_worker.services.meeting_monitors.visio_monitor import (
    VisioMeetingMonitor,
)
from mcr_capture_worker.services.meeting_monitors.webconf_monitor import (
    WebConfMeetingMonitor,
)
from mcr_capture_worker.services.meeting_monitors.webex_monitor import (
    WebexMeetingMonitor,
)
from mcr_capture_worker.services.meeting_monitors.webinaire_monitor import (
    WebinaireMeetingMonitor,
)


def build_meeting_monitor(meeting: Meeting, page: Page) -> MeetingMonitor:
    """Build the monitor for a meeting."""
    match meeting.name_platform:
        case MeetingPlatform.VISIO:
            return VisioMeetingMonitor(page)
        case MeetingPlatform.COMU:
            return ComuMeetingMonitor(page)
        case MeetingPlatform.WEBCONF:
            return WebConfMeetingMonitor(page)
        case MeetingPlatform.WEBINAIRE:
            return WebinaireMeetingMonitor(page)
        case MeetingPlatform.WEBEX:
            return WebexMeetingMonitor(page)
