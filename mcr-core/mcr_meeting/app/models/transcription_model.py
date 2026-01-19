from typing import TYPE_CHECKING

if TYPE_CHECKING:  # Avoid circular imports but allow proper typing
    from .meeting_model import Meeting

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.db import Base


class Transcription(Base):
    """
    Schema for storing transcription data related to specific audio segments in a meeting.

    This model represents a single transcription of an audio segment, which includes
    the speaker, transcription text, and metadata like audio and transcription indices.

    Attributes:
        id (int): The unique identifier for the transcription record.
        transcription_index (int): The index of the transcription.
        speaker (str): The name of the speaker who provided the transcription.
        transcription (str): The text of the transcription for the specific segment.
        version (int): The version number of the transcription (default is 0).
        meeting_id (int): The identifier of the meeting associated with the transcription.
        meeting (Meeting): A relationship to the `Meeting` model, linking each transcription to a meeting.

    This class is used to store transcriptions for specific audio segments within a meeting, enabling
    efficient retrieval and analysis of meeting transcriptions.
    """

    __tablename__ = "transcription"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    transcription_index: Mapped[int] = mapped_column(index=True)
    speaker: Mapped[str] = mapped_column(String, index=True)
    transcription: Mapped[str] = mapped_column(String)
    meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meeting.id", ondelete="CASCADE")
    )

    meeting: Mapped["Meeting"] = relationship(back_populates="transcriptions")
