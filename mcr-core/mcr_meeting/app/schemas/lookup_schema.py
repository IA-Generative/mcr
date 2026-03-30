from pydantic import BaseModel, model_validator


class ComuMeetingLookup(BaseModel):
    comu_meeting_id: str
    secret: str | None = None
    passcode: str | None = None

    @model_validator(mode="after")
    def validate_secret_or_passcode(self) -> "ComuMeetingLookup":
        if self.secret is None and self.passcode is None:
            raise ValueError("Either 'secret' or 'passcode' must be provided")
        if self.secret is not None and self.passcode is not None:
            raise ValueError(
                "Only one of 'secret' or 'passcode' must be provided, not both"
            )
        return self


class ComuMeetingLookupResponse(BaseModel):
    name: str
