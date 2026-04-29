from mcr_meeting.app.db.db import get_db_session_ctx
from mcr_meeting.app.models.feedback_model import Feedback


def save_feedback(feedback: Feedback) -> Feedback:
    db = get_db_session_ctx()
    db.add(feedback)
    db.flush()
    return feedback
