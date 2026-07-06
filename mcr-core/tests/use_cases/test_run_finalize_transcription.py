from unittest.mock import Mock

from pytest_mock import MockerFixture

import mcr_meeting.app.use_cases.transcription.run_finalize_transcription as rf
from tests.mocks.in_memory_s3 import InMemoryS3

MEETING_ID = 123

# Clé écrite en dur : elle fait partie du contrat d'interface de l'app
# vers S3, un changement ici casse la reprise des pipelines en vol.
TRANSCRIPTION_RAW_KEY = "artifacts/123/transcription_raw.json"


def test_reads_raw_segments_and_builds_speaker_transcriptions(
    in_memory_s3: InMemoryS3, mocker: MockerFixture
) -> None:
    in_memory_s3.objects[TRANSCRIPTION_RAW_KEY] = (
        b'[{"id": 0, "start": 0.0, "end": 1.0, "text": "hello", "speaker": "A"}]'
    )
    mocker.patch.object(
        rf,
        "get_feature_flag_client",
        return_value=Mock(is_enabled=Mock(return_value=False)),
    )
    mocker.patch.object(rf, "correct_acronyms", side_effect=lambda text: text)
    mocker.patch.object(rf, "extract_participants", return_value=[])

    result = rf.run_finalize_transcription(MEETING_ID)

    assert len(result) == 1
    assert result[0].meeting_id == MEETING_ID
    assert "hello" in result[0].transcription
