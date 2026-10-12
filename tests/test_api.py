import os

import pytest
from fastapi.testclient import TestClient

import portsvc
from portsvc.biz.errors import AppOpException


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    for k, v in {
        "SQLDB_USERNAME": "u",
        "SQLDB_PASSWORD": "p",
        "SQLDB_HOST": "localhost",
        "SQLDB_PORT": "5432",
        "SQLDB_DBNAME": "db",
    }.items():
        monkeypatch.setenv(k, os.environ.get(k, v))

    def fake_publish(*_: object) -> None:
        raise AppOpException(message="App release not found")

    monkeypatch.setattr("portsvc.api.port.publish", fake_publish)
    return TestClient(portsvc.create_app(), raise_server_exceptions=False)


@pytest.mark.unit
class TestMain:
    def test_invalid_payload_returns_400(self, client: TestClient) -> None:
        res = client.post("/ports/apps/foo/releases/bar", content="descr: {}\n")
        assert res.status_code == 400
        assert res.json()["code"] == 1400

    def test_biz_error_returns_409(self, client: TestClient) -> None:
        res = client.post("/ports/apps/foo/releases/bar/publish")
        assert res.status_code == 409
        assert res.json() == {"code": 1409, "message": "App release not found"}
