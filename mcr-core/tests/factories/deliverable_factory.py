from factory import LazyAttribute, SubFactory

from mcr_meeting.app.models.deliverable_model import Deliverable, DeliverableFileType

from .base import BaseFactory
from .meeting_factory import MeetingFactory


class DeliverableFactory(BaseFactory[Deliverable]):
    class Meta:
        model = Deliverable

    file_type = DeliverableFileType.TRANSCRIPTION
    external_url = "https://drive.example.com/documents/123/"
    meeting = SubFactory(MeetingFactory)
    meeting_id = LazyAttribute(lambda obj: obj.meeting.id)
