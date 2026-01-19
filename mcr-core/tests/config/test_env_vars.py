from pydantic_settings import BaseSettings

from mcr_meeting.app.configs.base import (
    ApiSettings,
    CelerySettings,
    DBSettings,
    S3Settings,
    SentrySettings,
    Settings,
)


def test_settings() -> None:
    """
    This test is mainly aimed at the CI. It validates that all env vars / settings are set properly.
    If it fails, chances are they are not set on the helm deployment. Changes must then be made on `mirai-infra/mcr/Values.yaml`
    (for values identical on all envs) or `mirai-value/mcr/values-{env}.yaml` for env specific values
    """
    for settings_cls in [
        DBSettings,
        Settings,
        S3Settings,
        ApiSettings,
        CelerySettings,
        SentrySettings,
    ]:
        # This will fail if env vars are not set in env
        settings_obj = settings_cls()
        assert_env_var_are_not_empty_str(settings_obj)


def assert_env_var_are_not_empty_str(settings_obj: BaseSettings) -> None:
    for field, value in settings_obj.__dict__.items():
        # Only check str fields
        if isinstance(value, str):
            assert value != "", (
                f"{settings_obj.__class__.__name__}.{field} is not set in the env"
            )
