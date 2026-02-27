import os
import base64
import re
import json
import smtplib
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
REDIRECT_PORT = int(os.getenv("GMAIL_REDIRECT_PORT", "8080"))
MAIL_MODE = os.getenv("MAIL_MODE", "smtp").strip().lower()
EMAIL_REGEX = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
DEFAULT_SUBJECT = "Quick introduction"
DEFAULT_BODY = (
    "Hello,\n\n"
    "I am reaching out regarding a possible collaboration.\n"
    "Please let me know if we can connect.\n\n"
    "Regards"
)


def _get_client_type(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        if "installed" in data:
            return "installed"
        if "web" in data:
            return "web"
    except Exception:
        return "unknown"
    return "unknown"


def _startup_oauth_config_check(file_path):
    if not os.path.exists(file_path):
        print(
            f"OAuth config not found: {file_path}. "
            "Place client_secret.json in project root or set GMAIL_CLIENT_SECRET_FILE in .env"
        )
        return

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except Exception as error:
        print(f"Could not read OAuth config file: {file_path} ({error})")
        return

    if "installed" in data:
        return

    if "web" in data:
        redirect_uris = data.get("web", {}).get("redirect_uris", []) or []
        required = f"http://localhost:{REDIRECT_PORT}/"
        if required not in redirect_uris:
            print(
                "OAuth config warning: detected 'web' client without required redirect URI. "
                f"Add this in Google Cloud Console -> OAuth client redirect URIs: {required}"
            )
        return

    print("OAuth config warning: unrecognized client type. Use Desktop App OAuth client JSON.")


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

            client_type = _get_client_type(CLIENT_SECRET_FILE)
            if client_type == "web":
                print(
                    "Detected Google OAuth 'web' client secret. "
                    f"Add this exact Authorized redirect URI in Google Cloud Console: http://localhost:{REDIRECT_PORT}/"
                )

            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=REDIRECT_PORT, host="localhost")

        with open(TOKEN_FILE, "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


if MAIL_MODE != "smtp":
    _startup_oauth_config_check(CLIENT_SECRET_FILE)


def _build_message(sender_email, receiver, subject, body):
    message = MIMEText(body)
    message["to"] = receiver
    message["from"] = sender_email
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {"raw": raw}


def _get_authenticated_email(service):
    profile = service.users().getProfile(userId="me").execute()
    return profile.get("emailAddress", "").strip()


def _send_via_smtp(sender_email, app_password, receiver, subject, body):
    message = MIMEText(body)
    message["to"] = receiver
    message["from"] = sender_email
    message["subject"] = subject

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
        server.starttls()
        server.login(sender_email, app_password)
        server.sendmail(sender_email, [receiver], message.as_string())


def send_email(receiver):
    receiver = receiver.strip().lower()
    if not re.fullmatch(EMAIL_REGEX, receiver):
        print(f"Skipping invalid recipient: {receiver}")
        return {"status": "skipped", "recipient": receiver, "reason": "invalid"}

    configured_sender = os.getenv("GMAIL_SENDER_EMAIL", "").strip().lower()
    app_password = os.getenv("GMAIL_APP_PASSWORD", "").strip().replace(" ", "")

    subject = DEFAULT_SUBJECT
    body = DEFAULT_BODY

    try:
        if MAIL_MODE == "smtp":
            if not configured_sender:
                print("GMAIL_SENDER_EMAIL is not set in .env")
                return {"status": "failed", "recipient": receiver, "reason": "missing_sender"}
            if not app_password:
                print(
                    "GMAIL_APP_PASSWORD is empty in .env. "
                    "Set your Gmail App Password to send emails in SMTP mode."
                )
                return {"status": "failed", "recipient": receiver, "reason": "missing_app_password"}

            _send_via_smtp(configured_sender, app_password, receiver, subject, body)
            print(f"Email sent to: {receiver} (via SMTP app password)")
            return {"status": "sent", "recipient": receiver}

        service = _get_gmail_service()
        authenticated_sender = _get_authenticated_email(service)
        sender_email = authenticated_sender or configured_sender

        if configured_sender and authenticated_sender and configured_sender != authenticated_sender:
            print(
                f"Note: GMAIL_SENDER_EMAIL ({configured_sender}) differs from authorized Gmail ({authenticated_sender}). "
                f"Using authorized Gmail account."
            )

        if not sender_email:
            print("Could not determine sender email. Authorize Gmail and set GMAIL_SENDER_EMAIL in .env.")
            return {"status": "failed", "recipient": receiver, "reason": "missing_oauth_sender"}

        email_message = _build_message(sender_email, receiver, subject, body)
        result = service.users().messages().send(userId="me", body=email_message).execute()

        print(f"Email sent to: {receiver} (message id: {result.get('id', 'N/A')})")
        return {"status": "sent", "recipient": receiver}

    except smtplib.SMTPAuthenticationError as error:
        print(
            "Failed to authenticate with Gmail SMTP. "
            "Use a Gmail App Password (16 characters), not your normal Gmail password."
        )
        print(
            "Steps: Google Account -> Security -> 2-Step Verification ON -> App passwords -> Mail -> "
            "paste generated password into GMAIL_APP_PASSWORD in .env"
        )
        print(f"Failed to send: {receiver} ({error})")
        return {"status": "failed", "recipient": receiver, "reason": "smtp_auth_error"}
    except Exception as error:
        if "redirect_uri_mismatch" in str(error):
            print(
                "OAuth redirect URI mismatch. In Google Cloud Console -> OAuth Client -> Authorized redirect URIs, "
                f"add: http://localhost:{REDIRECT_PORT}/"
            )
            if configured_sender:
                print(
                    "Quick workaround: set GMAIL_APP_PASSWORD in .env to send via SMTP without OAuth browser redirect."
                )
        print(f"Failed to send: {receiver} ({error})")
        return {"status": "failed", "recipient": receiver, "reason": "send_exception"}
