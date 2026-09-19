"""Permanent account deletion: DELETE /users/{id}/permanent and the `deletable` flag.

An account may be deleted for good only if it has never recorded or changed anything;
merely having logged in does not count. Everything else is deactivated, so that each
record keeps the name of whoever wrote it.

Two halves:

* Through the API - roles, the seeded accounts that must be refused, self-deletion, and
  a real delete of accounts this script creates. It deletes what it creates, so the
  only trace left is the audit log, which is append-only by design.
* Against the database, inside a transaction that is rolled back - the audit-log case,
  which cannot be staged through the API without leaving an undeletable account behind
  (that is the whole point of the rule). Also checks that the models know every foreign
  key the database has into `users`, since the rule is built from the models.

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
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

load_dotenv(".env")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.user_service import (  # noqa: E402
    _columns_referencing_users,
    _users_with_records,
)

BASE = "http://localhost:8000/api/v1"
PW = "Password123!"
ADMIN = "admin@neonatal.rs"
PERAWAT = "siti.aisyah@neonatal.rs"
WITH_RECORDS = "budi.santoso@neonatal.rs"   # seeded nurse with clinical records
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


def api_half():
    created = []
    with httpx.Client(timeout=30) as c:
        A, P = login(c, ADMIN), login(c, PERAWAT)
        me = c.get(f"{BASE}/auth/me", headers=A).json()["id"]

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
                f"{BASE}/users/{me}/permanent", headers=A).status_code, 400)
            busy = listed(c, A, WITH_RECORDS)
            check("account with records is flagged not deletable", busy["deletable"], False)
            check("account with records is refused", c.delete(
                f"{BASE}/users/{busy['id']}/permanent", headers=A).status_code, 409)
            check("...and still exists", listed(c, A, WITH_RECORDS) is not None, True)

            print("\n2. An account never used")
            check("flagged deletable", listed(c, A, fresh_email)["deletable"], True)
            check("deleted", c.delete(
                f"{BASE}/users/{fresh_id}/permanent", headers=A).status_code, 204)
            check("gone from the list", listed(c, A, fresh_email), None)
            check("a second delete is 404", c.delete(
                f"{BASE}/users/{fresh_id}/permanent", headers=A).status_code, 404)
            logs = c.get(f"{BASE}/audit-logs?skip=0&limit=50", headers=A).json()
            entry = next((l for l in logs if l["action"] == "DELETE"
                          and str(l.get("record_id")) == fresh_id), None)
            check("audit entry keeps whose account it was",
                  (entry or {}).get("details", {}).get("email"), fresh_email)

            print("\n3. An account that only ever logged in")
            once_id, once_email = make("perawat")
            login(c, once_email)
            check("still flagged deletable", listed(c, A, once_email)["deletable"], True)
            check("deleted", c.delete(
                f"{BASE}/users/{once_id}/permanent", headers=A).status_code, 204)
        finally:
            # Best effort if a check above failed half-way: delete, else deactivate.
            for uid in created:
                if c.delete(f"{BASE}/users/{uid}/permanent", headers=A).status_code == 409:
                    c.delete(f"{BASE}/users/{uid}", headers=A)


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

        print("\n5. Audit entries - rolled back, nothing is kept")
        uid = uuid.uuid4()
        await db.execute(text("""
            INSERT INTO users (id, role, email, password_hash, full_name)
            VALUES (:id, 'admin', :email, 'x', 'Uji Hapus')"""),
            {"id": uid, "email": f"uji.hapus.{uid.hex[:8]}@neonatal.rs"})

        async def audit(action):
            await db.execute(text(
                "INSERT INTO audit_logs (user_id, action, table_name) VALUES (:u, :a, 'incubators')"),
                {"u": uid, "a": action})

        await audit("LOGIN")
        check("a LOGIN entry does not make an account undeletable",
              uid in await _users_with_records(db), False)
        await audit("UPDATE")
        check("any other audited action does", uid in await _users_with_records(db), True)
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
