import json
import logging

from fastapi.testclient import TestClient

from app.main import app

SENSITIVE = "SENSITIVE-INITDATA-8900123456"


class _Capture(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def capture_access_logs() -> _Capture:
    handler = _Capture()
    logging.getLogger("app.access").addHandler(handler)
    return handler


def test_access_log_records_structured_fields_without_credentials() -> None:
    handler = capture_access_logs()
    try:
        response = TestClient(app).get(
            "/api/v1/health",
            headers={"Authorization": f"tma {SENSITIVE}", "X-Request-ID": "req-xyz"},
        )
    finally:
        logging.getLogger("app.access").removeHandler(handler)

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-xyz"

    record = handler.records[-1]
    assert record.method == "GET"
    assert record.path == "/api/v1/health"
    assert record.status == 200
    assert record.request_id == "req-xyz"
    assert isinstance(record.duration_ms, float)

    # No captured record may carry the Authorization credential anywhere.
    for captured in handler.records:
        assert SENSITIVE not in json.dumps(captured.__dict__, default=str)


def test_access_log_generates_a_request_id_when_absent() -> None:
    handler = capture_access_logs()
    try:
        response = TestClient(app).get("/api/v1/health")
    finally:
        logging.getLogger("app.access").removeHandler(handler)

    generated = response.headers["X-Request-ID"]
    assert generated
    assert handler.records[-1].request_id == generated
