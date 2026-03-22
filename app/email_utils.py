import os
import resend

APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:8501")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "info@pacey32.com")

if not RESEND_API_KEY:
    raise ValueError("RESEND_API_KEY is missing")

resend.api_key = RESEND_API_KEY


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

    resend.Emails.send({
        "from": EMAIL_FROM,
        "to": [email],
        "subject": "Verify your account",
        "html": html,
    })


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

    resend.Emails.send({
        "from": EMAIL_FROM,
        "to": [email],
        "subject": "Reset your password",
        "html": html,
    })