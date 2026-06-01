import math
from dataclasses import dataclass

from pydantic import UUID4

from mcr_meeting.app.db.meeting_repository import get_meetings
from mcr_meeting.app.db.user_repository import get_user_by_keycloak_uuid
from mcr_meeting.app.models import Meeting


@dataclass
class PaginatedMeetingsResult:
    items: list[Meeting]
    total: int
    page: int
    total_pages: int


def list_meetings(
    user_keycloak_uuid: UUID4,
    search: str | None,
    page: int,
    page_size: int,
) -> PaginatedMeetingsResult:
    page = max(1, page)
    page_size = page_size if page_size > 0 else 1

    user = get_user_by_keycloak_uuid(user_keycloak_uuid)
    paginated = get_meetings(
        user_id=user.id, search=search, page=page, page_size=page_size
    )

    total_pages = max(1, math.ceil(paginated.total / page_size))
    return PaginatedMeetingsResult(
        items=paginated.items,
        total=paginated.total,
        page=page,
        total_pages=total_pages,
    )
