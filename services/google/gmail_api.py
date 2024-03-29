import base64
import json
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def construct_mime_message(email_components):
    """
    Constructs a MIME message from email components.
    """
    message = MIMEMultipart()
    message["to"] = ", ".join(email_components["recipient"])
    message["from"] = email_components["sender"]
    message["subject"] = email_components["subject"]

    msg = MIMEText(email_components["body"], "plain")
    message.attach(msg)

    return message.as_string()

def send_email(access_token, email_components):
    """
    Sends an email using the Gmail API.
    Requires email components with 'sender', 'recipient', 'subject' and 'body'
    """

    url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    raw_mime_message = construct_mime_message(email_components)
    encoded_message = base64.urlsafe_b64encode(raw_mime_message.encode("utf-8")).decode("utf-8")

    body = {"raw": encoded_message}
    response = requests.post(url, headers=headers, data=json.dumps(body))

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to send email: {response.text}")
