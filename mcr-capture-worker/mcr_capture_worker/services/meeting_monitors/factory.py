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
from mcr_capture_worker.services.meeting_monitors.webex_node_monitor import (
    WebexNodeMeetingMonitor,
)
from mcr_capture_worker.services.meeting_monitors.webinaire_monitor import (
    WebinaireMeetingMonitor,
)


def build_meeting_monitor(meeting: Meeting, page: Page | None) -> MeetingMonitor:
    """Build the monitor for a meeting.

    Playwright-based platforms require a Page; Webex (Node subprocess) does not.
    """
    match meeting.name_platform:
        case MeetingPlatform.VISIO:
            assert page is not None, "Visio requires a Playwright page"
            return VisioMeetingMonitor(page)
        case MeetingPlatform.COMU:
            assert page is not None, "Comu requires a Playwright page"
            return ComuMeetingMonitor(page)
        case MeetingPlatform.WEBCONF:
            assert page is not None, "WebConf requires a Playwright page"
            return WebConfMeetingMonitor(page)
        case MeetingPlatform.WEBINAIRE:
            assert page is not None, "Webinaire requires a Playwright page"
            return WebinaireMeetingMonitor(page)
        case MeetingPlatform.WEBEX:
            return WebexNodeMeetingMonitor()
