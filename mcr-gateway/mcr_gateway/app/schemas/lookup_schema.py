from pydantic import BaseModel


class ComuMeetingLookup(BaseModel):
    comu_meeting_id: str
    secret: str | None = None
    passcode: str | None = None


class ComuMeetingLookupResponse(BaseModel):
    name: str
