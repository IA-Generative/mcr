from typing import List, Optional

from loguru import logger
from sqlalchemy.orm import Session

from mcr_meeting.app.db.db import get_db_session_ctx
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.models import Transcription
from mcr_meeting.app.schemas.transcription_schema import SpeakerTranscription


def save_transcription(
    transcription_data: List[SpeakerTranscription],
) -> List[Transcription]:
    """
    Persist a transcript in the database's transcription table

    Args:
        transcription_data (List[SpeakerTranscription]): List of Pydantic model containing the transcription data.

    Returns:
        List[AudioSegmentTranscription]: The created transcription objects.
    """
    with UnitOfWork():
        db = get_db_session_ctx()

        saved_transcriptions: List[Transcription] = []
        for item in transcription_data:
            existing_transcription = get_existing_transcription_segment(
                meeting_id=item.meeting_id,
                transcription_index=item.transcription_index,
                db_session=db,
            )
            if existing_transcription is not None:
                continue

            transcription = Transcription(
                **item.model_dump(exclude_unset=True, exclude={"start", "end"})
            )
            db.add(transcription)

            saved_transcriptions.append(transcription)

        logger.info(
            "New transcriptions segments added to the database | meeting-id : {} | segment count : {} ",
            item.meeting_id,
            len(saved_transcriptions),
        )

        return saved_transcriptions


def get_existing_transcription_segment(
    meeting_id: int, transcription_index: int, db_session: Session
) -> Optional[Transcription]:
    existing_transcription = (
        db_session.query(Transcription)
        .filter_by(
            meeting_id=meeting_id,
            transcription_index=transcription_index,
        )
        .first()
    )

    return existing_transcription
