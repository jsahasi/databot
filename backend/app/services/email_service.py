"""Email service: SendGrid (preferred) or Gmail SMTP fallback.

Used for:
- Content sharing links
- Daily improvement-inbox digest (11:59 PM)
"""

import logging
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


async def send_email(
    to: str | list[str],
    subject: str,
    html_body: str,
    attachments: list[Path] | None = None,
    from_name: str = "ON24 Nexus",
) -> bool:
    """Send email via SendGrid (if key available) or Gmail SMTP fallback.

    Returns True if sent successfully, False otherwise.
    """
    recipients = [to] if isinstance(to, str) else to
    if not recipients:
        return False

    if settings.sendgrid_api_key:
        return await _send_via_sendgrid(recipients, subject, html_body, attachments, from_name)
    elif settings.gmail_user and settings.gmail_app_password:
        return _send_via_gmail(recipients, subject, html_body, attachments, from_name)
    else:
        logger.warning("No email service configured (set SENDGRID_API_KEY or GMAIL_USER + GMAIL_APP_PASSWORD)")
        return False


async def _send_via_sendgrid(
    recipients: list[str],
    subject: str,
    html_body: str,
    attachments: list[Path] | None,
    from_name: str,
) -> bool:
    """Send via SendGrid API."""
    try:
        import base64
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import (
            Attachment,
            Content,
            Disposition,
            FileContent,
            FileName,
            FileType,
            Mail,
            To,
        )

        message = Mail(
            from_email=(settings.gmail_user or "noreply@on24.com", from_name),
            to_emails=[To(r) for r in recipients],
            subject=subject,
            html_content=Content("text/html", html_body),
        )

        if attachments:
            for path in attachments:
                if path.exists():
                    data = path.read_bytes()
                    encoded = base64.b64encode(data).decode()
                    attachment = Attachment(
                        FileContent(encoded),
                        FileName(path.name),
                        FileType("text/plain"),
                        Disposition("attachment"),
                    )
                    message.add_attachment(attachment)

        sg = SendGridAPIClient(settings.sendgrid_api_key)
        response = sg.send(message)
        logger.info(f"SendGrid email sent to {recipients} (status {response.status_code})")
        return response.status_code in (200, 201, 202)
    except Exception:
        logger.exception("SendGrid email failed")
        return False


def _send_via_gmail(
    recipients: list[str],
    subject: str,
    html_body: str,
    attachments: list[Path] | None,
    from_name: str,
) -> bool:
    """Send via Gmail SMTP (synchronous — called from async context via thread)."""
    try:
        msg = MIMEMultipart()
        msg["From"] = f"{from_name} <{settings.gmail_user}>"
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject

        msg.attach(MIMEText(html_body, "html"))

        if attachments:
            for path in attachments:
                if path.exists():
                    with open(path, "rb") as f:
                        part = MIMEApplication(f.read(), Name=path.name)
                    part["Content-Disposition"] = f'attachment; filename="{path.name}"'
                    msg.attach(part)

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(settings.gmail_user, settings.gmail_app_password)
            server.sendmail(settings.gmail_user, recipients, msg.as_string())

        logger.info(f"Gmail email sent to {recipients}")
        return True
    except Exception:
        logger.exception("Gmail email failed")
        return False
