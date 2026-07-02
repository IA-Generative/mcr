"""Pure participant reconciliation: input formatting and name-loss detection."""

from dataclasses import dataclass

from mcr_meeting.app.schemas.transcription_schema import (
    DiarizedTranscriptionSegment,
    Participant,
)


@dataclass
class ParticipantNameLoss:
    speaker_id: str
    previous_name: str
    step_index: int
    reason: str


def format_participants_input(
    segments: list[DiarizedTranscriptionSegment],
) -> str:
    return "\n".join(str(seg) for seg in segments)


def detect_name_losses(
    previous: list[Participant],
    current: list[Participant],
    step_index: int,
) -> list[ParticipantNameLoss]:
    previous_by_id = {p.speaker_id: p for p in previous}
    current_by_id = {p.speaker_id: p for p in current}

    losses: list[ParticipantNameLoss] = []
    for speaker_id, prev in previous_by_id.items():
        if prev.name is None:
            continue
        current_participant = current_by_id.get(speaker_id)
        if current_participant is None:
            losses.append(
                ParticipantNameLoss(
                    speaker_id=speaker_id,
                    previous_name=prev.name,
                    step_index=step_index,
                    reason="disappeared",
                )
            )
        elif current_participant.name is None:
            losses.append(
                ParticipantNameLoss(
                    speaker_id=speaker_id,
                    previous_name=prev.name,
                    step_index=step_index,
                    reason="name_set_to_null",
                )
            )

    return losses
