from datetime import datetime, timezone

from loguru import logger

from mcr_meeting.app.db.deliverable_repository import save_deliverable
from mcr_meeting.app.db.meeting_repository import (
    get_meeting_with_owner,
    update_meeting,
)
from mcr_meeting.app.db.meeting_transition_record_repository import (
    save_meeting_transition_record,
)
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain.email import (
    build_transcription_ready_email,
)
from mcr_meeting.app.domain.meeting_transitions import mark_transcription_done
from mcr_meeting.app.domain.transcription_rendering import render_transcription_docx
from mcr_meeting.app.infrastructure import email as email_infra
from mcr_meeting.app.infrastructure.drive import upload_file
from mcr_meeting.app.infrastructure.keycloak import (
    TokenRefreshResult,
    refresh_access_token,
)
from mcr_meeting.app.infrastructure.redis import (
    delete_refresh_token,
    get_refresh_token,
    save_refresh_token,
)
from mcr_meeting.app.infrastructure.s3 import upload_transcription_to_s3
from mcr_meeting.app.models import Meeting
from mcr_meeting.app.models.deliverable_model import (
    Deliverable,
    DeliverableStatus,
    DeliverableType,
)
from mcr_meeting.app.models.meeting_model import MeetingStatus
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord
from mcr_meeting.app.schemas.transcription_schema import SpeakerTranscription
from mcr_meeting.app.utils.deliverable_filename import build_deliverable_filename

TRANSCRIPTION_FILENAME = "v0.docx"


def complete_transcription(
    meeting_id: int, transcriptions: list[SpeakerTranscription]
) -> None:
    meeting = get_meeting_with_owner(meeting_id)
    mark_transcription_done(meeting)

    docx_buffer = render_transcription_docx(meeting.name, transcriptions)
    upload_transcription_to_s3(
        meeting_id=meeting.id,
        filename=TRANSCRIPTION_FILENAME,
        content=docx_buffer,
    )
    meeting.transcription_filename = TRANSCRIPTION_FILENAME

    external_url = _try_drive_upload_workflow(
        meeting, file_bytes=docx_buffer.getvalue()
    )

    with UnitOfWork():
        update_meeting(meeting)
        save_meeting_transition_record(
            MeetingTransitionRecord(
                meeting_id=meeting.id,
                timestamp=datetime.now(timezone.utc),
                status=MeetingStatus.TRANSCRIPTION_DONE,
            )
        )
        save_deliverable(
            Deliverable(
                meeting_id=meeting.id,
                type=DeliverableType.TRANSCRIPTION,
                status=DeliverableStatus.AVAILABLE,
                external_url=external_url,
            )
        )

    _notify_transcription_ready_best_effort(meeting)


def _notify_transcription_ready_best_effort(meeting: Meeting) -> None:
    try:
        content = build_transcription_ready_email(
            meeting.name or "", meeting_id=meeting.id
        )
        email_infra.send_email(
            to_email=meeting.owner.email,
            subject=content.subject,
            html=content.html,
        )
    except Exception:
        logger.exception("notification failed for meeting {}", meeting.id)


def _try_drive_upload_workflow(
    meeting: Meeting,
    file_bytes: bytes,
) -> str | None:
    token = _try_acquire_token(meeting)
    if token is None:
        return None

    filename = build_deliverable_filename(
        DeliverableType.TRANSCRIPTION, meeting.name or ""
    )
    external_url = _try_post_drive(token, filename, file_bytes)

    return external_url


def _try_acquire_token(meeting: Meeting) -> TokenRefreshResult | None:
    user_sub = str(meeting.owner.keycloak_uuid)

    refresh_token = get_refresh_token(user_sub)
    if refresh_token is None:
        logger.info("No refresh token for user {}; skipping Drive upload", user_sub)
        return None

    try:
        token_result = refresh_access_token(refresh_token)
    except Exception:
        delete_refresh_token(user_sub)
        logger.warning(
            "Drive token refresh failed for user {}; skipping upload", user_sub
        )
        return None

    if token_result.rotated_refresh:
        save_refresh_token(user_sub, token_result.rotated_refresh)

    return token_result


def _try_post_drive(
    token: TokenRefreshResult, filename: str, file_bytes: bytes
) -> str | None:
    try:
        return upload_file(token.access_token, filename, file_bytes)
    except Exception:
        logger.warning("Drive upload failed")
        return None
