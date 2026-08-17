# DENTAI WhatsApp service

Internal clinic-scoped WhatsApp transport using Baileys QR authentication. It does not use Meta Cloud API, WABA, Twilio, or provider access tokens.

## Default DENTAI deployment

The production DENTAI web image embeds this Node/Baileys service in the same container, matching the deployment pattern used by `Typhon-Namira/scrap`.

`scripts/start_railway.sh` starts the WhatsApp service on loopback port `3001` and then starts FastAPI. When `WHATSAPP_SERVICE_URL` is not set, the script supplies:

`http://127.0.0.1:3001`

No separate Railway `DENTAI-WHATSAPP` service and no `WHATSAPP_SERVICE_TOKEN` are required for this default loopback mode.

Sessions use:

`/app/data/whatsapp_sessions/clinic_<clinic_uuid_hex>`

The QR payload comes directly from Baileys `connection.update` and is converted with `qrcode.toDataURL()`. The frontend polls the authenticated FastAPI QR endpoint until the QR is available or the account is connected.

For persistent login across container replacement, mount persistent storage at `/app/data` on the DENTAI web service. Without a volume, QR login still works but a new deployment can require reconnecting WhatsApp.

## Optional external mode

The standalone `whatsapp_service/Dockerfile` remains available for deployments that explicitly disable the embedded process. External/non-loopback mode should use a strong shared `WHATSAPP_SERVICE_TOKEN` and an explicit `WHATSAPP_SERVICE_URL`.

Baileys is pinned to 6.7.22 rather than the reference repository's vulnerable 6.7.9. This retains the same `makeWASocket()` / `useMultiFileAuthState()` QR architecture while using the patched compatible 6.7.x release.
