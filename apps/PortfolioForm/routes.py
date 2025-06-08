import os
from flask import request, render_template_string, abort
from apps.PortfolioForm import portfoliocontactform_bp
from datetime import datetime, timedelta
from dateutil import parser
import resend
from dotenv import load_dotenv
from apps.shared_pocketbase.pocketbase_client import get_pocketbase_client
from apps.shared_resend.resend_client import send_contact_form_email

load_dotenv()

RESEND_API = os.getenv("RESEND_API")
resend.api_key = RESEND_API  # Set the API key globally

pb_client = get_pocketbase_client()

@portfoliocontactform_bp.route('/', methods=['POST'])
def handle_form():
    # Honeypot field (bots fill it, users don't)
    if request.form.get('website'):
        return "Bot detected", 400

    first_name = request.form.get('firstName', '').strip()
    last_name = request.form.get('lastName', '').strip()
    email = request.form.get('email', '').strip().lower()
    phone = request.form.get('phone', '').strip()
    message = request.form.get('message', '').strip()
    ip_address = request.remote_addr

    # Validate required fields
    if not all([first_name, last_name, email, phone, message]):
        abort(400, "All fields (first name, last name, email, phone, message) are required.")

    name = f"{first_name} {last_name}"

    # Check for recent submissions from this IP
    now = datetime.utcnow()
    twenty_four_hours_ago = (now - timedelta(hours=24)).isoformat()
    filter_expr = f'(ip_address = "{ip_address}" || email = "{email}") && created > "{twenty_four_hours_ago}"'
    recent = pb_client.collection("portfolio_contactform").get_list(1, 1, {"filter": filter_expr})
    if recent.total_items > 0:
        html = f"""
            <section class="error-section">
                <div style="max-width: 600px; margin: auto; padding: 30px; background: #2a2a2a; border: 1px solid #ff4d4d; border-radius: 8px; text-align: center;">
                    <h2 style="color: #ff6b6b;">Too Many Requests</h2>
                    <p style="color: #cccccc;">You <strong>{name}</strong> have submitted the form already so take a break. Please wait 24 hours before trying again.</p>
                </div>
            </section>
            """
        return render_template_string(html)

    # Submit to PocketBase and get the created record
    record = pb_client.collection("portfolio_contactform").create({
        "name": name,
        "email": email,
        "phone": phone,
        "message": message,
        "ip_address": ip_address
    })

    # Format the created timestamp (record.created is already a datetime object)
    if isinstance(record.created, str):
        # If it's a string, parse it first
        created_dt = parser.isoparse(record.created)
    else:
        # If it's already a datetime object, use it directly
        created_dt = record.created
    
    created_human = created_dt.strftime("%B %d, %Y at %-I:%M %p UTC")

    # Build the email body with the formatted timestamp
    html_body = build_email_html(
        name, email, phone, message, ip_address, created_human
    )

    try:
        send_contact_form_email(
            to_emails=["evergarcia621@outlook.com"],
            subject="New Contact Form Submission",
            html_content=html_body
        )
    except Exception as e:
        print(f"Failed to send email: {e}")

    return render_template_string(THANK_YOU_HTML)

THANK_YOU_HTML = """
        <section id="contact" class="section contact-section">
            <div class="container text-center">
                <h2 class="contact-title mb-8 text-teal-400">Thank You!</h2>
                <p class="text-lg">Your message has been successfully submitted.</p>
            </div>
        </section>
"""

def build_email_html(name, email, phone, message, ip_address, submitted_at):
    return f"""
    <!DOCTYPE html>
    <html lang="en" >
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: #f5f8fa;
            color: #333;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            background: #fff;
            max-width: 600px;
            margin: auto;
            border-radius: 8px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        h1 {{
            color: #0077cc;
            font-size: 24px;
            margin-bottom: 20px;
            border-bottom: 2px solid #0077cc;
            padding-bottom: 8px;
        }}
        p {{
            font-size: 16px;
            line-height: 1.5;
            margin: 12px 0;
        }}
        strong {{
            color: #004466;
        }}
        .footer {{
            font-size: 12px;
            color: #999;
            margin-top: 30px;
            text-align: center;
        }}
        </style>
    </head>
    <body>
        <div class="container">
        <h1>New Contact Form Submission</h1>

        <p><strong>Name:</strong> {name}</p>
        <p><strong>Email:</strong> {email}</p>
        <p><strong>Phone:</strong> {phone}</p>
        <p><strong>Message:</strong></p>
        <p style="background:#f0f4f8; padding:15px; border-radius:5px; white-space: pre-line;">{message}</p>
        <p><strong>IP Address:</strong> {ip_address}</p>
        <p><strong>Submitted At:</strong> {submitted_at}</p>

        <div class="footer">
            This message was sent from everscode.com contact form.
        </div>
        </div>
    </body>
    </html>
    """