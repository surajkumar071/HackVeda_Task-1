from crawler import get_websites
from email_extractor import extract_emails
from smtp_mail_sender import send_email
import re


def load_seed_urls(file_path="seed_urls.txt"):
    urls = []
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            for line in file:
                value = line.strip()
                if not value or value.startswith("#"):
                    continue
                urls.append(value)
    except FileNotFoundError:
        return []
    return urls


def normalize_url(url):
    value = url.strip()
    if not value:
        return value
    if not value.startswith(("http://", "https://")):
        value = "https://" + value
    return value

keyword = input("Enter business keyword: ")

websites = get_websites(keyword)
print(f"Found {len(websites)} website(s) from search")

if not websites:
    seed_urls = load_seed_urls()
    if seed_urls:
        websites = [normalize_url(url) for url in seed_urls if normalize_url(url)]
        print(f"Using {len(websites)} website(s) from seed_urls.txt")

if not websites:
    try:
        manual = input(
            "No websites found from search. Enter website URLs separated by comma (or press Enter to skip): "
        ).strip()
    except EOFError:
        manual = ""
    if manual:
        websites = [normalize_url(url) for url in manual.split(",") if normalize_url(url)]
        print(f"Using {len(websites)} manually provided website(s)")

all_emails = set()

print("\nExtracting Emails...\n")

for site in websites:
    emails = extract_emails(site)
    print(f"{site} -> {len(emails)} email(s)")

    for email in emails:
        clean_email = email.strip().lower()
        if re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", clean_email):
            all_emails.add(clean_email)

# Save emails (both filenames for convenience)
sorted_emails = sorted(all_emails)

with open("emails.txt", "w", encoding="utf-8") as file:
    for email in sorted_emails:
        file.write(email + "\n")

with open("email.txt", "w", encoding="utf-8") as file:
    for email in sorted_emails:
        file.write(email + "\n")

print(f"\n{len(sorted_emails)} email(s) saved in emails.txt and email.txt")

if not sorted_emails:
    print("No emails were found for the current keyword/results.")
    print("Try a more specific keyword like: 'Ashu bakery Mumbai' or 'Ashu digital marketing Delhi'.")

# Send emails
print("\nSending Emails...\n")

if not sorted_emails:
    print("Skipping email sending because no recipients were found.")

for email in all_emails:
    send_email(email)

print("\nProcess Completed ✅")
