from datetime import datetime, timedelta, timezone

import factory
from factory import Faker, LazyAttribute, SubFactory

from mcr_meeting.app.models.meeting_model import (
    Meeting,
    MeetingPlatforms,
    MeetingStatus,
)

from .base import BaseFactory
from .user_factory import UserFactory


class MeetingFactory(BaseFactory[Meeting]):
    """
    Factory for creating Meeting instances with realistic test data.

    By default, creates a COMU meeting with NONE status.
    Automatically creates an owner user unless specified.

    Examples:
        meeting = MeetingFactory()
        meeting = MeetingFactory(status=MeetingStatus.CAPTURE_DONE)
        meeting = MeetingFactory.import_meeting()
        meeting = MeetingFactory.with_dates()
        meeting = MeetingFactory(owner=existing_user)
    """

    class Meta:
        model = Meeting

    name = Faker("catch_phrase")
    url = Faker("url")
    name_platform = MeetingPlatforms.COMU
    creation_date = LazyAttribute(lambda _: datetime.now(timezone.utc))
    start_date = None
    end_date = None
    status = MeetingStatus.NONE
    transcription_filename = None
    report_filename = None
    meeting_platform_id = Faker("uuid4")
    meeting_password = Faker("password", length=6)

    # Automatically create a user as the owner
    owner = SubFactory(UserFactory)
    user_id = LazyAttribute(lambda obj: obj.owner.id)

    class Params:
        # Trait for import meetings
        import_meeting = factory.Trait(
            name_platform=MeetingPlatforms.MCR_IMPORT,
            url=None,
            meeting_platform_id=None,
        )

        # Trait for record meetings
        record_meeting = factory.Trait(
            name_platform=MeetingPlatforms.MCR_RECORD,
            url=None,
            meeting_platform_id=None,
        )

        # Trait for meetings with dates set
        with_dates = factory.Trait(
            start_date=LazyAttribute(
                lambda obj: obj.creation_date + timedelta(hours=1)
                if obj.creation_date
                else datetime.now(timezone.utc) + timedelta(hours=1)
            ),
            end_date=LazyAttribute(
                lambda obj: obj.start_date + timedelta(hours=1)
                if obj.start_date
                else datetime.now(timezone.utc) + timedelta(hours=2)
            ),
        )

        # Trait for meetings with transcription file
        with_transcription = factory.Trait(
            transcription_filename="transcription_file.json",
            status=MeetingStatus.TRANSCRIPTION_DONE,
        )

        # Trait for meetings with report file
        with_report = factory.Trait(
            report_filename="report_file.json",
            status=MeetingStatus.REPORT_DONE,
        )
