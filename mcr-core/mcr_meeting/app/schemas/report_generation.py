from typing import List, Optional

from pydantic import BaseModel


class ReportParticipant(BaseModel):
    """
    Model representing a participant in the report generation process.

    Attributes:
        speaker_id (str): The unique identifier of the speaker in the transcription.
        name (Optional[str]): The name of the participant, if available.
        role (Optional[str]): The role or function of the participant, if available.
    """

    speaker_id: str
    name: Optional[str]
    role: Optional[str]
    confidence: Optional[float]


class ReportHeader(BaseModel):
    """
    Model representing metadata for the report generation process.

    Attributes:
        meeting_id (int): The unique identifier of the meeting for which the report is generated.
        report_filename (Optional[str]): The filename of the generated report, if available.
    """

    title: Optional[str]
    objective: Optional[str]
    participants: List[ReportParticipant]
    next_meeting: Optional[str]


class ReportTopicWithDecision(BaseModel):
    title: str
    introduction_text: Optional[str]
    details: list[str]
    main_decision: Optional[str]


class ReportGenerationResponse(BaseModel):
    """
    Model representing the response of the report generation process.

    Attributes:
        topics_with_decision List[ReportTopicWithDecision]: A list of topics, each with its associated decisions.
        next_steps List[str]: A list of next steps identified during the meeting.
        header ReportHeader: Metadata about the meeting discussion.
    This class is used to structure the output of a report generation process.
    """

    header: ReportHeader
    topics_with_decision: List[ReportTopicWithDecision]
    next_steps: List[str]
