import logging
import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from mcr_meeting.app.configs.base import Settings, SMTPSettings

_smtp_server = None
# Protects SMTP singleton from race conditions in our multi-threaded app
_smtp_lock = threading.Lock()

logger = logging.getLogger(__name__)
settings = Settings()


def send_email(to_email: str, subject: str, html: str) -> bool:
    """
    Send an email using the singleton SMTP client.

    Args:
        to_email (str): Recipient email address
        subject (str): Email subject
        html (str): Email html content (HTML)

    Returns:
        bool: True if sent successfully, False otherwise
    """
    try:
        settings = SMTPSettings()
        server = _get_smtp_server()

        msg = MIMEMultipart()
        msg["From"] = settings.SMTP_SENDER
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html, "html", "utf-8"))

        server.sendmail(
            settings.SMTP_SENDER,
            [to_email],
            msg.as_string(),
        )

        return True

    except Exception as e:
        logger.error("Failed to send email to %s: %s", to_email, str(e))
        # Reset connection on failure
        close_smtp_server()
        return False


def _get_smtp_server() -> smtplib.SMTP_SSL:
    """
    Lazily initialize and return the singleton SMTP server.
    """
    global _smtp_server

    if _smtp_server is not None:
        return _smtp_server

    with _smtp_lock:
        if _smtp_server is not None:
            return _smtp_server

        settings = SMTPSettings()
        try:
            server = smtplib.SMTP_SSL(
                settings.SMTP_ENDPOINT,
                settings.SMTP_PORT,
                timeout=10,
            )
            server.login(
                settings.SMTP_USERNAME,
                settings.SMTP_SECRET,
            )
            _smtp_server = server
            logger.info("SMTP connection initialized")
        except Exception:
            logger.exception("Failed to initialize SMTP connection")
            raise

    return _smtp_server


def close_smtp_server() -> None:
    """
    Explicitly close the SMTP connection (useful on shutdown).
    """
    global _smtp_server

    with _smtp_lock:
        if _smtp_server is None:
            return

        try:
            _smtp_server.quit()
            logger.info("SMTP connection closed")
        except Exception:
            logger.exception("Failed to close SMTP connection")
        finally:
            _smtp_server = None
