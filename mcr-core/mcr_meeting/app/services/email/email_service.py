import logging
from typing import Tuple

from mcr_meeting.app.client.smtp_client import send_email
from mcr_meeting.app.configs.base import Settings
from mcr_meeting.app.db.meeting_repository import get_meeting_by_id
from mcr_meeting.app.exceptions.exceptions import NotFoundException
from mcr_meeting.app.models import Meeting
from mcr_meeting.app.services.email.templates import (
    get_report_generation_success_email_template,
    get_transcription_generation_success_email_template,
)

logger = logging.getLogger(__name__)
settings = Settings()


def _get_meeting_info(meeting_id: int) -> Tuple[Meeting, str]:
    """
    Util function that returns meeting infos
    """
    meeting = get_meeting_by_id(meeting_id)
    user = meeting.owner
    if not user:
        logger.error("No user found for meeting_id: %s", meeting.id)
        raise NotFoundException("No user found for meeting_id: %s", meeting.id)

    return meeting, user.email


def send_transcription_generation_success_email(meeting_id: int) -> bool:
    meeting, email = _get_meeting_info(meeting_id)
    meeting_name = meeting.name or ""
    meeting_link = f"{settings.MCR_FRONTEND_URL}/meetings/{meeting.id}"
    subject = f"Votre transcription de la réunion {meeting_name} est prête"

    return send_email(
        to_email=email,
        subject=subject,
        html=get_transcription_generation_success_email_template(
            meeting_name=meeting_name, meeting_link=meeting_link
        ),
    )


def send_report_generation_success_email(meeting_id: int) -> bool:
    meeting, email = _get_meeting_info(meeting_id)
    meeting_name = meeting.name or ""
    meeting_link = f"{settings.MCR_FRONTEND_URL}/meetings/{meeting.id}"
    subject = f"Votre compte rendu de la réunion {meeting_name} est prêt"

    return send_email(
        to_email=email,
        subject=subject,
        html=get_report_generation_success_email_template(
            meeting_name=meeting_name, meeting_link=meeting_link
        ),
    )
