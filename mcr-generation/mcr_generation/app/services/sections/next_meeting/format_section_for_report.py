from loguru import logger

from mcr_generation.app.schemas.base import NextMeeting


def format_next_meeting_for_report(next_meeting: NextMeeting) -> str | None:
    """Format NextMeeting information into a string for the report.

    Args:
        next_meeting (NextMeeting): NextMeeting object with title, objective, date, and time attributes
    return f"Titre: {next_meeting.title}\nObjectif: {next_meeting.objective}\nDate: {next_meeting.date}\nHeure: {next_meeting.time}"
    """
    date = next_meeting.date
    time = next_meeting.time
    confidence = next_meeting.confidence
    purpose = next_meeting.purpose

    if confidence is None or confidence < 0.5:
        logger.info(
            "No reliable NextMeeting information extracted (confidence: {})", confidence
        )
        return None
    if purpose is None:
        logger.info(
            "No purpose for NextMeeting information extracted (confidence: {}) purpose: {} ",
            confidence,
            purpose,
        )
        return None

    if date and time:
        date_time_text = f"\nDate et heure prévues: {date} - {time}"
    else:
        date_text = f"\nDate prévue: {date}" if date else ""
        time_text = f"\nHeure prévue: {time}" if time else ""
        date_time_text = date_text + time_text

    text = f"{purpose}{date_time_text}"
    logger.debug("Formatted NextMeeting for report: {}", text)
    return text
