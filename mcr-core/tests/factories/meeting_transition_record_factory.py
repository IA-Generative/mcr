from datetime import datetime, timedelta, timezone

import factory
from factory import LazyAttribute, LazyFunction

from mcr_meeting.app.models.meeting_model import MeetingStatus
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord

from .base import BaseFactory
from .meeting_factory import MeetingFactory


def _get_or_create_meeting_id() -> int:
    """Create a meeting and return its ID."""
    meeting = MeetingFactory.create()
    return meeting.id


class MeetingTransitionRecordFactory(BaseFactory[MeetingTransitionRecord]):
    """
    Factory for creating MeetingTransitionRecord instances with realistic test data.

    By default, creates a transition record with NONE status.
    Automatically creates a meeting unless specified.

    Examples:
        record = MeetingTransitionRecordFactory()
        record = MeetingTransitionRecordFactory(meeting_id=existing_meeting.id)
        record = MeetingTransitionRecordFactory(with_prediction=True)
        record = MeetingTransitionRecordFactory(transcription_pending=True)
    """

    class Meta:
        model = MeetingTransitionRecord

    timestamp = LazyAttribute(lambda _: datetime.now(timezone.utc))
    predicted_date_of_next_transition = None
    status = MeetingStatus.NONE
    meeting_id = LazyFunction(_get_or_create_meeting_id)

    class Params:
        # Trait for records with prediction
        with_prediction = factory.Trait(
            predicted_date_of_next_transition=LazyAttribute(
                lambda obj: obj.timestamp + timedelta(minutes=30)
            ),
        )

        # Trait for transcription pending status
        transcription_pending = factory.Trait(
            status=MeetingStatus.TRANSCRIPTION_PENDING,
            predicted_date_of_next_transition=LazyAttribute(
                lambda obj: obj.timestamp + timedelta(minutes=15)
            ),
        )

        # Trait for transcription in progress status
        transcription_in_progress = factory.Trait(
            status=MeetingStatus.TRANSCRIPTION_IN_PROGRESS,
            predicted_date_of_next_transition=LazyAttribute(
                lambda obj: obj.timestamp + timedelta(minutes=10)
            ),
        )
