from pydantic import BaseModel


class DiarizationSegment(BaseModel):
    start: float
    end: float
    speaker: str
