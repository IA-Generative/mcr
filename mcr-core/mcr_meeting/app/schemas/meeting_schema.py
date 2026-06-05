import re
from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Self
from urllib.parse import urlparse, urlunparse

from pydantic import (
    BaseModel,
    ConfigDict,
    computed_field,
    field_serializer,
    field_validator,
    model_validator,
)

from mcr_meeting.app.models import (
    DeliverableStatus,
    DeliverableType,
    Meeting,
    MeetingPlatforms,
    MeetingStatus,
)
from mcr_meeting.app.schemas.platform_connection_validator_schema import (
    PlatformConnectionInfoValidator,
)


class PaginatedMeetings(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    items: list[Meeting]
    total: int


class PaginatedMeetingsResult(PaginatedMeetings):
    page: int
    total_pages: int


class MeetingAudioStream(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    iterator: Iterator[bytes]
    media_type: str


class MeetingBase(BaseModel):
    """
    Base schema for a meeting.

    Attributes:
        name (str): The name of the meeting.
        url (Optional[str]): The URL for the meeting (if applicable).
        name_platform (str): The name of the platform used for the meeting.
        creation_date (datetime): The creation date and time of the meeting.
        start_date (datetime): The start date and time of the meeting.
        end_date (datetime): The end date and time of the meeting.
        meeting_password (Optional[str]): The password for the meeting (if required).
        meeting_platform_id (Optional[str]): The platform-specific identifier for the meeting.
    """

    name: str
    url: str | None = None
    name_platform: MeetingPlatforms
    creation_date: datetime
    start_date: datetime | None = None
    end_date: datetime | None = None
    meeting_password: str | None = None
    meeting_platform_id: str | None = None
    notes: str | None = None

    @field_serializer("creation_date", when_used="json")
    def serialize_creation_date(self, ts: datetime) -> str:
        return ts.strftime("%Y-%m-%dT%H:%M:%S.%f")[:23] + "Z"

    model_config = ConfigDict(
        from_attributes=True,
    )


class MeetingWriteBase(MeetingBase):
    """Base for write schemas (Create, Update): enforces platform/url consistency."""

    @model_validator(mode="after")
    def validate_url_based_on_platform(self) -> Self:
        """Validate the URL based on the specified platform.

        This validator checks that the connexion information (url or password and identifier)
        provided for a meeting matches the expected format based on the `name_platform`.
        Different platforms may have different URL formats, and this validator ensures that
        the connexion information conforms to the platform-specific format.
        """

        PlatformConnectionInfoValidator(
            name_platform=self.name_platform,
            url=self.url,
            meeting_password=self.meeting_password,
            meeting_platform_id=self.meeting_platform_id,
        )
        if self.name_platform == MeetingPlatforms.COMU:
            rewrite_comu_url_to_use_public_url(self)
        return self


class MeetingCreate(MeetingWriteBase):
    status: MeetingStatus = MeetingStatus.NONE


class MeetingUpdate(MeetingWriteBase):
    """
    Schema for a meeting update.

    It overrides attributes to allow patch endpoint.
    """

    # As we overide the fields, we need # type: ignore[assignment] for Mypy to stay quiet
    name: str | None = None  # type: ignore[assignment]
    name_platform: MeetingPlatforms | None = None  # type: ignore[assignment]
    creation_date: datetime | None = None  # type: ignore[assignment]


class PaginatedMeetingsResponse(BaseModel):
    total_items: int
    total_pages: int
    page: int
    data: list["MeetingResponse"]


class MeetingResponse(MeetingBase):
    """
    Full model for meeting details.

    Attributes:
        id (int): Unique meeting identifier.
        name (str): Name of the meeting.
        url (Optional[str]): Meeting URL.
        name_platform (str): Platform hosting the meeting.
        meeting_password (Optional[str]): Meeting password.
        meeting_platform_id (Optional[str]): Platform-specific meeting identifier.
        creation_date (datetime): UTC creation time of the meeting.
        start_date (datetime): UTC start time of the meeting.
        end_date (datetime): UTC end time of the meeting.
        status (MeetingStatus): Current status of the meeting.
    """

    id: int
    status: MeetingStatus

    @field_validator("creation_date")
    @classmethod
    def set_utc_creation(cls, value: datetime) -> datetime:
        """
        Ensure datetime values are in UTC.

        Args:
            value (datetime): The datetime value to validate.

        Returns:
            datetime: The datetime value in UTC.
        """
        if value.tzinfo is None:
            # Si la date est naïve, on ajoute UTC
            return value.replace(tzinfo=timezone.utc)
        # Si la date a une timezone, on la convertit en UTC
        return value.astimezone(timezone.utc)

    @field_validator("start_date")
    @classmethod
    def set_utc_start(cls, value: datetime | None) -> datetime | None:
        """
        Ensure datetime values are in UTC.

        Args:
            value (datetime): The datetime value to validate.

        Returns:
            datetime: The datetime value in UTC.
        """
        if value is None:
            return value
        if value.tzinfo is None:
            # Si la date est naïve, on ajoute UTC
            return value.replace(tzinfo=timezone.utc)
        # Si la date a une timezone, on la convertit en UTC
        return value.astimezone(timezone.utc)

    @field_validator("end_date")
    @classmethod
    def set_utc_end(cls, value: datetime | None) -> datetime | None:
        """
        Ensure datetime values are in UTC.

        Args:
            value (datetime): The datetime value to validate.

        Returns:
            datetime: The datetime value in UTC.
        """
        if value is None:
            return value
        if value.tzinfo is None:
            # Si la date est naïve, on ajoute UTC
            return value.replace(tzinfo=timezone.utc)
        # Si la date a une timezone, on la convertit en UTC
        return value.astimezone(timezone.utc)


def rewrite_comu_url_to_use_public_url(meeting: MeetingBase) -> MeetingBase:
    if meeting.url is None:
        return meeting

    parsed_url = urlparse(meeting.url)
    new_host = "webconf.comu.gouv.fr"
    new_path = re.sub(r"^/[a-z]{2}-[A-Z]{2}", "", parsed_url.path)

    meeting.url = str(urlunparse(parsed_url._replace(netloc=new_host, path=new_path)))

    return meeting


class DeliverableResponse(BaseModel):
    type: DeliverableType
    status: DeliverableStatus
    external_url: str | None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def file_type(self) -> DeliverableType:
        # Legacy alias kept until the v2 frontend (Step 4) replaces the old one.
        return self.type


class MeetingDetailResponse(MeetingResponse):
    deliverables: list[DeliverableResponse] = []
