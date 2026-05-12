from loguru import logger

from mcr_meeting.app.db.deliverable_repository import save_deliverable
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.models.deliverable_model import (
    Deliverable,
    DeliverableStatus,
    DeliverableType,
)
from mcr_meeting.app.services.drive_upload_service import try_upload_to_drive


def store_deliverable(
    meeting_id: int,
    user_keycloak_uuid: str,
    file_bytes: bytes,
    type: DeliverableType,
    filename: str = "document.docx",
) -> None:
    external_url = try_upload_to_drive(
        user_keycloak_uuid=user_keycloak_uuid,
        filename=filename,
        content=file_bytes,
    )
    if external_url is None:
        return

    try:
        with UnitOfWork():
            save_deliverable(
                Deliverable(
                    meeting_id=meeting_id,
                    type=type,
                    status=DeliverableStatus.AVAILABLE,
                    external_url=external_url,
                )
            )
    except Exception:
        logger.exception(
            "Failed to persist {} deliverable for meeting {}",
            type.value,
            meeting_id,
        )
