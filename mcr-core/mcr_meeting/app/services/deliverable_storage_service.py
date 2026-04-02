from loguru import logger
from pydantic import UUID4

from mcr_meeting.app.client.drive_client import upload_file
from mcr_meeting.app.db.deliverable_repository import (
    get_deliverable_by_meeting_id_and_file_type,
    save_deliverable,
)
from mcr_meeting.app.db.deliverable_repository import (
    update_deliverable as update_deliverable_repository,
)
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.models.deliverable_model import Deliverable, DeliverableFileType
from mcr_meeting.app.schemas.deliverable_schema import (
    DeliverableUpdate,
    VoteRequest,
)
from mcr_meeting.app.services.meeting_service import get_meeting_service
from mcr_meeting.app.services.redis_token_store import (
    delete_refresh_token,
    get_refresh_token,
    save_refresh_token,
)
from mcr_meeting.app.services.token_exchange_service import refresh_access_token
from mcr_meeting.app.utils.db_utils import update_model


def _acquire_fresh_access_token(user_keycloak_uuid: str) -> str:
    refresh_token = get_refresh_token(user_keycloak_uuid)
    if refresh_token is None:
        raise RuntimeError(
            f"No refresh token skipping Drive upload: user = {user_keycloak_uuid}"
        )

    try:
        token_refresh_result = refresh_access_token(refresh_token)
    except Exception as exc:
        delete_refresh_token(user_keycloak_uuid)
        raise RuntimeError(
            f"Refresh token failed for user = {user_keycloak_uuid}: {exc}"
        ) from exc

    if token_refresh_result.rotated_refresh:
        save_refresh_token(user_keycloak_uuid, token_refresh_result.rotated_refresh)
    return token_refresh_result.access_token


def store_deliverable(
    meeting_id: int,
    user_keycloak_uuid: str,
    file_bytes: bytes,
    file_type: DeliverableFileType,
    filename: str = "document.docx",
) -> None:
    try:
        access_token = _acquire_fresh_access_token(user_keycloak_uuid)

        external_url = upload_file(access_token, filename, file_bytes)

        with UnitOfWork():
            save_deliverable(
                Deliverable(
                    meeting_id=meeting_id,
                    file_type=file_type,
                    external_url=external_url,
                )
            )

    except Exception as exc:
        logger.exception(
            "Failed to store {} deliverable for meeting {}: {}",
            file_type.value,
            meeting_id,
            exc,
        )


def get_deliverable_service(
    meeting_id: int, current_user_keycloak_uuid: UUID4, file_type: DeliverableFileType
) -> Deliverable:
    """
    Service to retrieve a deliverable for a given meeting and file type.

    Args:
        meeting_id (int): The ID of the meeting linked to the deliverable.
        file_type (DeliverableFileType): The type of the deliverable file.

    Returns:
        Deliverable: The retrieved deliverable object, or None if no deliverable was found.
    """

    # Check if the meeting exists and is accessible by the user, but we don't need the meeting object itself, so we discard it
    _ = get_meeting_service(meeting_id, current_user_keycloak_uuid)
    return get_deliverable_by_meeting_id_and_file_type(
        meeting_id=meeting_id, file_type=file_type
    )


def update_deliverable(
    meeting_id: int,
    current_user_keycloak_uuid: UUID4,
    deliverable_update: DeliverableUpdate,
) -> Deliverable:
    """
    Service to update an existing deliverable.

    Args:

        meeting_id (int): The ID of the meeting linked to the deliverable.
        deliverable_update (Deliverable): The Pydantic model containing the updated deliverable data.

    Returns:
        Deliverable: The updated deliverable object, or None if no deliverable was found.
    """

    with UnitOfWork():
        deliverable = get_deliverable_service(
            meeting_id=meeting_id,
            current_user_keycloak_uuid=current_user_keycloak_uuid,
            file_type=deliverable_update.file_type,
        )

        update_model(deliverable, deliverable_update)

        return update_deliverable_repository(deliverable)


def update_deliverable_vote(
    deliverable: Deliverable,
    vote_request: VoteRequest,
) -> Deliverable:
    deliverable.vote_type = vote_request.vote_type
    deliverable.vote_comment = vote_request.vote_comment
    return update_deliverable_repository(deliverable)
