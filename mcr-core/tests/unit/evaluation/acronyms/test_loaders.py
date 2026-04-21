import json
from pathlib import Path

from mcr_meeting.evaluation.acronyms.loaders import (
    load_audio_reference,
    load_glossary,
)


class TestLoadGlossary:
    def test_loads_flat_list(self, tmp_path: Path) -> None:
        path = tmp_path / "glossary.json"
        path.write_text(json.dumps(["DGPN", "DGGN", "ANTS"]))
        assert load_glossary(path) == ["DGPN", "DGGN", "ANTS"]


class TestLoadAudioReference:
    def test_loads_flat_mapping(self, tmp_path: Path) -> None:
        path = tmp_path / "ref.json"
        path.write_text(json.dumps({"DGPN": 1, "ANTS": 2}))
        assert load_audio_reference(path) == {"DGPN": 1, "ANTS": 2}
