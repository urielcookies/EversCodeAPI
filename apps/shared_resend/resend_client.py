import os
import resend
from dotenv import load_dotenv

load_dotenv()

RESEND_API = os.getenv("RESEND_API")
resend.api_key = RESEND_API

def send_contact_form_email(to_emails, subject, html_content, from_email="noreply@everscode.com"):
    params = {
        "from": from_email,
        "to": to_emails if isinstance(to_emails, list) else [to_emails],
        "subject": subject,
        "html": html_content,
    }
    try:
        response = resend.Emails.send(params)
        print(f"Email sent successfully: {response}")
        return response
    except Exception as e:
        print(f"Failed to send email: {e}")
        raise
