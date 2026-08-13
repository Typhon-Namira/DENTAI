# Architecture

DENTAI is one stateless FastAPI application with a control plane and physically isolated clinic databases. The control plane stores only clinic identity, status, encrypted database routing configuration, origins, and feature flags. Users, sessions, patients, clinical records, files' metadata, AI results, usage, and audit events live only in each clinic database.

Login resolves a slug through the control plane, then authenticates inside that clinic. Access tokens contain the trusted clinic registry UUID. Every authenticated request re-resolves that UUID, verifies clinic and user activity and token version, and creates a session only for that clinic engine. Request bodies cannot select a tenant.

Domain authorization is layered: role, branch membership, then active doctor-patient assignment. X-rays use opaque server-generated keys and private storage. AI is behind a provider boundary; mock results are explicitly decision support and create pending AI findings. Confirmation creates a distinct dentist-sourced finding.

## Implementation checklist

- [x] Control/clinic separation and resolver
- [x] Authentication, rotation, revocation, RBAC
- [x] Core clinical models, patient profile and transactional transfer
- [x] Private X-ray storage abstraction
- [x] Mock AI and explicit doctor review
- [x] Risk, care, follow-up, package, usage, subscription and audit models
- [x] Role dashboards, health/readiness, Docker/Railway foundation
- [ ] Production object-storage integration test against the chosen S3 vendor
- [ ] Real dental AI provider (intentionally excluded)

