import logging
import smtplib
import socket
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from mcr_meeting.app.configs.base import SMTPSettings

logger = logging.getLogger(__name__)


def send_email(
    to_email: str,
    subject: str,
    html: str,
    max_retries: int = 3,
) -> bool:
    """
    Send an email with retry and exponential backoff.

    Returns:
        bool: True if sent successfully, False otherwise.
    """

    settings = SMTPSettings()

    for attempt in range(1, max_retries + 1):
        try:
            with smtplib.SMTP_SSL(
                settings.SMTP_ENDPOINT,
                settings.SMTP_PORT,
                timeout=30,
            ) as server:
                server.login(
                    settings.SMTP_USERNAME,
                    settings.SMTP_SECRET,
                )

                msg = MIMEMultipart()
                msg["From"] = settings.SMTP_SENDER
                msg["To"] = to_email
                msg["Subject"] = subject
                msg.attach(MIMEText(html, "html", "utf-8"))

                errors = server.sendmail(
                    settings.SMTP_SENDER,
                    [to_email],
                    msg.as_string(),
                )

                if errors:
                    logger.error("SMTP refused recipients: %s", errors)
                    return False

            logger.info("Email sent to %s", to_email)
            return True

        except Exception as exc:
            retryable = _is_retryable_exception(exc)

            logger.warning(
                "Email attempt %d/%d failed (retryable=%s): %s",
                attempt,
                max_retries,
                retryable,
                str(exc),
            )

            if not retryable or attempt == max_retries:
                logger.exception("Email sending failed permanently for %s", to_email)
                return False

            # Exponential backoff: 2s, 4s, 8s...
            sleep_time = 2**attempt
            time.sleep(sleep_time)

    return False


def _is_retryable_exception(exc: Exception) -> bool:
    """
    Determine if an SMTP exception is temporary and worth retrying.
    """

    # Network-level issues
    if isinstance(exc, (socket.timeout, OSError)):
        return True
    # Generic SMTP exceptions
    if isinstance(exc, smtplib.SMTPServerDisconnected):
        return True

    if isinstance(exc, smtplib.SMTPConnectError):
        return True

    if isinstance(exc, smtplib.SMTPDataError):
        # Retry only 4xx errors (temporary)
        try:
            code = exc.smtp_code
            return 400 <= code < 500
        except Exception:
            return True

    # Authentication / permanent failures should NOT retry
    if isinstance(
        exc,
        (
            smtplib.SMTPAuthenticationError,
            smtplib.SMTPSenderRefused,
            smtplib.SMTPRecipientsRefused,
        ),
    ):
        return False

    # Retry for generic SMTPException
    if isinstance(exc, smtplib.SMTPException):
        return True

    return False
