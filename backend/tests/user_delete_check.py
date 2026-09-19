"""Account deletion: DELETE /users/{id}/permanent. Nothing an account recorded goes with it.

An account with no records - merely having logged in does not count - is removed
outright. An account with records is kept, marked deleted: off every list, unable to
sign in or be reactivated, email still taken, while every record and audit entry keeps
naming it as the author.

Two halves:

* Through the API - roles, self-deletion, and a real delete of accounts this script
  creates (which have no records, so they are removed outright). It deletes what it
  creates, so the only trace left is the audit log, which is append-only by design.
* Against the database, inside a transaction that is rolled back - deleting an account
  that HAS records. Doing that through the API would leave a deleted account behind for
  good (that is the whole point), and doing it to a seeded account would really delete
  it. Also checks that the models know every foreign key the database has into `users`,
  since the rule is built from the models.

Needs a LIVE backend on :8000 and the seeded database:

    python tests/user_delete_check.py

Exits non-zero on any failure.
"""
import asyncio
import os
import sys
import uuid

import httpx
from dotenv import load_dotenv
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

load_dotenv(".env")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.schemas.user import UserCreate, UserUpdate  # noqa: E402
from app.services import user_service  # noqa: E402
from app.services.user_service import (  # noqa: E402
    _columns_referencing_users,
    _users_with_records,
)

BASE = "http://localhost:8000/api/v1"
PW = "Password123!"
ADMIN = "admin@neonatal.rs"
ADMIN_ID = uuid.UUID("aaaaaaaa-0001-0001-0001-000000000001")
PERAWAT = "siti.aisyah@neonatal.rs"
BABY_ID = uuid.UUID("cccccccc-0003-0003-0003-000000000001")
results = []


