import pytest

from mcr_meeting.app.domain.feedback import extract_meeting_id_from_url


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://app.example.com/meetings/42", 42),
        ("https://app.example.com/meetings/42?secret=abc", 42),
        ("https://app.example.com/meetings/7/details", 7),
        ("https://app.example.com/", None),
        ("https://app.example.com/meetings/", None),
        ("https://app.example.com/meetings/abc", None),
        ("not-a-url", None),
    ],
)
def test_extract_meeting_id_from_url(url: str, expected: int | None) -> None:
    assert extract_meeting_id_from_url(url) == expected
