import requests
import re

EMAIL_REGEX = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"


def normalize_email(value):
    return value.strip().lower()


def is_valid_email(value):
    return bool(re.fullmatch(EMAIL_REGEX, normalize_email(value)))

def extract_emails(url):

    emails = set()

    try:
        # Add headers to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()  # Raise error for bad status codes
        data = response.text

        found_emails = re.findall(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            data
        )

        for email in found_emails:
            cleaned_email = normalize_email(email)
            if is_valid_email(cleaned_email):
                emails.add(cleaned_email)

    except requests.exceptions.Timeout:
        print(f"  Timeout visiting: {url}")
    except requests.exceptions.RequestException as e:
        print(f"  Error visiting: {url} - {type(e).__name__}")
    except Exception as e:
        print(f"  Unexpected error on {url}: {e}")

    return sorted(emails)
