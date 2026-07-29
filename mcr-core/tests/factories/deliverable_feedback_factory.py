from factory import LazyAttribute, SubFactory

from mcr_meeting.app.models.deliverable_feedback_model import DeliverableFeedback
from mcr_meeting.app.models.feedback_model import VoteType
from tests.factories.base import BaseFactory
from tests.factories.deliverable_factory import DeliverableFactory


class DeliverableFeedbackFactory(BaseFactory[DeliverableFeedback]):
    class Meta:
        model = DeliverableFeedback
        exclude = ("deliverable",)

    vote_type = VoteType.POSITIVE
    comment = None
    is_active = True
    deliverable = SubFactory(DeliverableFactory)
    deliverable_id = LazyAttribute(lambda obj: obj.deliverable.id)
