import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465

GMAIL_ADDRESS = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]


def send_password_reset_email(to_email: str, token: str) -> None:
    message = EmailMessage()
    message["Subject"] = "Reset your password"
    message["From"] = GMAIL_ADDRESS
    message["To"] = to_email
    message.set_content(
        "You requested a password reset.\n\n"
        f"Reset token: {token}\n\n"
        "This token expires in 30 minutes. If you didn't request this, ignore this email."
    )

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        smtp.send_message(message)
