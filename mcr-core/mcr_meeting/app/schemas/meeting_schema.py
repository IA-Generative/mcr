import re
from datetime import datetime, timezone
from typing import Optional, Self
from urllib.parse import urlparse, urlunparse

from pydantic import (
    BaseModel,
    ConfigDict,
    field_serializer,
    field_validator,
    model_validator,
)

from mcr_meeting.app.models import MeetingPlatforms, MeetingStatus


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
    url: Optional[str] = None
    name_platform: MeetingPlatforms
    creation_date: datetime
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    meeting_password: Optional[str] = None
    meeting_platform_id: Optional[str] = None

    @model_validator(mode="after")
    def validate_url_based_on_platform(self) -> Self:
        """Validate the URL based on the specified platform.

        This validator checks that the connexion information (url or password and identifier)
        provided for a meeting matches the expected format based on the `name_platform`.
        Different platforms may have different URL formats, and this validator ensures that
        the connexion information conforms to the platform-specific format.

        Args:
            values (MeetingBase): The MeetingBase object containing the fields to validate.

        Returns:
            MeetingBase: The validated MeetingBase object.

        """
        name_platform = self.name_platform

        platform_validators = {
            MeetingPlatforms.COMU: validate_comu_meeting,
            MeetingPlatforms.WEBINAIRE: validate_webinaire_meeting,
            MeetingPlatforms.WEBCONF: validate_webconf_meeting,
            MeetingPlatforms.VISIO: validate_visio_meeting,
            MeetingPlatforms.MCR_IMPORT: no_validation,
            MeetingPlatforms.MCR_RECORD: no_validation,
        }

        validation_function = platform_validators[name_platform]
        validation_function(self)

        if self.name_platform == MeetingPlatforms.COMU:
            rewrite_comu_url_to_use_public_url(self)

        return self

    @field_serializer("creation_date")
    def serialize_creation_date(self, ts: datetime) -> str:
        return ts.strftime("%Y-%m-%dT%H:%M:%S.%f")[:23] + "Z"

    model_config = ConfigDict(
        from_attributes=True,
    )


class MeetingCreate(MeetingBase):
    status: MeetingStatus = MeetingStatus.NONE


class MeetingUpdate(MeetingBase):
    """
    Model for updating meeting details.
    """

    pass


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


def validate_comu_meeting(values: MeetingBase) -> None:
    """Validates the values of a MeetingBase object for a COMU meeting platform.
    Args:
        values (MeetingBase): The values to be validated.
    Raises:
        ValueError: If the URL, meeting password, or meeting ID are in an invalid format.
    """
    comu_url_validator = ComuUrlValidator()

    if values.url is not None:
        if not comu_url_validator.validate_url(values.url):
            raise ValueError(f"Invalid URL format for platform {values.name_platform}")
        return None
    elif (values.meeting_password is not None) and (
        values.meeting_platform_id is not None
    ):
        if (
            not values.meeting_password.isdigit()
            or not 6 <= len(values.meeting_password) <= 8
        ):
            raise ValueError(
                f"Invalid password format for platform {values.name_platform}"
            )
        if (
            not values.meeting_platform_id.isdigit()
            or len(values.meeting_platform_id) <= 3
        ):
            raise ValueError(
                f"Invalid meeting identifier format for platform {values.name_platform}"
            )
    else:
        raise ValueError("No connection information provided")


def validate_webinaire_meeting(values: MeetingBase) -> None:
    """Validates the values of a MeetingBase object for a COMU meeting platform.
    Args:
        values (MeetingBase): The values to be validated.
    Raises:
        ValueError: If the URL is in an invalid format."""
    pattern = re.compile(
        r"^https:\/\/webinaire\.numerique\.gouv\.fr\/meeting\/signin\/moderateur\/\d+\/creator\/\d+\/hash\/[a-f0-9]{40}$"
    )
    if (values.url is None) or not (pattern.match(values.url)):
        raise ValueError(f"Invalid URL format for platform {values.name_platform}")


