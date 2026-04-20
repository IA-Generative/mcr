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
from mcr_capture_worker.services.connection_strategies.webinaire_connection import (
    WebinaireConnectionStrategy,
)


def build_connection_strategy(meeting: Meeting) -> ConnectionStrategy:
    """Build the Playwright-based connection strategy for a meeting.

    Raises ValueError for Webex, which uses the Node subprocess path instead.
    """
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
            raise ValueError(
                "Webex has no Playwright strategy; use the Node subprocess path"
            )
