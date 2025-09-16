import typing as t

import requests
from requests import Response
from requests.adapters import (
    HTTPAdapter,
    Retry,
)

# requests
CONNECT_TIMEOUT = 3
READ_TIMEOUT = 120


def _get_requests_session(
    total: int = 5,
    backoff_factor: int = 3,
    allowed_methods: frozenset = frozenset({"GET", "POST"}),
    status_forcelist: frozenset = frozenset({429, 500, 502, 503, 504}),
) -> requests.Session:
    # backoff_factor = 3: 5, 10, 20, 40, 80, 160, 320, 640, 1280, 2560
    retries = Retry(
        total=total,
        backoff_factor=backoff_factor,
        allowed_methods=allowed_methods,
        status_forcelist=status_forcelist,
    )
    sess = requests.Session()
    sess.mount("http://", HTTPAdapter(max_retries=retries))
    sess.mount("https://", HTTPAdapter(max_retries=retries))
    return sess


def get_url(url: str, params: t.Optional[dict] = None, headers: t.Optional[dict] = None) -> Response:
    s = _get_requests_session()
    return s.get(url, params=params, headers=headers, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))


def post_url(
    url: str, params: t.Optional[dict] = None, headers: t.Optional[dict] = None, data: t.Optional[str] = None
) -> Response:
    s = _get_requests_session()
    return s.post(url, params=params, headers=headers, data=data, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
