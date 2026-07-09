from collections.abc import Iterator

import pytest
from pytest_mock import MockerFixture

import mcr_meeting.app.infrastructure.speech_to_text_models as stt
from mcr_meeting.app.utils.compute_devices import ComputeDevice


@pytest.fixture(autouse=True)
def clear_model_caches() -> Iterator[None]:
    stt.get_transcription_model.cache_clear()
    stt.get_diarization_pipeline.cache_clear()
    yield
    stt.get_transcription_model.cache_clear()
    stt.get_diarization_pipeline.cache_clear()


class TestLazyModelCaching:
    def test_transcription_model_loads_once_across_calls(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(stt, "is_gpu_available", return_value=False)
        load = mocker.patch.object(stt, "load_whisper_model")

        first = stt.get_transcription_model()
        second = stt.get_transcription_model()

        load.assert_called_once_with(ComputeDevice.CPU)
        assert first is second

    def test_diarization_pipeline_loads_once_across_calls(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(stt, "is_gpu_available", return_value=False)
        load = mocker.patch.object(stt, "load_diarization_pipeline")

        first = stt.get_diarization_pipeline()
        second = stt.get_diarization_pipeline()

        load.assert_called_once_with(ComputeDevice.CPU)
        assert first is second

    def test_device_is_resolved_at_load_time(self, mocker: MockerFixture) -> None:
        mocker.patch.object(stt, "is_gpu_available", return_value=True)
        mocker.patch.object(stt, "get_gpu_name", return_value="fake-gpu")
        load = mocker.patch.object(stt, "load_whisper_model")

        stt.get_transcription_model()

        load.assert_called_once_with(ComputeDevice.GPU)
