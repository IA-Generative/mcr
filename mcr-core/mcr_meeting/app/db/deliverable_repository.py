from mcr_meeting.app.db.db import get_db_session_ctx
from mcr_meeting.app.models.deliverable_model import Deliverable


def save_deliverable(deliverable: Deliverable) -> Deliverable:
    db = get_db_session_ctx()
    db.add(deliverable)
    db.flush()
    return deliverable
