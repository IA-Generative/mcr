import redis
from loguru import logger

from mcr_meeting.app.configs.base import CelerySettings

_settings = CelerySettings()

_client: redis.Redis = redis.Redis(
    host=_settings.REDIS_HOST,
    port=_settings.REDIS_PORT,
    db=_settings.REDIS_TOKEN_STORE_DB,
    decode_responses=True,
)


def _key(user_sub: str) -> str:
    return f"drive_token:{user_sub}"


def save_refresh_token(user_sub: str, refresh_token: str) -> None:
    _client.set(_key(user_sub), refresh_token, ex=_settings.REDIS_TOKEN_TTL_SECONDS)
    logger.debug("Stored refresh token for user {}", user_sub)


def get_refresh_token(user_sub: str) -> str | None:
    return _client.get(_key(user_sub))  # type: ignore[return-value]


def delete_refresh_token(user_sub: str) -> None:
    _client.delete(_key(user_sub))
