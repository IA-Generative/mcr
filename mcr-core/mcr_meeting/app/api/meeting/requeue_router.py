from fastapi import APIRouter, Depends, Response, status

from mcr_meeting.app.api.dependencies.auth import require_admin
from mcr_meeting.app.configs.base import ApiSettings
from mcr_meeting.app.db.db import router_db_session_context_manager
from mcr_meeting.app.schemas.caller_schema import Caller
from mcr_meeting.app.schemas.requeue_schema import (
    RequeueFailure,
    RequeueTranscriptionsRequest,
    RequeueTranscriptionsResponse,
)
from mcr_meeting.app.use_cases.requeue_transcriptions import requeue_transcriptions

api_settings = ApiSettings()
router = APIRouter(
    prefix=api_settings.MEETING_API_PREFIX,
    dependencies=[Depends(router_db_session_context_manager)],
    tags=["Admin"],
)


@router.post("/transcription/requeue")
def requeue_transcriptions_endpoint(
    body: RequeueTranscriptionsRequest,
    response: Response,
    caller: Caller = Depends(require_admin),
) -> RequeueTranscriptionsResponse:
    meeting_ids = _dedupe_preserving_order(body.meeting_ids)
    result = requeue_transcriptions(meeting_ids, caller)

    response.status_code = (
        status.HTTP_202_ACCEPTED if not result.failed else status.HTTP_207_MULTI_STATUS
    )
    return RequeueTranscriptionsResponse(
        requeued=result.requeued,
        failed=[
            RequeueFailure(meeting_id=meeting_id, reason=reason)
            for meeting_id, reason in result.failed
        ],
    )


def _dedupe_preserving_order(meeting_ids: list[int]) -> list[int]:
    return list(dict.fromkeys(meeting_ids))
