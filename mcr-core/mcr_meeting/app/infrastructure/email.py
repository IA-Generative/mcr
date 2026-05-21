from mcr_meeting.app.services.email.email_service import (
    send_report_generation_success_email,
)


def notify_report_ready(meeting_id: int) -> None:
    send_report_generation_success_email(meeting_id=meeting_id)
