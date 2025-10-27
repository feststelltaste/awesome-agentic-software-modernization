#!/usr/bin/env python3
"""
Link checker for awesome-agentic-software-modernization README.md
Validates all HTTP/HTTPS links in the markdown file.
"""

import re
import sys
import time
from urllib.parse import urlparse
from typing import List, Tuple
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def create_session() -> requests.Session:
    """Create a requests session with retry logic and timeout."""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Set headers to avoid being blocked
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })

    return session


def extract_links(markdown_file: str) -> List[Tuple[int, str]]:
    """Extract all HTTP/HTTPS links from markdown file with line numbers."""
    links = []

    with open(markdown_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, start=1):
            # Find markdown links [text](url)
            markdown_links = re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', line)
            for text, url in markdown_links:
                if url.startswith(('http://', 'https://')):
                    links.append((line_num, url))

            # Find bare URLs (not in markdown format)
            bare_urls = re.findall(r'(?<!\()https?://[^\s\)]+', line)
            for url in bare_urls:
                links.append((line_num, url))

    return links


def check_link(session: requests.Session, url: str, timeout: int = 10) -> Tuple[bool, str, int]:
    """
    Check if a URL is reachable.
    Returns: (is_valid, status_message, status_code)
    """
    try:
        response = session.head(url, timeout=timeout, allow_redirects=True)

        # If HEAD fails, try GET (some servers don't support HEAD)
        if response.status_code >= 400:
            response = session.get(url, timeout=timeout, allow_redirects=True)

        if response.status_code < 400:
            return True, "OK", response.status_code
        else:
            return False, f"HTTP {response.status_code}", response.status_code

    except requests.exceptions.Timeout:
        return False, "Timeout", 0
    except requests.exceptions.ConnectionError:
        return False, "Connection Error", 0
    except requests.exceptions.TooManyRedirects:
        return False, "Too Many Redirects", 0
    except requests.exceptions.RequestException as e:
        return False, f"Request Error: {str(e)}", 0
    except Exception as e:
        return False, f"Unknown Error: {str(e)}", 0


def main():
    """Main function to check all links in README.md"""
    readme_file = "README.md"

    print("🔍 Extracting links from README.md...")
    links = extract_links(readme_file)

    if not links:
        print("❌ No links found in README.md")
        sys.exit(1)

    print(f"📋 Found {len(links)} links to check\n")

    session = create_session()

    broken_links = []
    valid_links = []

    for idx, (line_num, url) in enumerate(links, start=1):
        print(f"[{idx}/{len(links)}] Checking line {line_num}: {url[:80]}{'...' if len(url) > 80 else ''}")

        is_valid, message, status_code = check_link(session, url)

        if is_valid:
            valid_links.append((line_num, url, status_code))
            print(f"  ✅ {message} ({status_code})")
        else:
            broken_links.append((line_num, url, message))
            print(f"  ❌ {message}")

        # Be nice to servers - add delay between requests
        if idx < len(links):
            time.sleep(0.5)

        print()

    # Summary
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    print(f"✅ Valid links: {len(valid_links)}")
    print(f"❌ Broken links: {len(broken_links)}")
    print(f"📊 Total links checked: {len(links)}")

    if broken_links:
        print("\n" + "="*80)
        print("❌ BROKEN LINKS")
        print("="*80)
        for line_num, url, message in broken_links:
            print(f"Line {line_num}: {url}")
            print(f"  Error: {message}\n")

        sys.exit(1)
    else:
        print("\n🎉 All links are valid!")
        sys.exit(0)


if __name__ == "__main__":
    main()
