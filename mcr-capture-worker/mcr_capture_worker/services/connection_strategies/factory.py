from mcr_capture_worker.models.meeting_model import Meeting, MeetingPlatform
from mcr_capture_worker.services.connection_strategies.abstract_connection import (
    ConnectionStrategy,
)
from mcr_capture_worker.services.connection_strategies.comu_connection import (
    ComuConnectionStrategy,
)
from mcr_capture_worker.services.connection_strategies.visio_connection import (
    VisioStrategy,
)
from mcr_capture_worker.services.connection_strategies.webconf_connection import (
    WebConfConnectionStrategy,
)
from mcr_capture_worker.services.connection_strategies.webex_connection import (
    WebexStrategy,
)
from mcr_capture_worker.services.connection_strategies.webinaire_connection import (
    WebinaireConnectionStrategy,
)


def build_connection_strategy(meeting: Meeting) -> ConnectionStrategy:
    """Build the Playwright-based connection strategy for a meeting."""
    match meeting.name_platform:
        case MeetingPlatform.VISIO:
            return VisioStrategy()
        case MeetingPlatform.COMU:
            return ComuConnectionStrategy()
        case MeetingPlatform.WEBCONF:
            return WebConfConnectionStrategy()
        case MeetingPlatform.WEBINAIRE:
            return WebinaireConnectionStrategy()
        case MeetingPlatform.WEBEX:
            return WebexStrategy()
