import mcr_meeting.app.infrastructure.redis as redis_store
from tests.mocks.in_memory_redis import InMemoryRedis


def test_first_increment_starts_a_fresh_counter(
    in_memory_redis: InMemoryRedis,
) -> None:
    assert redis_store.increment_transcription_attempt("task-a") == 1
    assert redis_store.increment_transcription_attempt("task-a") == 2


def test_counters_are_isolated_per_task_id(in_memory_redis: InMemoryRedis) -> None:
    redis_store.increment_transcription_attempt("task-a")

    assert redis_store.increment_transcription_attempt("task-b") == 1


def test_counter_expires_so_a_stale_key_never_blocks_a_future_dispatch(
    in_memory_redis: InMemoryRedis,
) -> None:
    redis_store.increment_transcription_attempt("task-a")

    assert in_memory_redis.ttl("transcription_attempts:task-a") > 0
