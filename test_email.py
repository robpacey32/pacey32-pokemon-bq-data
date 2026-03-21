# test_email.py
from app.email_utils import send_verification_email

send_verification_email("rob.pacey32@gmail.com", "test123")
print("Email sent")