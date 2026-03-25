from mcr_meeting.app.models.deliverable_model import Deliverable, DeliverableFileType
from mcr_meeting.app.services.deliverable_storage_service import store_deliverable
from mcr_meeting.app.services.redis_token_store import get_refresh_token
from mcr_meeting.app.services.token_exchange_service import ensure_offline_token
from tests.factories.meeting_factory import MeetingFactory
from tests.mocks.in_memory_drive import InMemoryDriveClient
from tests.mocks.in_memory_keycloak import InMemoryKeycloak
from tests.mocks.in_memory_redis import InMemoryRedis


def _query_deliverables(meeting_id: int) -> list[Deliverable]:
    from mcr_meeting.app.db.db import get_db_session_ctx

    return list(
        get_db_session_ctx()
        .query(Deliverable)
        .filter(Deliverable.meeting_id == meeting_id)
        .all()
    )


def test_refresh_token_is_stored_when_user_starts_transcription(
    in_memory_redis: InMemoryRedis, in_memory_keycloak: InMemoryKeycloak
) -> None:
    in_memory_keycloak.exchange_refresh_token = "offline-refresh-token"

    ensure_offline_token("user-uuid-123", "access-token-abc")

    assert get_refresh_token("user-uuid-123") == "offline-refresh-token"


def test_ensure_offline_token_does_nothing_without_access_token() -> None:
    ensure_offline_token("user-uuid-123", None)


def test_token_exchange_failure_does_not_raise(
    in_memory_keycloak: InMemoryKeycloak,
) -> None:
    in_memory_keycloak.should_fail_exchange = True

    ensure_offline_token("user-uuid-123", "access-token-abc")


def test_transcription_is_uploaded_to_drive_after_completion(
    in_memory_redis: InMemoryRedis,
    in_memory_keycloak: InMemoryKeycloak,
    in_memory_drive: InMemoryDriveClient,
    db_session: None,
) -> None:
    meeting = MeetingFactory.create()
    user_uuid = str(meeting.owner.keycloak_uuid)
    in_memory_redis.set(f"drive_token:{user_uuid}", "stored-refresh-token")

    store_deliverable(
        meeting_id=meeting.id,
        user_keycloak_uuid=user_uuid,
        file_bytes=b"docx-content",
        file_type=DeliverableFileType.TRANSCRIPTION,
        filename="Transcription_Test.docx",
    )

    deliverables = _query_deliverables(meeting.id)
    assert len(deliverables) == 1
    assert deliverables[0].file_type == DeliverableFileType.TRANSCRIPTION
    assert deliverables[0].external_url == "https://drive.example.com/documents/42/"


def test_transcription_upload_skipped_when_no_refresh_token(
    in_memory_drive: InMemoryDriveClient,
    db_session: None,
) -> None:
    meeting = MeetingFactory.create()

    store_deliverable(
        meeting_id=meeting.id,
        user_keycloak_uuid=str(meeting.owner.keycloak_uuid),
        file_bytes=b"docx-content",
        file_type=DeliverableFileType.TRANSCRIPTION,
    )

    assert len(_query_deliverables(meeting.id)) == 0


def test_refresh_token_rotation_is_persisted(
    in_memory_redis: InMemoryRedis,
    in_memory_keycloak: InMemoryKeycloak,
    in_memory_drive: InMemoryDriveClient,
    db_session: None,
) -> None:
    meeting = MeetingFactory.create()
    user_uuid = str(meeting.owner.keycloak_uuid)
    in_memory_redis.set(f"drive_token:{user_uuid}", "old-refresh-token")
    in_memory_keycloak.rotated_refresh_token = "new-rotated-refresh-token"

    store_deliverable(
        meeting_id=meeting.id,
        user_keycloak_uuid=user_uuid,
        file_bytes=b"docx-content",
        file_type=DeliverableFileType.TRANSCRIPTION,
    )

    assert get_refresh_token(user_uuid) == "new-rotated-refresh-token"


def test_drive_upload_failure_does_not_raise(
    in_memory_redis: InMemoryRedis,
    in_memory_drive: InMemoryDriveClient,
    db_session: None,
) -> None:
    meeting = MeetingFactory.create()
    user_uuid = str(meeting.owner.keycloak_uuid)
    in_memory_redis.set(f"drive_token:{user_uuid}", "stored-refresh-token")
    in_memory_drive.should_fail = True

    store_deliverable(
        meeting_id=meeting.id,
        user_keycloak_uuid=user_uuid,
        file_bytes=b"docx-content",
        file_type=DeliverableFileType.TRANSCRIPTION,
    )

    assert len(_query_deliverables(meeting.id)) == 0
