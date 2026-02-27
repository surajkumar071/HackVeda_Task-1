import os
import base64
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


def _load_dotenv(file_path=".env"):
    if not os.path.exists(file_path):
        return

    try:
        with open(file_path, "r", encoding="utf-8") as env_file:
            for line in env_file:
                value = line.strip()
                if not value or value.startswith("#") or "=" not in value:
                    continue

                key, raw = value.split("=", 1)
                key = key.strip()
                raw = raw.strip().strip('"').strip("'")

                if key and key not in os.environ:
                    os.environ[key] = raw
    except Exception:
        pass


_load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
CLIENT_SECRET_FILE = os.getenv("GMAIL_CLIENT_SECRET_FILE", "client_secret.json")
TOKEN_FILE = os.getenv("GMAIL_TOKEN_FILE", "gmail_token.json")


def _get_gmail_service():
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRET_FILE):
                raise FileNotFoundError(
                    f"Client secret file not found: {CLIENT_SECRET_FILE}. "
                    "Set GMAIL_CLIENT_SECRET_FILE or place client_secret.json in project root."
                )

            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def _build_message(sender_email, receiver, subject, body):
    message = MIMEText(body)
    message["to"] = receiver
    message["from"] = sender_email
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {"raw": raw}


def send_email(receiver):

    sender_email = os.getenv("GMAIL_SENDER_EMAIL", "").strip()
    if not sender_email:
        print("Set GMAIL_SENDER_EMAIL before sending emails.")
        return

    subject = "Business Promotion"
    body = (
        "Hello,\n\n"
        "This is an automated marketing email sent using Python Automation Project.\n\n"
        "Thank You."
    )

    try:
        service = _get_gmail_service()
        email_message = _build_message(sender_email, receiver, subject, body)
        service.users().messages().send(userId="me", body=email_message).execute()

        print("Email sent to:", receiver)

    except Exception as error:
        print(f"Failed to send: {receiver} ({error})")
