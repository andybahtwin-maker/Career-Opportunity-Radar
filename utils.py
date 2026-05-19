from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from config import HTTP_TIMEOUT_SECONDS, USER_AGENT


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return clean_text(" ".join(self.parts))


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    value = html.unescape(value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def strip_html(value: str | None) -> str:
    if not value:
        return ""
    parser = TextExtractor()
    try:
        parser.feed(value)
        return parser.text()
    except Exception:
        return clean_text(value)


def extract_readable_text(html_value: str | None) -> str:
    if not html_value:
        return ""
    html_value = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", html_value)
    html_value = re.sub(r"(?is)<!--.*?-->", " ", html_value)
    return strip_html(html_value)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def fetch_json(url: str) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
        content_type = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(content_type, errors="replace")


def probe_url(url: str) -> dict:
    """Return a small HTTP diagnostic record without raising on HTTP errors."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            return {
                "url": url,
                "status": response.status,
                "ok": 200 <= response.status < 400,
                "error": "",
                "anti_bot_likely": False,
            }
    except urllib.error.HTTPError as exc:
        return {
            "url": url,
            "status": exc.code,
            "ok": False,
            "error": str(exc),
            "anti_bot_likely": exc.code in {401, 403, 429},
        }
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {
            "url": url,
            "status": None,
            "ok": False,
            "error": str(exc),
            "anti_bot_likely": False,
        }


def safe_fetch_json(url: str) -> tuple[Any | None, str | None]:
    try:
        return fetch_json(url), None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return None, str(exc)


def safe_fetch_text(url: str) -> tuple[str, str | None]:
    try:
        return fetch_text(url), None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return "", str(exc)


def stable_job_id(company: str, title: str, url: str) -> str:
    basis = url.strip() or f"{company}|{title}".lower()
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    value = str(value).strip()
    if not value:
        return None

    if value.isdigit():
        timestamp = int(value)
        if timestamp > 10_000_000_000:
            timestamp = timestamp / 1000
        return datetime.fromtimestamp(timestamp, timezone.utc).date()

    value = value.replace("Z", "+00:00")
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(value[:20], fmt).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def posting_age_days(date_posted: str | None, first_seen: str | None = None) -> int | None:
    posted = parse_date(date_posted) or parse_date(first_seen)
    if not posted:
        return None
    return (datetime.now(timezone.utc).date() - posted).days
