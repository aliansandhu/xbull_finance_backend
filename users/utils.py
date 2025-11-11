import requests
import json

from django.conf import settings


def send_email(sender, recipients, name, link, email_type):
    url = 'https://api.brevo.com/v3/smtp/email'
    headers = {
        'accept': 'application/json',
        'api-key': settings.SMTP_API_KEY,
        'content-type': 'application/json',
    }

    subject, template_id = get_email_subject_and_template(email_type)
    if not subject or not template_id:
        print(f"Invalid email type: {email_type}")
        return

    data = {
        "sender": {
            "email": sender["email"],
            "name": sender["name"],
        },
        "subject": subject,
        "templateId": template_id,
        "params": {
            "name": name,
            "verification_url": link,
        },
        "to": [{"email": recipient['email']} for recipient in recipients]
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        print('Email sent successfully:', response.json())
    except requests.exceptions.HTTPError as err:
        print(f"HTTP error occurred: {err}")
    except Exception as e:
        print(f"An error occurred: {e}")


def get_email_subject_and_template(email_type):
    """Returns the subject and template ID based on email type."""
    email_data = {
        'signup': ("Account Verification", 1),
        'forgot_password': ("Forgot Password", 2)
    }

    return email_data.get(email_type, (None, None))
