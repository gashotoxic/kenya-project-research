"""Source URL validation and optional live reachability checks.

No secrets here: requests are plain HTTPS GET/HEAD with a static UA.
"""
from __future__ import annotations

import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from .schema import normalize_url, valid_url

USER_AGENT = "kenya-project-research/1.0 (+https://github.com/gashotoxic/kenya-project-research)"
REQUEST_TIMEOUT = 6.0
MAX_WORKERS = 8


def validate_sources(urls) -> list:
    """Return the distinct, well-formed http(s) URLs (order preserved)."""
    seen = set()
    clean = []
    for url in urls:
        if not valid_url(url):
            continue
        norm = normalize_url(url)
        if norm not in seen:
            seen.add(norm)
            clean.append(url)
    return clean


def _probe(url: str, timeout: float) -> dict:
    status = "unreachable:unknown"
    for method in ("HEAD", "GET"):
        request = urllib.request.Request(
            url, method=method, headers={"User-Agent": USER_AGENT}
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                status = f"ok:{response.status}"
                break
        except urllib.error.HTTPError as exc:
            status = f"ok:{exc.code}"
            break
        except Exception as exc:  # DNS, TLS, timeout, ...
            status = f"unreachable:{type(exc).__name__}"
            if method == "GET":
                break
    return {"url": url, "status": status}


def check_live(urls, timeout: float = REQUEST_TIMEOUT) -> list:
    """Best-effort reachability probe, parallel and bounded. Never raises.

    A URL is "ok:<code>" when the server answered anything (even 403/404 --
    the source exists), "unreachable:<reason>" otherwise.
    """
    clean = validate_sources(urls)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        return list(pool.map(lambda u: _probe(u, timeout), clean))
