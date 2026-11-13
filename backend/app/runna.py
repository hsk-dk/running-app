"""Fetching a person's Runna calendar link. Network only."""
from __future__ import annotations

import re
from urllib.parse import urlparse

import requests

HOST = "cal.runna.com"
MAX_BYTES = 5 * 1024 * 1024


class RunnaLinkError(ValueError):
    """The address is not a Runna calendar link, or it could not be read."""


def check_url(url: str) -> str:
    """Only Runna's own calendar address is accepted (the server fetches it, so anything else would be a way in)."""
    url = (url or "").strip()
    parts = urlparse(url)
    if parts.scheme != "https" or parts.hostname != HOST or parts.port not in (None, 443) or parts.username or parts.password:
        raise RunnaLinkError("Det ligner ikke et Runna-kalenderlink (https://cal.runna.com/…ics)")
    if not re.fullmatch(r"/[A-Za-z0-9_-]{8,128}\.ics", parts.path) or parts.query or parts.fragment:
        raise RunnaLinkError("Det ligner ikke et Runna-kalenderlink (https://cal.runna.com/…ics)")
    return url


def fetch(url: str) -> str:
    response = requests.get(check_url(url), timeout=30, allow_redirects=False, stream=True)
    try:
        if response.status_code != 200:
            raise RunnaLinkError(f"Runna svarede {response.status_code}. Er linket stadig slået til i Runna?")
        body = b""
        for chunk in response.iter_content(65536):
            body += chunk
            if len(body) > MAX_BYTES:
                raise RunnaLinkError("Runna-kalenderen er uventet stor")
    finally:
        response.close()
    text = body.decode("utf-8", errors="replace")
    if "BEGIN:VCALENDAR" not in text:
        raise RunnaLinkError("Svaret fra Runna er ikke en kalender")
    return text
