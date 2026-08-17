# DENTAI WhatsApp service

Internal clinic-scoped WhatsApp transport using Baileys QR authentication. It does not use Meta Cloud API, WABA, Twilio, or provider access tokens.

Railway:

- Create a separate private service named `DENTAI-WHATSAPP` using this directory and Dockerfile.
- Mount a persistent volume at `/app/data`.
- Set `WHATSAPP_SESSION_DIR=/app/data/whatsapp_sessions`.
- Set the same strong `WHATSAPP_SERVICE_TOKEN` on the Node service and DENTAI API/worker.
- Set `WHATSAPP_SERVICE_URL` on the DENTAI API/worker to the Railway private URL.

`useMultiFileAuthState()` credentials are isolated under deterministic `clinic_<uuid>` directories. Session files are never returned by the API.

Baileys is pinned to 6.7.22 rather than the reference repository's vulnerable 6.7.9. This is the minimum patched 6.7.x release named by GHSA-qvv5-jq5g-4cgg and retains the same makeWASocket/useMultiFileAuthState architecture.
