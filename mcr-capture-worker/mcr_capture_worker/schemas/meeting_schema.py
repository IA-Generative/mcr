from typing import Protocol

from typing_extensions import TypeGuard

from mcr_capture_worker.models.meeting_model import Meeting


class IMeetingWithUrl(Protocol):
    url: str
    meeting_password: None = None
    meeting_platform_id: None = None


class IMeetingWithPlatformAndPassword(Protocol):
    url: None = None
    meeting_password: str
    meeting_platform_id: str


def is_meeting_with_url(meeting: Meeting) -> TypeGuard["IMeetingWithUrl"]:
    return meeting.url is not None


def is_meeting_with_password(
    meeting: Meeting,
) -> TypeGuard["IMeetingWithPlatformAndPassword"]:
    return meeting.url is None and meeting.meeting_password is not None
