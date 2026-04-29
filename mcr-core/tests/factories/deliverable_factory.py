from factory import LazyAttribute, SubFactory

from mcr_meeting.app.models.deliverable_model import (
    Deliverable,
    DeliverableStatus,
    DeliverableType,
)

from .base import BaseFactory
from .meeting_factory import MeetingFactory


class DeliverableFactory(BaseFactory[Deliverable]):
    class Meta:
        model = Deliverable

    type = DeliverableType.TRANSCRIPTION
    status = DeliverableStatus.AVAILABLE
    external_url = "https://drive.example.com/documents/123/"
    meeting = SubFactory(MeetingFactory)
    meeting_id = LazyAttribute(lambda obj: obj.meeting.id)
