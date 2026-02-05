from pydantic import BaseModel, ConfigDict

from mcr_meeting.app.models import Meeting


class MeetingInfo(BaseModel):
    meeting: Meeting
    email: str

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )
