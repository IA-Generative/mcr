from pydantic import BaseModel, Field


class RequeueTranscriptionsRequest(BaseModel):
    meeting_ids: list[int] = Field(min_length=1, max_length=100)
