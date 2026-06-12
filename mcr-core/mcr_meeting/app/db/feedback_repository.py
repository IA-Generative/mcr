from sqlalchemy.exc import DataError

from mcr_meeting.app.db.db import get_db_session_ctx
from mcr_meeting.app.exceptions.exceptions import InvalidFeedbackDataException
from mcr_meeting.app.models.feedback_model import Feedback


def save_feedback(feedback: Feedback) -> Feedback:
    db = get_db_session_ctx()
    db.add(feedback)
    try:
        db.flush()
    except DataError as exc:
        raise InvalidFeedbackDataException(
            f"Feedback data rejected by the database for user={feedback.user_id}"
        ) from exc
    return feedback
