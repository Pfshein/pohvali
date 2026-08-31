import pytest
from fastapi.testclient import TestClient

from app.main import app

PRAISE_ID = "0ecaf26f-ee72-4f06-ae79-41198dd1ac6d"
CIPHERTEXT = "YWJj"  # base64("abc")
IV = "AAAAAAAAAAAAAAAA"  # base64(bytes(12))


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("POST", "/api/v1/session", {"timezone": "UTC"}),
        ("POST", "/api/v1/praises", {"body_ciphertext": CIPHERTEXT, "iv": IV}),
        ("GET", "/api/v1/praises", None),
        ("PATCH", f"/api/v1/praises/{PRAISE_ID}", {"body_ciphertext": CIPHERTEXT, "iv": IV}),
        ("DELETE", f"/api/v1/praises/{PRAISE_ID}", None),
        ("GET", "/api/v1/calendar?from=2026-09-01&to=2026-09-30", None),
    ],
)
def test_every_user_route_requires_authorization(
    method: str,
    path: str,
    body: dict | None,
) -> None:
    response = TestClient(app).request(method, path, json=body)

    assert response.status_code == 401
    # The generic 401 must not hint at whether the resource exists.
    assert "not found" not in response.text.lower()
