from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from mcr_meeting.app.models.meeting_model import MeetingStatus

from ..db.db import Base


class MeetingTransitionRecord(Base):
    """
    ORM model representing a the record of meeting state transition.

    Attributes:
        __tablename__ (str): The name of the database table for this model.
        id (int): The unique identifier of the record, automatically incremented.
        meeting_id (int): The id of the associated meeting.
        url (str): The URL for accessing the meeting, if applicable.
        start_date (datetime): The start time of the transition.
        estimation_date (datetime): The estimated end time of the transition.
        status_from (MeetingStatus): The status of the meeting when starting the transition.
    """

    __tablename__ = "meeting_transition_record"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meeting.id", ondelete="CASCADE"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    predicted_date_of_next_transition: Mapped[Optional[datetime]] = mapped_column(
        DateTime
    )
    status: Mapped[MeetingStatus] = mapped_column(
        SQLEnum(MeetingStatus), nullable=False
    )
