from enum import StrEnum

from mcr_generation.app.schemas.celery_types import ReportTypes


class NotesFacet(StrEnum):
    INTENT = "intent"
    NEXT_MEETING = "next_meeting"
    TOPICS = "topics"
    DISCUSSIONS = "discussions"


_FACETS_BY_REPORT_TYPE: dict[ReportTypes, frozenset[NotesFacet]] = {
    ReportTypes.DECISION_RECORD: frozenset(
        {NotesFacet.INTENT, NotesFacet.NEXT_MEETING, NotesFacet.TOPICS}
    ),
    ReportTypes.DETAILED_SYNTHESIS: frozenset(
        {NotesFacet.INTENT, NotesFacet.NEXT_MEETING, NotesFacet.DISCUSSIONS}
    ),
    ReportTypes.STRUCTURED_MINUTES: frozenset(
        {NotesFacet.INTENT, NotesFacet.NEXT_MEETING, NotesFacet.TOPICS}
    ),
}


def facets_for_report_type(report_type: ReportTypes) -> frozenset[NotesFacet]:
    """Map a ReportTypes to its historical notes facets; empty frozenset for any
    unmapped type (incl. CUSTOM_REPORT, where facets come from the rewriter plan)."""
    return _FACETS_BY_REPORT_TYPE.get(report_type, frozenset())
