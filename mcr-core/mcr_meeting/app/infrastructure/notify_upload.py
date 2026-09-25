import httpx
from loguru import logger

from mcr_meeting.app.configs.base import NotifyUploadSettings
from mcr_meeting.app.models.deliverable_model import DeliverableType

_settings = NotifyUploadSettings()


# Proof of concept: the receiver is not settled yet, so the payload contract is
# intentionally minimal and unversioned, and there is no auth, signature,
# dedup key or retry. All four are productionisation concerns — retrying a POST
# whose response was lost would double-deliver the event, so the retry scope
# cannot be chosen before the receiver's idempotency is known.
def notify_upload(
    meeting_id: int, deliverable_type: DeliverableType, drive_url: str
) -> None:
    if not _settings.NOTIFY_UPLOAD_URL:
        return

    # str(): Deliverable.type is a String column, so the ORM yields a plain str
    # despite its Mapped[DeliverableType] annotation. StrEnum makes this correct
    # for both an enum member and a raw value.
    type_name = str(deliverable_type)

    response = httpx.post(
        _settings.NOTIFY_UPLOAD_URL,
        json={
            "meetingId": meeting_id,
            "deliverableType": type_name,
            "driveUrl": drive_url,
        },
        timeout=httpx.Timeout(_settings.NOTIFY_UPLOAD_TIMEOUT, connect=2.0),
    )
    response.raise_for_status()
    logger.info("Notified upload of {} for meeting {}", type_name, meeting_id)
