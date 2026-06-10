from mcr_meeting.app.infrastructure.redis import get_refresh_token
from mcr_meeting.app.use_cases.ensure_offline_token import ensure_offline_token
from tests.mocks.in_memory_keycloak import InMemoryKeycloak
from tests.mocks.in_memory_redis import InMemoryRedis


def test_refresh_token_is_stored_when_user_starts_transcription(
    in_memory_redis: InMemoryRedis, in_memory_keycloak: InMemoryKeycloak
) -> None:
    in_memory_keycloak.exchange_refresh_token = "offline-refresh-token"

    ensure_offline_token("user-uuid-123", "access-token-abc")

    assert get_refresh_token("user-uuid-123") == "offline-refresh-token"


def test_ensure_offline_token_does_nothing_without_access_token() -> None:
    ensure_offline_token("user-uuid-123", None)


def test_token_exchange_failure_does_not_raise(
    in_memory_keycloak: InMemoryKeycloak,
) -> None:
    in_memory_keycloak.should_fail_exchange = True

    ensure_offline_token("user-uuid-123", "access-token-abc")
