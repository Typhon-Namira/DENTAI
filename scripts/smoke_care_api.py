"""Authenticated deployment smoke test for the Care API."""

import json  # noqa: I001 - kept explicit for the standalone deployment probe
import os
from urllib import error, parse, request


REQUIRED_CARE_ROUTES = {
    "/api/v1/care/analyses/{analysis_id}/generation-readiness",
    "/api/v1/care/analyses/{analysis_id}/generate-plan",
    "/api/v1/care/sequential-plans/search",
    "/api/v1/care/plans/{plan_id}/approve-sequential",
}


def request_json(base: str, path: str, *, token: str | None = None, body: dict | None = None):
    if parse.urlparse(base).scheme != "https":
        raise RuntimeError("Smoke-test origins must use HTTPS")
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = request.Request(
        base.rstrip("/") + path,
        data=data,
        headers=headers,
        method="POST" if body is not None else "GET",
    )
    try:
        with request.urlopen(req, timeout=20) as response:  # nosec B310 - HTTPS enforced above
            payload = response.read()
            if not payload:
                return response.status, None
            try:
                return response.status, json.loads(payload)
            except json.JSONDecodeError as exc:
                content_type = response.headers.get("content-type", "unknown")
                raise RuntimeError(
                    f"{path} at {base} did not return JSON (content-type: {content_type})"
                ) from exc
    except error.HTTPError as exc:
        raise RuntimeError(f"{path} returned {exc.code}: {exc.read().decode()[:500]}") from exc


def check_openapi_contract(base: str) -> None:
    status, schema = request_json(base, "/openapi.json")
    if status != 200 or not isinstance(schema, dict):
        raise RuntimeError(f"OpenAPI contract unavailable at {base}")
    paths = schema.get("paths")
    if not isinstance(paths, dict):
        raise RuntimeError(f"OpenAPI paths are missing at {base}")
    missing = sorted(REQUIRED_CARE_ROUTES - set(paths))
    if missing:
        raise RuntimeError(
            f"Care release contract is stale at {base}; missing routes: {', '.join(missing)}"
        )


def check_origin(base: str) -> None:
    # A single successful request can hide a partially wedged worker or proxy route.
    for probe in range(1, 6):
        status, health = request_json(base, "/health")
        if status != 200 or health.get("status") != "ok":
            raise RuntimeError(f"Health check {probe}/5 failed for {base}")
    status, ready = request_json(base, "/ready")
    if status != 200 or ready.get("status") != "ready":
        raise RuntimeError(f"Readiness check failed for {base}")

    check_openapi_contract(base)

    _, tokens = request_json(
        base,
        "/api/v1/auth/login",
        body={
            "clinic_slug": os.environ["CARE_SMOKE_CLINIC_SLUG"],
            "identifier": os.environ["CARE_SMOKE_IDENTIFIER"],
            "password": os.environ["CARE_SMOKE_PASSWORD"],
        },
    )
    token = tokens["access_token"]
    _, me = request_json(base, "/api/v1/auth/me", token=token)
    if not isinstance(me, dict) or not me.get("id") or not me.get("clinic_id"):
        raise RuntimeError(f"Authenticated session contract failed at {base}")

    _, dashboard = request_json(base, "/api/v1/care/dashboard", token=token)
    required = {
        "appointments_awaiting_approval",
        "active_care_plans",
        "active_conversations",
        "followups_due",
        "notification_count",
    }
    if not required.issubset(dashboard):
        raise RuntimeError(f"Care dashboard contract incomplete at {base}")
    for path in (
        "/api/v1/care/plans",
        "/api/v1/care/sequential-plans/search?offset=0&limit=1",
        "/api/v1/care/appointments",
        "/api/v1/care/conversations",
    ):
        request_json(base, path, token=token)


def main() -> None:
    # CARE_FRONTEND_URL is intentionally not probed here. The frontend is a static
    # Vercel origin and does not expose backend routes such as /openapi.json.
    # The deployment workflow verifies the authenticated frontend separately with
    # Playwright after this API contract smoke test succeeds.
    check_origin(os.environ["CARE_BACKEND_URL"])
    print("Care API authenticated smoke test passed", flush=True)


if __name__ == "__main__":
    main()
