import logging
import os
import threading
import time

import requests

from portsvc.biz.scrapers.misc import post_url

CLIENT_ID = os.environ.get("IGDB_CLIENT_ID")
CLIENT_SECRET = os.environ.get("IGDB_CLIENT_SECRET")
MIN_SLEEP = 0.25
ACCESS_TOKEN_TTL = 24 * 60 * 60  # seconds

log = logging.getLogger("portsvc")


class _AccessTokenCache:
    token: str | None = None
    expires_at = 0.0
    lock = threading.Lock()


def _fetch_access_token() -> str:
    # POST: https://id.twitch.tv/oauth2/token?client_id=abcde&client_secret=fghijk&grant_type=client_credentials
    res = post_url(
        "https://id.twitch.tv/oauth2/token",
        {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "client_credentials",
        },
    )
    payload = res.json()
    if "access_token" not in payload:
        raise RuntimeError(f"Failed to obtain IGDB access token: {payload}")
    return payload["access_token"]


def get_access_token() -> str:
    c = _AccessTokenCache
    with c.lock:
        if c.token is None or time.monotonic() >= c.expires_at:
            c.token = _fetch_access_token()
            c.expires_at = time.monotonic() + ACCESS_TOKEN_TTL
        return c.token


def _post_url(url: str, data: str | None = None) -> requests.Response:
    return post_url(
        url,
        headers={"Client-ID": CLIENT_ID, "Authorization": f"Bearer {get_access_token()}", "Accept": "application/json"},
        data=data,
    )


def get_data(url: str, data: str) -> list[dict]:
    offset = 0
    limit = 500
    res = []
    while True:
        query = data + f"offset {offset};limit {limit};"
        cur_res = _post_url(url=url, data=query).json()
        if not isinstance(cur_res, list) or not cur_res:
            if cur_res:
                log.error("IGDB error for %s query=%s: %s", url, query, cur_res)
            break
        if "id" not in cur_res[0] and "status" in cur_res[0] and cur_res[0]["status"] != 200:
            log.error("IGDB error for %s query=%s: %s", url, query, cur_res)
            break
        res += cur_res
        offset += limit
        time.sleep(MIN_SLEEP)
    return res
