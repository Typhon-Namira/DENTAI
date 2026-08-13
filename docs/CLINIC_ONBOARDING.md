# Clinic onboarding

Create a dedicated PostgreSQL database and credentials; run clinic migrations; generate a Fernet key; then run `python -m scripts.onboard_clinic` with CLI identity fields and environment-supplied DSNs/key. The command registers the encrypted DSN, creates the initial branch, and hashes the initial Director password. Configure origins, verify `/ready`, login, and explicitly test that another clinic's token cannot route to this database. Never place bootstrap credentials in source control.

