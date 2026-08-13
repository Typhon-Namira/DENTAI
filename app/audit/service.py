import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AuditLog, User


async def audit(
    db: AsyncSession,
    actor: User,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | str | None,
    branch_id: uuid.UUID | None = None,
    metadata: dict | None = None,
):
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            actor_role=actor.role.value,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            branch_id=branch_id,
            audit_metadata=metadata or {},
        )
    )
