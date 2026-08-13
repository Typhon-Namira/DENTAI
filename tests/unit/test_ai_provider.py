import pytest

from app.ai.providers import MockDentalAIProvider


@pytest.mark.asyncio
async def test_mock_ai_is_deterministic_and_disclaimed():
    provider = MockDentalAIProvider()
    one = await provider.analyze_xray(patient_context={}, xray_reference="a")
    two = await provider.analyze_xray(patient_context={}, xray_reference="a")
    assert one == two
    assert one.structured_result["mock"] is True
    assert "Not a diagnosis" in one.structured_result["disclaimer"]
    assert one.findings[0]["confidence"] is None
