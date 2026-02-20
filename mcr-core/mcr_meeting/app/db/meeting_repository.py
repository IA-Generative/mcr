from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import joinedload

from mcr_meeting.app.db.db import get_db_session_ctx
from mcr_meeting.app.exceptions.exceptions import (
    NotFoundException,
)
from mcr_meeting.app.models import Meeting, MeetingStatus, Transcription
from mcr_meeting.app.utils.db_utils import update_model

from ..schemas.meeting_schema import MeetingCreate


def save_meeting(user_id: int, meeting_data: MeetingCreate) -> Meeting:
    """
    Service to create a new meeting.

    Args:
        user_id (int): The ID of the user creating the meeting.
        meeting_data (MeetingCreate): The Pydantic model containing the meeting data.

    Returns:
        Meeting: The created meeting object.
    """
    db = get_db_session_ctx()
    meeting = Meeting(user_id=user_id)
    update_model(meeting, meeting_data)

    db.add(meeting)
    return meeting


def get_meeting_by_id(meeting_id: int) -> Meeting:
    """
    Retrieve a meeting by its ID from the database.

    Args:
        meeting_id (int): The ID of the meeting to retrieve.

    Returns:
        Meeting: The meeting object with the specified ID, or None if not found.
    """
    db = get_db_session_ctx()
    meeting = db.get(Meeting, meeting_id)
    meeting = (
        db.query(Meeting)
        .filter(Meeting.id == meeting_id, Meeting.status != MeetingStatus.DELETED)
        .first()
    )

    if meeting is None:
        raise NotFoundException(f"Meeting not found: id={meeting_id}")

    return meeting


def update_meeting(updated_meeting: Meeting) -> Meeting:
    """
    ORM link to update a meeting in the database.

    Args:
        updated_meeting (Meeting): The ORM model representing the meeting to update.

    Returns:
        Meeting: The updated meeting object,
    """

    db = get_db_session_ctx()

    db.merge(updated_meeting)
    return updated_meeting


def get_meetings(
    user_id: int, search: Optional[str], page: int, page_size: int
) -> List[Meeting]:
    """
    Récupère une liste de réunions filtrées depuis la base de données.

    Args:
        user_id (int): ID de l'utilisateur.
        search (str): Terme de recherche optionnel pour filtrer les réunions.
        page (int): Numéro de page.
        page_size (int): Nombre d'éléments par page.

    Returns:
        List[Meeting]: Liste des réunions correspondant aux critères.
    """
    page = max(1, page)
    page_size = page_size if page_size > 0 else 1

    db = get_db_session_ctx()
    query = db.query(Meeting).filter(
        Meeting.user_id == user_id, Meeting.status != MeetingStatus.DELETED
    )
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            Meeting.name.ilike(search_pattern),
        )

    offset = (page - 1) * page_size
    return (
        query.order_by(Meeting.creation_date.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )


def get_meeting_with_transcriptions(
    meeting_id: int,
) -> Meeting:
    """
    Retrieve a meeting and its latest transcriptions by its ID from the database.

    Args:
        meeting_id (int): The ID of the meeting to retrieve.

    Returns:
        Meeting: The meeting object with the specified ID, or None if not found.
    """
    db = get_db_session_ctx()
    # Requête principale pour récupérer la réunion avec les transcriptions
    meeting: Optional[Meeting] = (
        db.query(Meeting)
        .options(
            joinedload(Meeting.transcriptions)  # Chargement rapide des transcriptions
        )
        .join(Transcription)  # Jointure avec la table Transcription
        .filter(
            Meeting.id == meeting_id,
            Meeting.status != MeetingStatus.DELETED,
        )
        .first()
    )
    if not meeting:
        raise NotFoundException(f"Meeting not found: id={meeting_id}")
    return meeting


def count_pending_meetings() -> int:
    """
    Count the number of meetings in TRANSCRIPTION_PENDING that are less than 24 hours old.

    Returns:
        int: The number of pending meetings
    """
    db = get_db_session_ctx()
    staleness_threshold = datetime.now() - timedelta(hours=24)
    return (
        db.query(Meeting)
        .filter(
            Meeting.status == MeetingStatus.TRANSCRIPTION_PENDING,
            Meeting.creation_date > staleness_threshold,
        )
        .count()
    )
