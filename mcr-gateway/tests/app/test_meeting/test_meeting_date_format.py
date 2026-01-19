from datetime import datetime

import pytest

from mcr_gateway.app.schemas.meeting_schema import Meeting, MeetingStatus


@pytest.mark.parametrize(
    "dt,expected_json",
    [
        (
            datetime(2024, 1, 1, 12, 30, 45, 123456),
            "2024-01-01T12:30:45.123Z",
        ),
        (
            datetime(2025, 7, 31, 23, 59, 59, 999999),  # Last second of the day
            "2025-07-31T23:59:59.999Z",
        ),
        (
            datetime(2023, 8, 1, 0, 0, 0, 0),  # Midnight
            "2023-08-01T00:00:00.000Z",
        ),
    ],
)
def test_datetime_serialization_fixed(
    dt: datetime, expected_json: dict[str, str]
) -> None:
    model = Meeting(
        id=1,
        status=MeetingStatus.NONE,
        name="test",
        name_platform="MCR_IMPORT",
        creation_date=dt,
    )
    serialized = model.model_dump()
    assert serialized["creation_date"] == expected_json
