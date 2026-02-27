import time

from email_extractor import extract_emails, is_valid_email, normalize_email
from smtp_mail_sender import send_email


def ask_yes_no(prompt, default=True):
    suffix = "Y/n" if default else "y/N"
    value = input(f"{prompt} ({suffix}): ").strip().lower()

    if not value:
        return default
    return value in {"y", "yes"}


def ask_delay_seconds():
    value = input("Delay between emails in seconds (default 1): ").strip()
    if not value:
        return 1.0

    try:
        delay = float(value)
        if delay < 0:
            return 1.0
        return delay
    except ValueError:
        return 1.0

url = input("Enter website URL: ").strip()

# Validate URL format
if not url.startswith(('http://', 'https://')):
    url = 'https://' + url

all_emails = set()
invalid_count = 0

print("\nExtracting Emails...\n")

emails = extract_emails(url)

if emails:
    print(f"Found {len(emails)} email(s) on {url}")
    for email in emails:
        cleaned_email = normalize_email(email)
        if is_valid_email(cleaned_email):
            all_emails.add(cleaned_email)
        else:
            invalid_count += 1
else:
    print(f"No emails found on {url}")

# Save emails
if all_emails:
    with open("email.txt", "w") as file:
        for email in sorted(all_emails):
            file.write(email + "\n")
    print(f"\n{len(all_emails)} unique email(s) saved in email.txt")
else:
    print("\nNo emails extracted. email.txt is empty.")

# Send emails
if all_emails:
    dry_run = ask_yes_no("Dry run only (show recipients, don't send)?", default=True)
    delay_seconds = ask_delay_seconds()

    print("\nSending Emails...\n")

    sent_count = 0
    failed_count = 0
    skipped_count = 0

    for index, email in enumerate(sorted(all_emails), start=1):
        if dry_run:
            print(f"[DRY RUN] {index}. {email}")
            skipped_count += 1
            continue

        result = send_email(email)
        status = (result or {}).get("status")
        if status == "sent":
            sent_count += 1
        elif status == "skipped":
            skipped_count += 1
        else:
            failed_count += 1

        if delay_seconds > 0 and index < len(all_emails):
            time.sleep(delay_seconds)

    print("\nRun Summary")
    print(f"- Extracted (raw): {len(emails)}")
    print(f"- Valid unique recipients: {len(all_emails)}")
    print(f"- Invalid skipped before save/send: {invalid_count}")
    print(f"- Sent: {sent_count}")
    print(f"- Failed: {failed_count}")
    print(f"- Dry-run/Skipped: {skipped_count}")
else:
    print("\nNo emails to send.")

print("\nProcess Completed ✅")
