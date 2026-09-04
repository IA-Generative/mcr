import pytest
from pytest_mock import MockerFixture

import mcr_meeting.app.use_cases.transcription.register_redelivery as uc
from mcr_meeting.app.exceptions.exceptions import TranscriptionAttemptsExhaustedError
from tests.mocks.in_memory_redis import InMemoryRedis

TASK_ID = "task-1"
MEETING_ID = 123
TASK_NAME = "mcr_transcription.diarize"
KEY = f"transcription_attempts:{TASK_ID}"


def _register(redelivered: bool, task_id: str = TASK_ID) -> None:
    uc.register_redelivery(task_id, MEETING_ID, TASK_NAME, redelivered=redelivered)


def test_first_delivery_is_not_an_attempt(in_memory_redis: InMemoryRedis) -> None:
    _register(redelivered=False)

    assert not in_memory_redis.exists(KEY)


def test_redeliveries_within_budget_let_the_task_run(
    in_memory_redis: InMemoryRedis,
) -> None:
    _register(redelivered=True)
    _register(redelivered=True)

    assert in_memory_redis.get(KEY) == "2"


def test_redelivery_beyond_budget_fails_the_task(
    in_memory_redis: InMemoryRedis,
) -> None:
    _register(redelivered=True)
    _register(redelivered=True)

    with pytest.raises(TranscriptionAttemptsExhaustedError):
        _register(redelivered=True)


def test_a_new_dispatch_starts_from_zero(in_memory_redis: InMemoryRedis) -> None:
    for _ in range(2):
        _register(redelivered=True)

    _register(redelivered=True, task_id="task-2")


def test_redis_outage_lets_the_task_run(
    in_memory_redis: InMemoryRedis, mocker: MockerFixture
) -> None:
    mocker.patch.object(
        in_memory_redis, "incr", side_effect=ConnectionError("redis down")
    )

    _register(redelivered=True)
