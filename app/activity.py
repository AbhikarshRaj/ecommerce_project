def record_event(db, event_type, entity_type, entity_id, details):
    db.execute(
        """
        INSERT INTO activity_logs
        (event_type, entity_type, entity_id, details)
        VALUES (?, ?, ?, ?)
        """,
        (event_type, entity_type, entity_id, details)
    )

def cleanup_old_logs(db, retention_days=90):
    if retention_days < 1:
        raise ValueError("Retention days must be positive")

    cursor = db.execute(
        """
        DELETE FROM activity_logs
        WHERE created_at < datetime('now', ?)
        """,
        (f"-{retention_days} days",)
    )

    return cursor.rowcount
