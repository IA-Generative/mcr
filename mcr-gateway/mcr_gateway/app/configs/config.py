from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Configuration settings for the application.

    Attributes:
        MEETING_SERVICE_URL (str): The base URL for the meeting service.
        USER_SERVICE_URL (str): The base URL for the user service.
        MEMBER_SERVICE_URL (str): The base URL for the member service.
    """

    CORE_SERVICE_BASE_URL: str

    @property
    def MEETING_SERVICE_URL(self) -> str:
        return f"{self.CORE_SERVICE_BASE_URL}/api/meetings/"

    @property
    def USER_SERVICE_URL(self) -> str:
        return f"{self.CORE_SERVICE_BASE_URL}/api/user/"

    @property
    def MEMBER_SERVICE_URL(self) -> str:
        return f"{self.CORE_SERVICE_BASE_URL}/api/members/"

    @property
    def NOTIFICATION_SERVICE_URL(self) -> str:
        return f"{self.CORE_SERVICE_BASE_URL}/api/notifications/"

    COMU_LOOKUP_URL: str = Field(default="https://webconf.comu.gouv.fr/api/lookup")
    KEYCLOAK_URL: str
    KEYCLOAK_REALM: str
    KEYCLOAK_CLIENT_ID: str

    @property
    def KEYCLOAK_TOKEN_URL(self) -> str:
        return f"{self.KEYCLOAK_URL}/realms/{self.KEYCLOAK_REALM}/protocol/openid-connect/token"

    ENV_MODE: str = "PROD"


class LoggingSettings(BaseSettings):
    COLORIZE: bool = Field(default=False, description="Should log output be colored")
    LEVEL: int | str = Field(default="INFO")
    DISPLAY_REQUEST_ID: bool = Field(
        default=True, description="Should display request id in logs"
    )
    DISPLAY_TIMESTAMP: bool = Field(
        default=False, description="Should display log timestamp"
    )


settings = Settings()
