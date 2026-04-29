from pydantic import BaseModel, ConfigDict


class MeetingResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    name_platform: str
