from pydantic import BaseModel, Field

from mcr_meeting.app.use_cases.requeue_transcriptions import RequeueReason


class RequeueTranscriptionsRequest(BaseModel):
    meeting_ids: list[int] = Field(min_length=1, max_length=100)


class RequeueFailure(BaseModel):
    meeting_id: int
    reason: RequeueReason


class RequeueTranscriptionsResponse(BaseModel):
    requeued: list[int]
    failed: list[RequeueFailure]
