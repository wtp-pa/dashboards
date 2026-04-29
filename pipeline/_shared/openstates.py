"""
Shared OpenStates v3 HTTP client.

Originally lived inline in pipeline/legislation/fetch_bills.py. Lifted out so
the elected-officials fetchers (and any future candidate-tracking dashboard)
can share auth, rate-limit handling, retry, and pagination — and so we have
a single place to update when OpenStates changes their API.

Usage:

    from pipeline._shared.openstates import OpenStatesClient

    client = OpenStatesClient.from_env()
    data = client.get("/bills", {"jurisdiction": "pa", "session": "2025-2026"})

    for result in client.paginate("/bills", {"jurisdiction": "pa", "session": "2025-2026"},
                                  include=["sponsorships", "abstracts"]):
        process(result)

The free tier is aggressively rate-limited; the default 6-second
inter-request delay was tuned empirically. Tighten only with care.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Iterable, Iterator

import requests

API_BASE = "https://v3.openstates.org"
DEFAULT_USER_AGENT = "wtpppa-dashboards/1.0"
DEFAULT_DELAY_SEC = 6.0
DEFAULT_PER_PAGE = 20  # OpenStates v3 caps at 20 with non-default sort
DEFAULT_TIMEOUT_SEC = 60
MAX_RETRIES = 4


class OpenStatesError(RuntimeError):
    """Raised when OpenStates returns an unrecoverable error."""


class OpenStatesClient:
    def __init__(
        self,
        api_key: str,
        user_agent: str = DEFAULT_USER_AGENT,
        delay_sec: float = DEFAULT_DELAY_SEC,
    ) -> None:
        if not api_key:
            raise OpenStatesError("api_key is required")
        self._api_key = api_key
        self._headers = {"X-API-KEY": api_key, "User-Agent": user_agent}
        self._delay_sec = delay_sec

    @classmethod
    def from_env(
        cls,
        env_var: str = "OPENSTATES_API_KEY",
        user_agent: str = DEFAULT_USER_AGENT,
        delay_sec: float = DEFAULT_DELAY_SEC,
    ) -> "OpenStatesClient":
        key = os.environ.get(env_var)
        if not key:
            raise OpenStatesError(
                f"{env_var} env var is required. "
                f"Get a free key at https://openstates.org/accounts/profile/."
            )
        return cls(key, user_agent=user_agent, delay_sec=delay_sec)

    def get(
        self,
        path: str,
        params: list[tuple[str, str]] | dict[str, str] | None = None,
        timeout: int = DEFAULT_TIMEOUT_SEC,
    ) -> dict:
        """One request with retry on 429 / transient HTTP errors.

        `params` may be a dict OR a list of tuples — use the list form when you
        need repeated keys (OpenStates' `include` is repeated, not comma-joined).
        """
        url = f"{API_BASE}{path}" if path.startswith("/") else f"{API_BASE}/{path}"
        last_err: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = requests.get(url, params=params, headers=self._headers, timeout=timeout)
                if resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After", "")
                    wait = int(retry_after) if retry_after.isdigit() else 10 * (attempt + 1)
                    print(f"  rate-limited, sleeping {wait}s before retry...", file=sys.stderr)
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
            except (requests.Timeout, requests.HTTPError) as e:
                last_err = e
                time.sleep(3 * (attempt + 1))
        assert last_err is not None
        raise OpenStatesError(f"GET {url} failed after {MAX_RETRIES} attempts: {last_err}") from last_err

    def paginate(
        self,
        path: str,
        params: dict[str, str] | None = None,
        include: Iterable[str] | None = None,
        per_page: int = DEFAULT_PER_PAGE,
        max_pages: int | None = None,
    ) -> Iterator[dict]:
        """Yield every result across pages, sleeping `delay_sec` between requests.

        Stops when OpenStates' pagination block reports we've hit max_page,
        when a page returns no results, or when `max_pages` is reached.
        Does NOT mutate `params`.
        """
        params = dict(params or {})
        for page in range(1, (max_pages or 10_000) + 1):
            query: list[tuple[str, str]] = list(params.items())
            query.append(("per_page", str(per_page)))
            query.append(("page", str(page)))
            for inc in include or ():
                query.append(("include", inc))

            data = self.get(path, query)
            results = data.get("results") or []
            if not results:
                break
            for r in results:
                yield r

            pagination = data.get("pagination") or {}
            current = pagination.get("page", page)
            last = pagination.get("max_page", page)
            if current >= last:
                break
            time.sleep(self._delay_sec)
