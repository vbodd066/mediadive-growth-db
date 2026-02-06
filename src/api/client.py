"""
Resilient HTTP client for the MediaDive REST API.

Features:
- Automatic retries with exponential backoff
- Rate-limiting between requests
- Response caching to disk (avoids re-fetching on restart)
- Paginated-list iterator
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Iterator

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.config import BASE_URL, RAW_DIR, REQUEST_DELAY, TIMEOUT

log = logging.getLogger(__name__)

HEADERS = {
    "Accept": "application/json",
    "X-Requested-With": "XMLHttpRequest",
}

# ── Session with automatic retries ─────────────────────────
_session: requests.Session | None = None


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update(HEADERS)
        retry = Retry(
            total=4,
            backoff_factor=1.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        _session.mount("https://", HTTPAdapter(max_retries=retry))
        _session.mount("http://", HTTPAdapter(max_retries=retry))
    return _session


# ── Low-level GET ───────────────────────────────────────────

def get(endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """GET a JSON response from MediaDive, with retries and rate-limiting."""
    url = f"{BASE_URL}{endpoint}"
    session = _get_session()

    log.debug("GET %s  params=%s", url, params)
    r = session.get(url, params=params, timeout=TIMEOUT)

    r.raise_for_status()

    content_type = r.headers.get("Content-Type", "")
    if "application/json" not in content_type:
        log.error(
            "Non-JSON response from %s  status=%d  content_type=%s",
            r.url,
            r.status_code,
            content_type,
        )
        raise RuntimeError(f"Expected JSON, got {content_type} from {r.url}")

    time.sleep(REQUEST_DELAY)
    return r.json()  # type: ignore[no-any-return]


def get_cached(
    endpoint: str,
    params: dict[str, Any] | None = None,
    *,
    cache_dir: str = "api_cache",
) -> dict[str, Any]:
    """
    GET with local JSON disk cache.

    Cache key is derived from the full URL + params so re-runs skip
    already-fetched resources.  Delete ``data/raw/api_cache/`` to
    force a full re-fetch.
    """
    cache_root = RAW_DIR / cache_dir
    cache_root.mkdir(parents=True, exist_ok=True)

    key_src = f"{endpoint}|{sorted(params.items()) if params else ''}"
    key = hashlib.sha256(key_src.encode()).hexdigest()[:16]
    cache_path = cache_root / f"{key}.json"

    if cache_path.exists():
        log.debug("Cache hit: %s → %s", endpoint, cache_path.name)
        return json.loads(cache_path.read_text())

    data = get(endpoint, params)

    cache_path.write_text(json.dumps(data, indent=2))
    return data


# ── Paginated list iterator ─────────────────────────────────

def paginate(
    endpoint: str,
    *,
    limit: int = 200,
    extra_params: dict[str, Any] | None = None,
    use_cache: bool = True,
) -> Iterator[list[dict[str, Any]]]:
    """
    Yield successive pages of ``data`` items from a paginated endpoint.

    Stops when the API returns an empty ``data`` list.
    """
    offset = 0
    page = 0
    fetcher = get_cached if use_cache else get

    while True:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if extra_params:
            params.update(extra_params)

        log.info("Fetching %s  page=%d  offset=%d", endpoint, page, offset)
        resp = fetcher(endpoint, params)

        items = resp.get("data", [])
        if not items:
            break

        yield items

        # If fewer items than limit, we've reached the last page
        if len(items) < limit:
            break

        offset += limit
        page += 1


def get_detail(
    endpoint: str,
    *,
    use_cache: bool = True,
) -> dict[str, Any]:
    """
    Fetch a single-resource detail endpoint, returning the ``data`` payload.

    Raises ValueError if the response has no ``data`` key.
    """
    fetcher = get_cached if use_cache else get
    resp = fetcher(endpoint)
    if "data" not in resp:
        raise ValueError(f"No 'data' key in response from {endpoint}")
    return resp["data"]  # type: ignore[no-any-return]

