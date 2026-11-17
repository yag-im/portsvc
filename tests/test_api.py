import dataclasses
import logging
import os

import pytest
import requests
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi_rfc9457 import Problem
from pydantic import ValidationError

import portsvc
from portsvc.biz import errors
from portsvc.biz.dto import UpsertAppReleaseRequestDTO
from portsvc.biz.errors import (
    AppReleaseNotFound,
    CompanyNotFound,
    IgdbFailed,
    InconsistentData,
    PortsvcProblem,
    S3Failed,
    UaLockPointerUnknown,
    upstream_errors,
)
from portsvc.biz.port import get_ua_lock_pointer_state

UPSERT_URL = "/ports/apps/foo/releases/bar"
PUBLISH_URL = "/ports/apps/foo/releases/bar/publish"
PROBLEM_JSON = "application/problem+json"


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
    monkeypatch.setattr("portsvc.api.port.publish", lambda *_: None)
    return TestClient(portsvc.create_app(), raise_server_exceptions=False)


def _extensions(problem: Problem) -> dict[str, object]:
    return {
        f.name: getattr(problem, f.name) for f in dataclasses.fields(problem) if f.name not in {"detail", "instance"}
    }


@pytest.mark.unit
class TestApi:
    def test_malformed_yaml_returns_400(self, client: TestClient) -> None:
        res = client.post(UPSERT_URL, content="descr: [\n")
        assert res.status_code == 400
        assert res.headers["content-type"] == PROBLEM_JSON
        body = res.json()
        assert body["type"] == "malformed-body"
        assert body["instance"] == UPSERT_URL
        assert body["error"]

    def test_invalid_payload_returns_422(self, client: TestClient) -> None:
        res = client.post(UPSERT_URL, content="descr: {}\n")
        assert res.status_code == 422
        assert res.headers["content-type"] == PROBLEM_JSON
        body = res.json()
        assert body["type"] == "validation"
        with pytest.raises(ValidationError) as exc_info:
            UpsertAppReleaseRequestDTO.model_validate({"descr": {}})
        assert body["errors"] == [
            {"loc": list(e["loc"]), "detail": e["msg"], "type": e["type"]} for e in exc_info.value.errors()
        ]

    def test_publish_returns_204(self, client: TestClient) -> None:
        res = client.post(PUBLISH_URL)
        assert res.status_code == 204
        assert res.content == b""

    @pytest.mark.parametrize(
        "problem",
        [
            AppReleaseNotFound(igdb_slug="foo", app_release_uuid="bar"),
            CompanyNotFound(publisher="Acme"),
            InconsistentData(igdb_slug="foo"),
            S3Failed(),
        ],
    )
    def test_problem_is_returned(self, client: TestClient, monkeypatch: pytest.MonkeyPatch, problem: Problem) -> None:
        def fake_publish(*_: object) -> None:
            raise problem

        monkeypatch.setattr("portsvc.api.port.publish", fake_publish)
        res = client.post(PUBLISH_URL)
        assert res.status_code == problem.status
        assert res.headers["content-type"] == PROBLEM_JSON
        expected = {"type": problem.type, "title": problem.title, "status": problem.status, "instance": PUBLISH_URL}
        if problem.detail:
            expected["detail"] = problem.detail
        assert res.json() == expected | _extensions(problem)

    def test_unknown_error_returns_500_without_details(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fake_publish(*_: object) -> None:
            raise RuntimeError("db password is secret")

        monkeypatch.setattr("portsvc.api.port.publish", fake_publish)
        res = client.post(PUBLISH_URL)
        assert res.status_code == 500
        assert res.headers["content-type"] == PROBLEM_JSON
        assert "secret" not in res.text
        assert res.json()["title"] == "Internal Server Error"

    def test_error_responses_are_logged(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        logged: list[str] = []
        monkeypatch.setattr(errors.log, "error", lambda msg, *_: logged.append(msg))
        res = client.post(UPSERT_URL, content="descr: {}\n")
        assert logged == [res.text]

    def test_unknown_error_is_not_logged_again_by_server(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        raised = RuntimeError("boom")

        def fake_publish(*_: object) -> None:
            raise raised

        monkeypatch.setattr("portsvc.api.port.publish", fake_publish)
        client.post(PUBLISH_URL)

        def server_log_record(exc: Exception) -> logging.LogRecord:
            return logging.LogRecord(
                "uvicorn.error",
                logging.ERROR,
                __file__,
                0,
                "Exception in ASGI application",
                None,
                (type(exc), exc, None),
            )

        server_log = logging.getLogger("uvicorn.error")
        assert not server_log.filter(server_log_record(raised))
        assert server_log.filter(server_log_record(RuntimeError("not handled by app")))

    def test_unknown_route_keeps_fastapi_format(self, client: TestClient) -> None:
        res = client.get("/no/such/route")
        assert res.status_code == 404
        assert res.headers["content-type"] == "application/json"
        assert res.json() == {"detail": "Not Found"}

    def test_openapi_documents_responses(self, client: TestClient) -> None:
        schema = client.get("/openapi.json").json()
        expected = {
            "upsert_port": (
                "/ports/apps/{igdb_slug}/releases/{app_release_uuid}",
                {"200", "400", "404", "422", "500", "502"},
            ),
            "publish_port": (
                "/ports/apps/{igdb_slug}/releases/{app_release_uuid}/publish",
                {"204", "404", "422", "500", "502"},
            ),
        }
        for op_id, (path, codes) in expected.items():
            op = schema["paths"][path]["post"]
            assert op["operationId"] == op_id
            assert op["summary"]
            assert set(op["responses"]) == codes
            for code, r in op["responses"].items():
                assert r["description"]
                if int(code) >= 400:
                    assert list(r["content"]) == [PROBLEM_JSON]
        upsert_422 = schema["paths"][expected["upsert_port"][0]]["post"]["responses"]["422"]
        assert {"ValidationProblem", "CompanyNotFound", "PlatformNotFound", "UaLockPointerUnknown"} <= set(
            upsert_422["content"][PROBLEM_JSON]["examples"]
        )
        assert "HTTPValidationError" not in schema["components"]["schemas"]

    def test_openapi_problem_schemas_match_responses(self, client: TestClient) -> None:
        schema = client.get("/openapi.json").json()
        components = schema["components"]["schemas"]
        for name in ("CompanyNotFound", "ValidationProblem", "InternalServerError", "ProblemDetail"):
            assert {"type", "title", "status"} <= set(components[name]["required"]), name
        assert set(components["CompanyNotFound"]["required"]) == {"type", "title", "status", "publisher"}
        invalid_param = components["InvalidParam"]
        assert "input" not in invalid_param["properties"]
        assert invalid_param["description"] == "One field-level validation failure."
        upsert_422 = schema["paths"]["/ports/apps/{igdb_slug}/releases/{app_release_uuid}"]["post"]["responses"]["422"]
        validation_example = upsert_422["content"][PROBLEM_JSON]["examples"]["ValidationProblem"]["value"]
        assert validation_example["errors"] == [{"loc": ["string"], "detail": "string", "type": "string"}]


@pytest.mark.unit
class TestErrors:
    def test_request_validation_error_returns_problem(self) -> None:
        app = FastAPI()
        errors.init_app(app)

        @app.get("/items/{item_id}")
        def get_item(item_id: int) -> int:
            return item_id

        res = TestClient(app).get("/items/foo")
        assert res.status_code == 422
        assert res.headers["content-type"] == PROBLEM_JSON
        body = res.json()
        assert body["type"] == "validation"
        assert body["instance"] == "/items/foo"
        assert body["errors"] == [
            {
                "loc": ["path", "item_id"],
                "detail": "Input should be a valid integer, unable to parse string as an integer",
                "type": "int_parsing",
            }
        ]

    @pytest.mark.parametrize("problem_cls", PortsvcProblem.__subclasses__())
    def test_detail_template_matches_fields(self, problem_cls: type[PortsvcProblem]) -> None:
        fields = [f.name for f in dataclasses.fields(problem_cls) if f.name not in {"detail", "instance"}]
        problem = problem_cls(**dict.fromkeys(fields, "x"))
        assert (problem.detail is None) == (problem_cls.detail_template is None)

    def test_upstream_errors_converts_client_errors(self) -> None:
        with pytest.raises(IgdbFailed), upstream_errors(IgdbFailed, requests.RequestException):
            raise requests.ConnectionError

    def test_upstream_errors_passes_other_errors(self) -> None:
        with pytest.raises(KeyError), upstream_errors(IgdbFailed, requests.RequestException):
            raise KeyError

    def test_unknown_ua_lock_pointer_state_is_unprocessable(self) -> None:
        req = UpsertAppReleaseRequestDTO.model_validate(
            {
                "descr": {
                    "distro": {"format": "zip", "url": "u"},
                    "igdb_slug": "foo",
                    "lang": "en",
                    "name": "Foo",
                    "platform": "dos",
                    "publisher": "Acme",
                    "refs": {},
                    "reqs": {"screen_width": 640, "screen_height": 480},
                    "runner": {"name": "unknown", "ver": "1"},
                    "uuid": "bar",
                    "year_released": 1990,
                },
                "installer": {},
            }
        )
        with pytest.raises(UaLockPointerUnknown) as exc_info:
            get_ua_lock_pointer_state(req)
        assert exc_info.value.runner == "unknown"
