"""Authenticated deployment smoke test for the Care API and frontend proxy."""

import json
import os
import urllib.error
import urllib.request
from urllib.parse import urlparse


def request(base: str, path: str, *, token: str | None = None, body: dict | None = None):
    if urlparse(base).scheme != "https":
        raise RuntimeError("Smoke-test origins must use HTTPS")
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = urllib.request.Request(
        base.rstrip("/") + path,
        data=data,
        headers=headers,
        method="POST" if body is not None else "GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:  # nosec B310 - HTTPS enforced above
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"{path} returned {exc.code}: {exc.read().decode()[:500]}") from exc


def check_origin(base: str) -> None:
    # A single successful request can hide a partially wedged worker or proxy route.
    for probe in range(1, 6):
        status, health = request(base, "/health")
        if status != 200 or health.get("status") != "ok":
            raise RuntimeError(f"Health check {probe}/5 failed for {base}")
    status, ready = request(base, "/ready")
    if status != 200 or ready.get("status") != "ready":
        raise RuntimeError(f"Readiness check failed for {base}")
    _, tokens = request(
        base,
        "/api/v1/auth/login",
        body={
            "clinic_slug": os.environ["CARE_SMOKE_CLINIC_SLUG"],
            "identifier": os.environ["CARE_SMOKE_IDENTIFIER"],
            "password": os.environ["CARE_SMOKE_PASSWORD"],
        },
    )
    token = tokens["access_token"]
    _, dashboard = request(base, "/api/v1/care/dashboard", token=token)
    required = {
        "appointments_awaiting_approval",
        "active_care_plans",
        "active_conversations",
        "followups_due",
        "notification_count",
    }
    if not required.issubset(dashboard):
        raise RuntimeError(f"Care dashboard contract incomplete at {base}")
    for path in ("/api/v1/care/plans", "/api/v1/care/appointments", "/api/v1/care/conversations"):
        request(base, path, token=token)


def main() -> None:
    check_origin(os.environ["CARE_BACKEND_URL"])
    frontend = os.getenv("CARE_FRONTEND_URL")
    if frontend:
        check_origin(frontend)
    print("Care API authenticated smoke test passed", flush=True)


if __name__ == "__main__":
    main()
