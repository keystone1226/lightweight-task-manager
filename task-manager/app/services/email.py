"""Optional email notification service via SMTP."""

import smtplib
from email.mime.text import MIMEText

from app.config import SMTP_FROM, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER


def is_email_configured() -> bool:
    return bool(SMTP_HOST)


def send_email(to: str, subject: str, body: str) -> bool:
    """Send an email. Returns True on success, False on failure."""
    if not is_email_configured():
        return False
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM
        msg["To"] = to

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            if SMTP_USER:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False
