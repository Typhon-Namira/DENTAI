from pathlib import Path


def test_embedded_whatsapp_runtime_wires_inbound_and_status_callbacks():
    startup = Path("scripts/start_railway.sh").read_text()

    assert "TETA2_CARE_CALLBACK_URL" in startup
    assert "/api/v1/care/internal/whatsapp/inbound" in startup
    assert "TETA2_CARE_STATUS_CALLBACK_URL" in startup
    assert "/api/v1/care/internal/whatsapp/status" in startup
    assert "WHATSAPP_SERVICE_TOKEN" in startup
    assert "secrets.token_urlsafe(32)" in startup
