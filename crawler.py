from googlesearch import search
import requests
import re
from urllib.parse import unquote, urlparse, parse_qs


def _duckduckgo_fallback(query, max_results=15):
    urls = []
    seen = set()

    try:
        response = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
            },
            timeout=10,
        )
        response.raise_for_status()

        html = response.text
        raw_links = re.findall(r'href="(//duckduckgo.com/l/\?uddg=[^"]+)"', html)

        for raw in raw_links:
            parsed = urlparse("https:" + raw)
            target = parse_qs(parsed.query).get("uddg", [""])[0]
            target = unquote(target)

            if target.startswith("http") and target not in seen:
                seen.add(target)
                urls.append(target)

            if len(urls) >= max_results:
                break
    except Exception:
        return []

    return urls


def _bing_fallback(query, max_results=15):
    urls = []
    seen = set()

    try:
        response = requests.get(
            "https://www.bing.com/search",
            params={"q": query},
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
            },
            timeout=10,
        )
        response.raise_for_status()

        html = response.text
        matches = re.findall(r'<h2><a href="(https?://[^"]+)"', html, flags=re.IGNORECASE)

        for link in matches:
            cleaned = link.split("&", 1)[0]
            if cleaned not in seen:
                seen.add(cleaned)
                urls.append(cleaned)
            if len(urls) >= max_results:
                break
    except Exception:
        return []

    return urls

def get_websites(keyword):
    websites = []
    seen = set()

    print("Searching Google...")

    queries = [
        keyword,
        f"{keyword} business official website",
        f"{keyword} contact email",
        f"{keyword} contact us",
    ]

    for query in queries:
        try:
            for url in search(query, num_results=10):
                if url not in seen:
                    seen.add(url)
                    websites.append(url)
        except Exception:
            continue

    if not websites:
        print("Google returned no results, trying fallback search...")
        for query in queries:
            for url in _duckduckgo_fallback(query, max_results=10):
                if url not in seen:
                    seen.add(url)
                    websites.append(url)

    if not websites:
        print("DuckDuckGo returned no results, trying Bing fallback...")
        for query in queries:
            for url in _bing_fallback(query, max_results=10):
                if url not in seen:
                    seen.add(url)
                    websites.append(url)

    return websites
