import re
from collections.abc import Callable
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from mcr_meeting.app.models import MeetingPlatforms


class PlatformConnectionInfoValidator(BaseModel):
    name_platform: MeetingPlatforms | None = None
    url: str | None = None
    meeting_password: str | None = None
    meeting_platform_id: str | None = None

    @model_validator(mode="after")
    def validate_platform_connection(self) -> Self:
        validators: dict[
            MeetingPlatforms | None, Callable[[PlatformConnectionInfoValidator], None]
        ] = {
            MeetingPlatforms.COMU: validate_comu_connection,
            MeetingPlatforms.WEBINAIRE: validate_webinaire_connection,
            MeetingPlatforms.WEBCONF: validate_webconf_connection,
            MeetingPlatforms.VISIO: validate_visio_connection,
            MeetingPlatforms.WEBEX: validate_webex_connection,
            MeetingPlatforms.MCR_IMPORT: validate_no_connection_info,
            MeetingPlatforms.MCR_RECORD: validate_no_connection_info,
            None: validate_no_connection_info,
        }
        validators[self.name_platform](self)
        return self

    model_config = ConfigDict(from_attributes=True)


def validate_comu_connection(values: PlatformConnectionInfoValidator) -> None:
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


def validate_webinaire_connection(values: PlatformConnectionInfoValidator) -> None:
    if values.meeting_password is not None or values.meeting_platform_id is not None:
        raise ValueError(
            f"meeting_password and meeting_platform_id are not supported for platform {values.name_platform}"
        )
    pattern = re.compile(
        r"^https:\/\/webinaire\.numerique\.gouv\.fr\/meeting\/signin\/moderateur\/\d+\/creator\/\d+\/hash\/[a-f0-9]{40}$"
    )
    if values.url is None or not pattern.match(values.url):
        raise ValueError(f"Invalid URL format for platform {values.name_platform}")


def validate_webconf_connection(values: PlatformConnectionInfoValidator) -> None:
    if values.meeting_password is not None or values.meeting_platform_id is not None:
        raise ValueError(
            f"meeting_password and meeting_platform_id are not supported for platform {values.name_platform}"
        )
    if not values.url:
        raise ValueError("No connection information provided")
    if not WebConfUrlValidator().validate_url(values.url):
        raise ValueError(f"Invalid URL format for platform {values.name_platform}")


def validate_visio_connection(values: PlatformConnectionInfoValidator) -> None:
    if values.meeting_password is not None:
        raise ValueError(
            f"meeting_password is not supported for platform {values.name_platform}"
        )
    if not values.url:
        raise ValueError("No connection information provided")
    if not VisioUrlValidator().validate_url(values.url):
        raise ValueError(f"Invalid URL format for platform {values.name_platform}")


def validate_webex_connection(values: PlatformConnectionInfoValidator) -> None:
    if values.meeting_password is not None or values.meeting_platform_id is not None:
        raise ValueError(
            f"meeting_password and meeting_platform_id are not supported for platform {values.name_platform}"
        )
    if not values.url:
        raise ValueError("No connection information provided")
    if not WebexUrlValidator().validate_url(values.url):
        raise ValueError(f"Invalid URL format for platform {values.name_platform}")


def validate_no_connection_info(values: PlatformConnectionInfoValidator) -> None:
    if (
        values.url is not None
        or values.meeting_password is not None
        or values.meeting_platform_id is not None
    ):
        raise ValueError(
            "url, meeting_password et meeting_platform_id are not supported for this platform"
        )


class ComuUrlValidator:
    domains = [
        re.compile(r"webconf\.comu\.gouv\.fr"),
        re.compile(r"webconf\.comu\.interieur\.rie\.gouv\.fr"),
        re.compile(r"webconf\.comu\.minint\.fr"),
        re.compile(r"webconf\.comu\.din\.gouv\.fr"),
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


class WebexUrlValidator:
    domain = re.compile(r"[A-Za-z0-9-]+\.webex\.com")
    slug = re.compile(r"[A-Za-z0-9._-]{1,64}")

    @property
    def url_regex(self) -> re.Pattern[str]:
        return re.compile(rf"^https://{self.domain.pattern}/meet/{self.slug.pattern}$")

    def validate_url(self, url: str) -> bool:
        return bool(self.url_regex.match(url))
