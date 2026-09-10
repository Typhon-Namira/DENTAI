from app.main import app


def test_explicit_followup_generation_route_is_registered():
    route = next(
        (
            item
            for item in app.routes
            if getattr(item, "path", None)
            == "/api/v1/care/analyses/{analysis_id}/generate-plan"
        ),
        None,
    )
    assert route is not None
    assert "POST" in route.methods