def validate_webconf_meeting(values: MeetingBase) -> None:
    """Validates the values of a MeetingBase object for a WEBCONF meeting platform.
    Args:
        values (MeetingBase): The values to be validated.
    Raises:
        ValueError: If the URL is in an invalid format."""
    webconf_url_validator = WebConfUrlValidator()
    if values.url:
        if not webconf_url_validator.validate_url(values.url):
            raise ValueError(f"Invalid URL format for platform {values.name_platform}")
        return None
    else:
        raise ValueError("No connection information provided")


def validate_visio_meeting(values: MeetingBase) -> None:
    """Validates the values of a MeetingBase object for a VISIO meeting platform.
    Args:
        values (MeetingBase): The values to be validated.
    Raises:
        ValueError: If the URL is in an invalid format."""
    visio_url_validator = VisioUrlValidator()
    if values.url:
        if not visio_url_validator.validate_url(values.url):
            raise ValueError(f"Invalid URL format for platform {values.name_platform}")
        return None
    else:
        raise ValueError("No connection information provided")


def no_validation(values: MeetingBase) -> None:
    """No validation is performed for this platform."""
    return None


class MeetingWithPresignedUrl(BaseModel):
    """
    Schema for a meeting with a presigned URL.

    Attributes:
        meeting (Meeting): The meeting details.
        presigned_url (str): The presigned URL for accessing the meeting.
    """

    meeting: MeetingResponse
    presigned_url: str


class ComuUrlValidator:
    domains = [
        re.compile(r"webconf\.comu\.gouv\.fr"),
        re.compile(r"webconf\.comu\.interieur\.rie\.gouv\.fr"),
        re.compile(r"webconf\.comu\.minint\.fr"),
    ]
    secret = re.compile(r"\?secret=[A-Za-z0-9_.]{22}")
    meeting_id = re.compile(r"\d+")
    maybe_language_code = re.compile(r"(\/[a-z]{2}-[A-Z]{2})?")

    @property
    def domain_pattern(self) -> str:
        return f"({'|'.join(r.pattern for r in self.domains)})"

    @property
    def url_regex(self) -> re.Pattern[str]:
        return re.compile(
            rf"^https://{self.domain_pattern}{self.maybe_language_code.pattern}/meeting/{self.meeting_id.pattern}{self.secret.pattern}$"
        )

    def validate_url(self, url: str) -> bool:
        return bool(self.url_regex.match(url))


class WebinaireUrlValidator:
    domain = re.compile(r"webinaire\.numerique\.gouv\.fr")
    user_id = re.compile(r"\d+")
    creator_id = re.compile(r"\d+")
    hash = re.compile(r"[a-f0-9]{40}")

    @property
    def url_regex(self) -> re.Pattern[str]:
        return re.compile(
            rf"^https://{self.domain.pattern}/meeting/signin/moderateur/{self.user_id.pattern}/creator/{self.creator_id.pattern}/hash/{self.hash.pattern}$"
        )

    def validate_url(self, url: str) -> bool:
        return bool(self.url_regex.match(url))


class WebConfUrlValidator:
    domain = re.compile(r"webconf\.numerique\.gouv\.fr")
    meeting_name = re.compile(r"(?=(?:.*\d){3,})[A-Za-z0-9]{10,}")

    @property
    def url_regex(self) -> re.Pattern[str]:
        return re.compile(
            rf"^https://{self.domain.pattern}/{self.meeting_name.pattern}$"
        )

    def validate_url(self, url: str) -> bool:
        return bool(self.url_regex.match(url))


class VisioUrlValidator:
    domain = re.compile(r"visio\.numerique\.gouv\.fr")
    slug = re.compile(r"[a-z]{3}-[a-z]{4}-[a-z]{3}")

    @property
    def url_regex(self) -> re.Pattern[str]:
        return re.compile(rf"^https://{self.domain.pattern}/{self.slug.pattern}$")

    def validate_url(self, url: str) -> bool:
        return bool(self.url_regex.match(url))


def rewrite_comu_url_to_use_public_url(meeting: MeetingBase) -> MeetingBase:
    if meeting.url is None:
        return meeting

    parsed_url = urlparse(meeting.url)
    new_host = "webconf.comu.gouv.fr"

    meeting.url = str(urlunparse(parsed_url._replace(netloc=new_host)))

    return meeting
