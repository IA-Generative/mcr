import factory
from factory import Faker, LazyAttribute, Sequence, SubFactory

from mcr_meeting.app.models.transcription_model import Transcription

from .base import BaseFactory
from .meeting_factory import MeetingFactory


class TranscriptionFactory(BaseFactory[Transcription]):
    """
    Factory for creating Transcription instances with realistic test data.

    By default, creates a transcription with auto-incrementing index.
    Automatically creates a meeting unless specified.

    Examples:
        transcription = TranscriptionFactory()
        transcription = TranscriptionFactory(meeting=existing_meeting)
        transcription = TranscriptionFactory.short_text()
        batch = TranscriptionFactory.create_batch(5, meeting=meeting)
    """

    class Meta:
        model = Transcription

    transcription_index = Sequence(lambda n: n)
    speaker = Faker("name")
    transcription = Faker("paragraph", nb_sentences=5)

    # Automatically create a meeting
    meeting = SubFactory(MeetingFactory)
    meeting_id = LazyAttribute(lambda obj: obj.meeting.id)

    class Params:
        # Trait for short transcription text
        short_text = factory.Trait(
            transcription=Faker("sentence", nb_words=10),
        )

        # Trait for long transcription text
        long_text = factory.Trait(
            transcription=Faker("paragraph", nb_sentences=20),
        )
