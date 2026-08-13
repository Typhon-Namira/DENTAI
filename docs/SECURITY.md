# Security

Tenant selection is derived from a signed token and an active control-plane record. Tokens do not authorize on their own: user state and token version are revalidated. Managers are branch-scoped; Doctors additionally require an active patient assignment. Passwords use Argon2. Refresh tokens are stored only as SHA-256 digests, rotated, and revocable.

X-rays are private, MIME/size checked, stored under random keys, and accessed only after patient authorization. Audit metadata must never contain passwords, tokens, file bodies, or clinical notes. Production rejects short/default secrets and wildcard CORS. Hard deletion and jurisdiction-specific retention are deliberately not automated; deployments must establish a legal retention policy.