def check(name, got, want):
    ok = got == want
    results.append((ok, name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got {got!r}, want {want!r}")


def login(c, email):
    r = c.post(f"{BASE}/auth/login", json={"email": email, "password": PW})
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def listed(c, A, email):
    return next((u for u in c.get(f"{BASE}/users", headers=A).json() if u["email"] == email), None)


def audit_entry(c, A, record_id):
    logs = c.get(f"{BASE}/audit-logs?skip=0&limit=50", headers=A).json()
    return next((l for l in logs if l["action"] == "DELETE"
                 and str(l.get("record_id")) == record_id), {})


def api_half():
    created = []
    with httpx.Client(timeout=30) as c:
        A, P = login(c, ADMIN), login(c, PERAWAT)

        def make(role):
            email = f"uji.hapus.{uuid.uuid4().hex[:8]}@neonatal.rs"
            r = c.post(f"{BASE}/users", headers=A, json={
                "email": email, "full_name": "Uji Hapus", "password": PW, "role": role})
            r.raise_for_status()
            created.append(r.json()["id"])
            return r.json()["id"], email

        try:
            print("\n1. Refusals")
            fresh_id, fresh_email = make("dokter")
            check("perawat may not delete", c.delete(
                f"{BASE}/users/{fresh_id}/permanent", headers=P).status_code, 403)
            check("admin may not delete itself", c.delete(
                f"{BASE}/users/{ADMIN_ID}/permanent", headers=A).status_code, 400)

            print("\n2. An account never used - removed outright")
            check("deleted", c.delete(
                f"{BASE}/users/{fresh_id}/permanent", headers=A).status_code, 204)
            check("gone from the list", listed(c, A, fresh_email), None)
            check("a second delete is 404", c.delete(
                f"{BASE}/users/{fresh_id}/permanent", headers=A).status_code, 404)
            entry = audit_entry(c, A, fresh_id)
            check("audit entry keeps whose account it was",
                  (entry.get("details") or {}).get("email"), fresh_email)
            check("...and that nothing had to be kept",
                  (entry.get("details") or {}).get("catatan_dipertahankan"), False)

            print("\n3. An account that only ever logged in - also removed outright")
            once_id, once_email = make("perawat")
            login(c, once_email)
            check("deleted", c.delete(
                f"{BASE}/users/{once_id}/permanent", headers=A).status_code, 204)
            check("nothing had to be kept",
                  (audit_entry(c, A, once_id).get("details") or {}).get("catatan_dipertahankan"),
                  False)
        finally:
            # Best effort if a check above failed half-way.
            for uid in created:
                c.delete(f"{BASE}/users/{uid}/permanent", headers=A)


async def refused(coro):
    """Status code of the HTTPException the call raises, or None if it succeeds."""
    try:
        await coro
    except HTTPException as e:
        return e.status_code
    return None


async def db_half():
    engine = create_async_engine(os.environ["DATABASE_URL"], echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as db:
        print("\n4. Models know every foreign key into users")
        in_db = {tuple(r) for r in (await db.execute(text("""
            SELECT c.conrelid::regclass::text, a.attname
            FROM pg_constraint c
            JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
            WHERE c.contype = 'f' AND c.confrelid = 'users'::regclass"""))).all()}
        in_models = {(col.table.name, col.name) for col in _columns_referencing_users()}
        check("database foreign keys missing from the models", sorted(in_db - in_models), [])

        print("\n5. What counts as a record - rolled back, nothing is kept")
        uid = uuid.uuid4()
        email = f"uji.hapus.{uid.hex[:8]}@neonatal.rs"
        await db.execute(text("""
            INSERT INTO users (id, role, email, password_hash, full_name)
            VALUES (:id, 'dokter', :email, 'x', 'Uji Hapus')"""), {"id": uid, "email": email})
        await db.execute(text(
            "INSERT INTO audit_logs (user_id, action, details) VALUES (:u, 'LOGIN', '{}')"),
            {"u": uid})
        check("a LOGIN entry is not a record", uid in await _users_with_records(db), False)
        await db.execute(text("""
            INSERT INTO doctor_notes (baby_id, recorded_by, observation_time, catatan)
            VALUES (:b, :u, now(), 'catatan uji')"""), {"b": BABY_ID, "u": uid})
        await db.execute(text(
            "INSERT INTO audit_logs (user_id, action, table_name) VALUES (:u, 'CREATE', 'doctor_notes')"),
            {"u": uid})
        check("a doctor note is", uid in await _users_with_records(db), True)

        print("\n6. Deleting an account that has records - rolled back, nothing is kept")
        await user_service.delete_user_permanently(uid, db, actor_id=ADMIN_ID)
        # A request's commit writes the audit entry; here nothing commits, so write the
        # pending rows before reading them back with plain SQL.
        await db.flush()
        row = (await db.execute(text(
            "SELECT deleted_at IS NOT NULL, is_active FROM users WHERE id = :u"), {"u": uid})).first()
        check("the row is kept, marked deleted and inactive", tuple(row) if row else None, (True, False))
        check("its doctor note still names it", (await db.execute(text(
            "SELECT count(*) FROM doctor_notes WHERE recorded_by = :u"), {"u": uid})).scalar(), 1)
        check("its audit entries still name it", (await db.execute(text(
            "SELECT count(*) FROM audit_logs WHERE user_id = :u"), {"u": uid})).scalar(), 2)
        deletion = (await db.execute(text("""
            SELECT user_id, details FROM audit_logs
            WHERE action = 'DELETE' AND table_name = 'users' AND record_id = :u"""),
            {"u": uid})).first()
        check("the deletion is audited, by the admin", deletion and deletion.user_id, ADMIN_ID)
        check("...noting that records were kept",
              deletion and deletion.details.get("catatan_dipertahankan"), True)

        users = await user_service.get_all_users(db)
        check("gone from the user list", any(u.id == uid for u in users), False)
        doctors = await user_service.get_doctors(db)
        check("gone from the DPJP choices", any(d.id == uid for d in doctors), False)
        check("cannot be reactivated", await refused(user_service.update_user(
            uid, UserUpdate(is_active=True), db, actor_id=ADMIN_ID)), 404)
        check("cannot be deleted twice", await refused(
            user_service.delete_user_permanently(uid, db, actor_id=ADMIN_ID)), 404)
        check("its email cannot be reused", await refused(user_service.create_user(
            UserCreate(role="dokter", email=email, password=PW, full_name="Baru"),
            db, actor_id=ADMIN_ID)), 409)
        await db.rollback()
    await engine.dispose()


def main():
    api_half()
    asyncio.run(db_half())
    passed = sum(1 for ok, _ in results if ok)
    print(f"\n{passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
