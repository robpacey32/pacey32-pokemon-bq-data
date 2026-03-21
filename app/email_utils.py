import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:8501")

SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER)


def send_email(to_email: str, subject: str, html_body: str):
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASS:
        raise ValueError("SMTP email settings are missing")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email

    text_body = "Please view this email in HTML format."
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_FROM, to_email, msg.as_string())


def send_verification_email(email: str, token: str):
    verify_url = f"{APP_BASE_URL}/Account?verify_token={token}"

    html = f"""
    <html>
      <body>
        <h2>Verify your email</h2>
        <p>Thanks for signing up.</p>
        <p>Please click the link below to verify your email address:</p>
        <p><a href="{verify_url}">Verify my email</a></p>
        <p>If you did not create this account, you can ignore this email.</p>
      </body>
    </html>
    """

    send_email(email, "Verify your account", html)


def send_password_reset_email(email: str, token: str):
    reset_url = f"{APP_BASE_URL}/Account?reset_token={token}"

    html = f"""
    <html>
      <body>
        <h2>Reset your password</h2>
        <p>We received a request to reset your password.</p>
        <p>Click the link below to choose a new password:</p>
        <p><a href="{reset_url}">Reset my password</a></p>
        <p>If you did not request this, you can ignore this email.</p>
      </body>
    </html>
    """

    send_email(email, "Reset your password", html)