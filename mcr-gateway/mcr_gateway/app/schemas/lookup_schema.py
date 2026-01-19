from pydantic import BaseModel


class ComuMeetingLookup(BaseModel):
    """
    Base model for looking up a Comu meeting.
    """

    comu_meeting_id: str
    secret: str


class ComuMeetingLookupResponse(BaseModel):
    """
    Base model for the response of a Comu meeting lookup.
    """

    name: str
