from app.database.collections import (
    USERS,
    PATIENT_PROFILES,
    DOCTOR_PROFILES,
    REPORTS,
    PRESCRIPTIONS,
    PAPER_UPLOADS,
    NOTIFICATIONS,
    ACCESS_REQUESTS,
    ACCESS_GRANTS,
    AUDIT_LOGS,
)


async def create_indexes():
    from app.database.connection import get_database

    db = get_database()

    await db[USERS].create_index("email", unique=True)
    await db[USERS].create_index("role")
    await db[USERS].create_index("is_active")

    await db[PATIENT_PROFILES].create_index("user_id", unique=True)
    # Sparse: legacy docs may lack patient_id; explicit values stay unique.
    # Drop the legacy non-sparse variant first (same name, conflicting options
    # would otherwise abort startup with IndexOptionsConflict).
    _info = await db[PATIENT_PROFILES].index_information()
    if "patient_id_1" in _info and not _info["patient_id_1"].get("sparse"):
        await db[PATIENT_PROFILES].drop_index("patient_id_1")
    await db[PATIENT_PROFILES].create_index("patient_id", unique=True, sparse=True)

    await db[DOCTOR_PROFILES].create_index("user_id", unique=True)
    # Sparse: legacy docs may lack doctor_id; explicit values stay unique.
    _dinfo = await db[DOCTOR_PROFILES].index_information()
    if "doctor_id_1" in _dinfo and not _dinfo["doctor_id_1"].get("sparse"):
        await db[DOCTOR_PROFILES].drop_index("doctor_id_1")
    await db[DOCTOR_PROFILES].create_index("doctor_id", unique=True, sparse=True)

    await db[REPORTS].create_index("patient_id")
    await db[REPORTS].create_index("created_at")

    await db[PRESCRIPTIONS].create_index("patient_id")
    await db[PRESCRIPTIONS].create_index("doctor_id")
    await db[PRESCRIPTIONS].create_index("prescription_date")
    await db[PRESCRIPTIONS].create_index("created_at")
    await db[PRESCRIPTIONS].create_index("verification_token", unique=True, sparse=True)

    await db[PAPER_UPLOADS].create_index("patient_id")
    await db[PAPER_UPLOADS].create_index("created_at")

    await db[NOTIFICATIONS].create_index("user_id")
    await db[NOTIFICATIONS].create_index("is_read")
    await db[NOTIFICATIONS].create_index("created_at")
    await db[NOTIFICATIONS].create_index("dedupe_key", unique=True, sparse=True)

    await db[ACCESS_REQUESTS].create_index("patient_id")
    await db[ACCESS_REQUESTS].create_index("doctor_id")
    await db[ACCESS_REQUESTS].create_index("status")
    await db[ACCESS_REQUESTS].create_index("created_at")

    await db[ACCESS_GRANTS].create_index("patient_id")
    await db[ACCESS_GRANTS].create_index("doctor_id")
    await db[ACCESS_GRANTS].create_index("status")
    await db[ACCESS_GRANTS].create_index("expires_at")

    await db[AUDIT_LOGS].create_index("patient_id")
    await db[AUDIT_LOGS].create_index("actor_id")
    await db[AUDIT_LOGS].create_index("action")
    await db[AUDIT_LOGS].create_index("timestamp")
