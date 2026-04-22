from sqlalchemy.orm import Session

from app.models import AuditLog


def record_audit_log(
    db: Session,
    *,
    actor_user_id: str | None,
    target_type: str,
    target_id: str | None,
    action: str,
    metadata: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor_user_id,
            target_type=target_type,
            target_id=target_id,
            action=action,
            metadata_json=metadata or {},
        )
    )

