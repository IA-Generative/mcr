import re

# Maps the canonical section name (used in `Criterion.scope`, in the dataset
# layout `expected/<section>/`, and as a CSV column key) to the heading text
# used by the report renderer.
SECTION_HEADERS: dict[str, str] = {
    "topics": "Topics",
    "participants": "Participants",
    "next_steps": "Next steps",
}


def extract_section(markdown: str, section_name: str) -> str | None:
    if section_name not in SECTION_HEADERS:
        raise KeyError(
            f"Unknown section '{section_name}'. "
            f"Known sections: {sorted(SECTION_HEADERS)}"
        )
    heading = SECTION_HEADERS[section_name]
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\s*$(?P<body>.*?)(?=^##\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(markdown)
    if match is None:
        return None
    return match.group("body").strip()
