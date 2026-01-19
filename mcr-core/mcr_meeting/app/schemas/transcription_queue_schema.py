from pydantic import BaseModel


class TranscriptionQueueStatusResponse(BaseModel):
    """
    Schema for the status of the transcription queue of a meeting.

    Attributes:
        estimation_duration_minutes: Estimated waiting time in minutes before the start of the transcription
    """

    estimation_duration_minutes: int
