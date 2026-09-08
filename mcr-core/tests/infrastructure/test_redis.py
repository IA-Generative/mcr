import mcr_meeting.app.infrastructure.redis as redis_store
from tests.mocks.in_memory_redis import InMemoryRedis


def test_attempt_counter_is_keyed_by_task_id_and_expires(
    in_memory_redis: InMemoryRedis,
) -> None:
    assert redis_store.increment_transcription_attempt("task-a") == 1

    assert in_memory_redis.store["transcription_attempts:task-a"] == "1"
    assert in_memory_redis.expiries["transcription_attempts:task-a"] == 604_800
