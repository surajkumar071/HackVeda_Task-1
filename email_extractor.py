import requests
import re
from html import unescape
from urllib.parse import urljoin, urlparse, unquote
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

EMAIL_PATTERN = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
BAD_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".js", ".css", ".ico", ".pdf")
COMMON_CONTACT_PATHS = ["/contact", "/contact-us", "/about", "/about-us", "/support", "/team"]


session = requests.Session()
retry_strategy = Retry(
    total=2,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)


def _normalize_url(url):
    value = url.strip()
    if not value:
        return value
    if not value.startswith(("http://", "https://")):
        value = "https://" + value
    return value


def _fetch_html(url, timeout=8):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    }
    response = session.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.text


def _same_domain(url, domain):
    return urlparse(url).netloc == domain


def _normalize_obfuscated_emails(html):
    text = unescape(unquote(html))
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*\[at\]\s*|\s*\(at\)\s*", "@", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*\[dot\]\s*|\s*\(dot\)\s*", ".", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+at\s+", "@", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+dot\s+", ".", text, flags=re.IGNORECASE)
    return text


def _clean_emails(emails):
    cleaned = set()
    for email in emails:
        value = email.strip().lower().strip(".,;:<>\"'()[]{}")
        if not value:
            continue
        if value.endswith(BAD_SUFFIXES):
            continue
        cleaned.add(value)
    return cleaned


def _get_contact_like_links(base_url, html, max_links=3):
    domain = urlparse(base_url).netloc
    links = []

    hrefs = re.findall(r'href=["\'](.*?)["\']', html, flags=re.IGNORECASE)

    for href in hrefs:
        candidate = urljoin(base_url, href)
        candidate_l = candidate.lower()

        if not _same_domain(candidate, domain):
            continue

        if any(word in candidate_l for word in ["contact", "about", "support", "team"]):
            if candidate not in links:
                links.append(candidate)

        if len(links) >= max_links:
            break

    for path in COMMON_CONTACT_PATHS:
        candidate = urljoin(base_url, path)
        if candidate not in links:
            links.append(candidate)
        if len(links) >= max_links + len(COMMON_CONTACT_PATHS):
            break

    return links


def _extract_from_html(html):
    normalized_html = _normalize_obfuscated_emails(html)
    emails = set(re.findall(EMAIL_PATTERN, normalized_html))
    mailto_emails = re.findall(
        r"mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
        normalized_html,
        flags=re.IGNORECASE,
    )
    emails.update(mailto_emails)
    return emails


def extract_emails(url):
    base_url = _normalize_url(url)
    emails = set()

    try:
        html = _fetch_html(base_url)
        emails.update(_extract_from_html(html))

        for extra_url in _get_contact_like_links(base_url, html):
            try:
                extra_html = _fetch_html(extra_url)
                emails.update(_extract_from_html(extra_html))
            except Exception:
                continue

    except Exception as error:
        print(f"Error visiting: {base_url} ({error})")

    return list(_clean_emails(emails))
