"""Read-only smoke test: every backend module answers, and RBAC holds.

Complements telemetry_check.py (which covers POST /telemetry in depth). This one
sweeps GET endpoints across all ten modules plus the role guards, so a broken
service, migration or dependency shows up immediately after an environment change.

Deliberately READ-ONLY -- it creates nothing and deletes nothing, so it is safe to
run against the seeded dev database as often as you like.

Needs a LIVE backend on :8000 and the seeded database:

    python -m uvicorn app.main:app --port 8000     # in one shell
    python tests/smoke_check.py                    # in another

Exits non-zero on any failure.
"""
import sys

import httpx

BASE = "http://localhost:8000/api/v1"
PW = "Password123!"
ACCOUNTS = {
    "admin": "admin@neonatal.rs",
    "perawat": "siti.aisyah@neonatal.rs",
    "dokter": "dr.anisa@neonatal.rs",
}

results = []


def check(name, got, want):
    ok = got == want if not callable(want) else want(got)
    results.append((ok, name))
    label = want.__doc__ if callable(want) else repr(want)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got {got!r}, want {label}")


def unauthorized(c):
    """401 or 403"""
    # FastAPI's HTTPBearer answers 403 when the Authorization header is missing
    # entirely, and 401 only when a token is present but bad. Both mean "refused".
    return c in (401, 403)


def main():
    with httpx.Client(timeout=30) as c:
        print("\n1. Auth — all three seeded roles")
        tok = {}
        for role, email in ACCOUNTS.items():
            r = c.post(f"{BASE}/auth/login", json={"email": email, "password": PW})
            check(f"login as {role}", r.status_code, 200)
            if r.status_code == 200:
                tok[role] = r.json()["access_token"]
        if "admin" not in tok:
            print("\n!! cannot continue without an admin token")
            return 1

        H = {r: {"Authorization": f"Bearer {t}"} for r, t in tok.items()}
        A = H["admin"]

        check("unauthenticated /auth/me refused", c.get(f"{BASE}/auth/me").status_code, unauthorized)
        check("/auth/me as admin", c.get(f"{BASE}/auth/me", headers=A).status_code, 200)

        print("\n2. Dashboard & incubators")
        check("dashboard", c.get(f"{BASE}/dashboard", headers=A).status_code, 200)
        r = c.get(f"{BASE}/incubators", headers=A)
        check("incubators list", r.status_code, 200)
        incs = r.json() if r.status_code == 200 else []
        incs = incs if isinstance(incs, list) else incs.get("items", [])
        check("incubators seeded", len(incs) > 0, True)
        check("incubators/available", c.get(f"{BASE}/incubators/available", headers=A).status_code, 200)

        inc_id = incs[0].get("incubator_id") if incs else None
        if inc_id:
            check("incubator detail", c.get(f"{BASE}/incubators/{inc_id}", headers=A).status_code, 200)
            check("incubator thresholds", c.get(f"{BASE}/incubators/{inc_id}/thresholds", headers=A).status_code, 200)

        print("\n3. Babies")
        r = c.get(f"{BASE}/babies", headers=A)
        check("babies list", r.status_code, 200)
        babies = r.json() if r.status_code == 200 else []
        babies = babies if isinstance(babies, list) else babies.get("items", [])
        check("babies seeded", len(babies) > 0, True)
        baby_id = babies[0].get("baby_id") if babies else None
        if baby_id:
            check("baby detail", c.get(f"{BASE}/babies/{baby_id}", headers=A).status_code, 200)

        print("\n4. Catalogs — the single source of truth for the 3 scored instruments")
        for name in ("observation", "involvement", "aksi"):
            r = c.get(f"{BASE}/{name}/catalog", headers=A)
            check(f"{name}/catalog", r.status_code, 200)

        if baby_id:
            print("\n5. Per-baby clinical records")
            for path in (
                "monitoring?skip=0&limit=50",
                "observation?skip=0&limit=50",
                "involvement?skip=0&limit=50",
                "involvement/summary",
                "aksi?skip=0&limit=50",
                "aksi/summary",
            ):
                r = c.get(f"{BASE}/babies/{baby_id}/{path}", headers=A)
                check(f"babies/*/{path.split('?')[0]}", r.status_code, 200)

            print("\n6. Reports")
            r = c.get(f"{BASE}/babies/{baby_id}/report", headers=A)
            check("report json", r.status_code, 200)
            if r.status_code == 200:
                body = r.json()
                for key in ("baby", "monitoring_history", "observation_latest", "aksi_latest"):
                    check(f"report contains {key}", key in body, True)
            r = c.get(f"{BASE}/babies/{baby_id}/report/pdf", headers=A)
            check("report pdf status", r.status_code, 200)
            if r.status_code == 200:
                check("pdf magic bytes", r.content[:4], b"%PDF")
                check("pdf non-trivial size", len(r.content) > 5000, True)

        print("\n7. Admin-only surfaces")
        check("users list as admin", c.get(f"{BASE}/users", headers=A).status_code, 200)
        check("doctors dropdown", c.get(f"{BASE}/users/doctors", headers=A).status_code, 200)
        check("audit logs as admin", c.get(f"{BASE}/audit-logs?skip=0&limit=100", headers=A).status_code, 200)

        print("\n8. RBAC — non-admins must be refused")
        for role in ("perawat", "dokter"):
            if role in H:
                check(f"{role} -> /users is 403", c.get(f"{BASE}/users", headers=H[role]).status_code, 403)
                check(f"{role} -> /audit-logs is 403", c.get(f"{BASE}/audit-logs", headers=H[role]).status_code, 403)
        if "dokter" in H:
            check("dokter can read dashboard", c.get(f"{BASE}/dashboard", headers=H["dokter"]).status_code, 200)

    passed = sum(1 for ok, _ in results if ok)
    total = len(results)
    print(f"\n{passed}/{total} passed")
    if passed != total:
        print("\nFailures:")
        for ok, name in results:
            if not ok:
                print("  -", name)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
