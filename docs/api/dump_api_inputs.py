"""Write the two inputs generate_api_html.py reads: openapi.json and roles_full.json.

    backend/venv/Scripts/python docs/api/dump_api_inputs.py <dir>
    backend/venv/Scripts/python docs/api/generate_api_html.py <dir> docs/deliverables/api.html

Roles are read off each route's dependency tree - the guards in app/api/deps.py that the
server actually enforces - rather than written by hand, so the reference cannot claim a
role the code does not check. Imports the app directly; no running server is needed.
"""
import json
import os
import pathlib
import sys

BACKEND = pathlib.Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)  # settings read backend/.env

from dotenv import load_dotenv  # noqa: E402

load_dotenv(".env")

from fastapi.routing import APIRoute  # noqa: E402

from app.api.deps import get_current_device, get_current_user  # noqa: E402
from app.main import app  # noqa: E402

LABEL = {
    ("admin",): "admin",
    ("perawat", "admin"): "perawat + admin",
    ("dokter",): "dokter",
}


def guards(dep, found):
    """Every guard anywhere under this dependant: a device key, a signed-in user, or
    the role tuple captured by a require_roles(...) closure."""
    for d in dep.dependencies:
        call = d.call
        if call is get_current_device:
            found.add("device")
        elif call is get_current_user:
            found.add("user")
        elif getattr(call, "__name__", "") == "_check" and call.__closure__:
            for cell in call.__closure__:
                if isinstance(cell.cell_contents, tuple):
                    found.add(cell.cell_contents)
        guards(d, found)
    return found


def main(out: pathlib.Path) -> None:
    roles = {}
    for r in app.routes:
        if not isinstance(r, APIRoute):
            continue
        g = guards(r.dependant, set())
        tuples = [x for x in g if isinstance(x, tuple)]
        if "device" in g:
            label = "IoT device (X-Device-Key)"
        elif tuples:
            label = LABEL[tuples[0]]
        elif "user" in g:
            label = "any signed-in role"
        else:
            label = "public"
        for m in r.methods - {"HEAD", "OPTIONS"}:
            roles[f"{m} {r.path}"] = label

    out.mkdir(parents=True, exist_ok=True)
    (out / "openapi.json").write_text(json.dumps(app.openapi()), encoding="utf-8")
    (out / "roles_full.json").write_text(json.dumps(roles, indent=1), encoding="utf-8")
    counts = {v: list(roles.values()).count(v) for v in sorted(set(roles.values()))}
    print(f"  {len(roles)} operations -> {out}: {counts}")


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]).resolve())
