from app.care.generation_api import router


def test_explicit_followup_generation_route_is_registered():
    route = next(
        (
            item
            for item in router.routes
            if getattr(item, "path", None) == "/care/analyses/{analysis_id}/generate-plan"
        ),
        None,
    )
    assert route is not None
    assert "POST" in route.methods
