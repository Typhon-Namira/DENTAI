from typing import Any

SENSITIVE_FIELDS = {"password_hash", "storage_key", "token_hash", "encrypted_database_url"}


def model_dict(instance: Any, *, exclude: set[str] | None = None) -> dict[str, Any]:
    blocked = SENSITIVE_FIELDS | (exclude or set())
    return {
        attribute.columns[0].name: getattr(instance, attribute.key)
        for attribute in instance.__mapper__.column_attrs
        if attribute.columns[0].name not in blocked
    }
