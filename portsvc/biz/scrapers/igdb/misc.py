import os
import time
import typing as t

import requests

from portsvc.biz.scrapers.misc import post_url

CLIENT_ID = os.environ.get("IGDB_CLIENT_ID")
CLIENT_SECRET = os.environ.get("IGDB_CLIENT_SECRET")
MIN_SLEEP = 0.25


def get_access_token() -> str:
    # POST: https://id.twitch.tv/oauth2/token?client_id=abcde&client_secret=fghijk&grant_type=client_credentials
    res = post_url(
        "https://id.twitch.tv/oauth2/token",
        {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "client_credentials",
        },
    )
    return res.json()["access_token"]


ACCESS_TOKEN = get_access_token()


def _post_url(url: str, data: t.Optional[str] = None) -> requests.Response:
    return post_url(
        url,
        headers={"Client-ID": CLIENT_ID, "Authorization": f"Bearer {ACCESS_TOKEN}", "Accept": "application/json"},
        data=data,
    )


def get_data(url: str, data: str) -> list[dict]:
    offset = 0
    limit = 500
    res = []
    while True:
        cur_res = _post_url(
            url=url,
            data=data + f"offset {offset};limit {limit};",
        ).json()
        if not cur_res or (("id" not in cur_res[0]) and ("status" in cur_res[0]) and (cur_res[0]["status"] != 200)):
            break
        res += cur_res
        offset += limit
        time.sleep(MIN_SLEEP)
    return res
