import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from mcr_meeting.app.configs.base import Settings, SMTPSettings
from mcr_meeting.app.db.meeting_repository import get_meeting_by_id
from mcr_meeting.app.models import Meeting

logger = logging.getLogger(__name__)
settings = Settings()


def send_transcription_generation_success_email(meeting_id: int) -> None:
    """
    Send an email notification to the meeting owner when report generation is successful.

    Args:
        meeting_id (int): The ID of the meeting for which the report was generated
    """
    try:
        meeting = get_meeting_by_id(meeting_id)
        user = meeting.owner
        if not user:
            logger.error("No user found for meeting_id: %s", meeting_id)
            return

        subject, body = get_transcription_generation_success_email_content(meeting)

        success = _send_email(to_email=user.email, subject=subject, body=body)

        if success:
            logger.info(
                "Success email sent to %s for meeting %s", user.email, meeting_id
            )
        else:
            logger.error(
                "Failed to send success email to %s for meeting %s",
                user.email,
                meeting_id,
            )

    except Exception as e:
        logger.error(
            "Error sending transcription generation success email for meeting %s: %s",
            meeting_id,
            str(e),
        )


def send_report_generation_success_email(meeting_id: int) -> None:
    """
    Send an email notification to the meeting owner when report generation is successful.

    Args:
        meeting_id (int): The ID of the meeting for which the report was generated
    """
    try:
        meeting = get_meeting_by_id(meeting_id)
        user = meeting.owner
        if not user:
            logger.error("No user found for meeting_id: %s", meeting_id)
            return

        subject, body = get_report_generation_success_email_content(meeting)

        success = _send_email(to_email=user.email, subject=subject, body=body)

        if success:
            logger.info(
                "Success email sent to %s for meeting %s", user.email, meeting_id
            )
        else:
            logger.error(
                "Failed to send success email to %s for meeting %s",
                user.email,
                meeting_id,
            )

    except Exception as e:
        logger.error(
            "Error sending report generation success email for meeting %s: %s",
            meeting_id,
            str(e),
        )


def get_transcription_generation_success_email_content(
    meeting: Meeting,
) -> tuple[str, str]:
    subject = f"Votre transcription de la réunion {meeting.name} est prête"

    body = f"""<p>Bonjour,</p>

<p>La transcription de votre réunion {meeting.name} est prête.</p>

<p><a href="{settings.MCR_FRONTEND_URL}/meetings/{meeting.id}">Accéder à la page de la réunion</a> pour la télécharger.</p>

<p>Merci d'utiliser notre service.</p>

<p>Cordialement,</p>

<p>L'équipe France Compte Rendu</p>"""
    return (subject, body)


def get_report_generation_success_email_content(meeting: Meeting) -> tuple[str, str]:
    subject = f"Votre compte rendu de la réunion {meeting.name} est prêt"

    body = f"""<p>Bonjour,</p>

<p>Le relevé de décisions de votre réunion {meeting.name} est prêt.</p>

<p><a href="{settings.MCR_FRONTEND_URL}/meetings/{meeting.id}">Accéder à la page de la réunion</a> pour le télécharger.</p>

<p>Merci d'utiliser notre service.</p>

<p>Cordialement,</p>

<p>L'équipe France Compte Rendu</p>"""

    return (subject, body)


def _send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Send an email using SMTP.

    Args:
        to_email (str): Recipient email address
        subject (str): Email subject
        body (str): Email body content (HTML format)

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        smtp_settings = SMTPSettings()
        msg = MIMEMultipart()
        msg["From"] = smtp_settings.SMTP_SENDER
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html", "utf-8"))

        server = smtplib.SMTP_SSL(smtp_settings.SMTP_ENDPOINT, smtp_settings.SMTP_PORT)
        server.login(smtp_settings.SMTP_USERNAME, smtp_settings.SMTP_SECRET)

        # Send email
        server.sendmail(smtp_settings.SMTP_SENDER, to_email, msg.as_string())
        server.quit()

        return True

    except Exception as e:
        logger.error("Failed to send email to %s: %s", to_email, str(e))
        return False
