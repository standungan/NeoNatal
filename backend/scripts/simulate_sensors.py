"""Background IoT telemetry simulator for live demos and presentations.

Streams realistic vital-sign and incubator-environment readings into
`POST /api/v1/telemetry` for every active incubator using the exact same
`X-Device-Key` authentication path that the ESP8266 rigs use.

    python scripts/simulate_sensors.py                 # against localhost:8000
    SIM_API_URL=http://backend:8000 python scripts/simulate_sensors.py

On startup it waits for `/health`, logs in as admin, ensures each eligible
incubator has a provisioned device key (persisted to `SIM_KEYS_FILE` so container
restarts do not re-mint keys), and then posts smooth mean-reverting samples at
`SIM_INTERVAL_SECONDS` (default 5s — well inside the 30s online window).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import pathlib
import random
import signal
from dataclasses import dataclass, field
from typing import Any

import httpx

logging.basicConfig(
    level=os.getenv("SIM_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [sim] %(levelname)s %(message)s",
)
log = logging.getLogger("simulate_sensors")

API_URL = os.getenv("SIM_API_URL", "http://backend:8000").rstrip("/")
ADMIN_EMAIL = os.getenv("SIM_ADMIN_EMAIL", "admin@neonatal.rs")
ADMIN_PASSWORD = os.getenv("SIM_ADMIN_PASSWORD", "Password123!")
INTERVAL_S = float(os.getenv("SIM_INTERVAL_SECONDS", "5.0"))
REFRESH_S = float(os.getenv("SIM_REFRESH_SECONDS", "60.0"))
INCLUDE_EMPTY = os.getenv("SIM_INCLUDE_EMPTY", "true").lower() in ("1", "true", "yes")
DEFAULT_KEYS_PATH = "/data/sim_keys.json" if pathlib.Path("/data").exists() else ".sim_keys.json"
KEYS_FILE = pathlib.Path(os.getenv("SIM_KEYS_FILE", DEFAULT_KEYS_PATH))


@dataclass(frozen=True)
class MetricSpec:
    low: float
    high: float
    target: float
    step_std: float
    decimals: int = 1


# Profiles stay aligned with seed_data.sql and DEFAULT_THRESHOLDS:
# - Normal occupied units stay strictly inside thresholds (no spurious alerts).
# - Warning units (e.g., INC-04 / INC-06) drift near/across their warning bounds
#   so the alert engine opens real SensorAlert rows for the live alert feed.
# - Empty ('kosong') units only report ambient incubator temperature & humidity.
PROFILES: dict[str, dict[str, MetricSpec | None]] = {
    "normal": {
        "suhu_bayi": MetricSpec(36.5, 37.2, 36.85, 0.04, 1),
        "suhu_inkubator": MetricSpec(34.3, 35.4, 34.80, 0.06, 1),
        "kelembapan_inkubator": MetricSpec(63.0, 73.0, 67.50, 0.35, 1),
        "heart_rate": MetricSpec(124.0, 148.0, 136.0, 1.8, 0),
        "spo2": MetricSpec(96.0, 99.5, 98.0, 0.25, 1),
    },
    "warning_warm": {
        "suhu_bayi": MetricSpec(37.55, 37.85, 37.70, 0.03, 1),
        "suhu_inkubator": MetricSpec(34.5, 35.6, 35.0, 0.05, 1),
        "kelembapan_inkubator": MetricSpec(62.0, 70.0, 66.0, 0.3, 1),
        "heart_rate": MetricSpec(170.0, 179.0, 175.0, 1.5, 0),
        "spo2": MetricSpec(90.5, 91.8, 91.2, 0.2, 1),
    },
    "warning_desat": {
        "suhu_bayi": MetricSpec(36.2, 36.6, 36.4, 0.04, 1),
        "suhu_inkubator": MetricSpec(34.6, 35.6, 35.1, 0.05, 1),
        "kelembapan_inkubator": MetricSpec(64.0, 72.0, 68.0, 0.3, 1),
        "heart_rate": MetricSpec(168.0, 178.0, 173.0, 1.5, 0),
        "spo2": MetricSpec(91.0, 92.6, 91.8, 0.2, 1),
    },
    "empty": {
        "suhu_bayi": None,
        "suhu_inkubator": MetricSpec(34.3, 35.1, 34.7, 0.05, 1),
        "kelembapan_inkubator": MetricSpec(62.0, 70.0, 65.5, 0.3, 1),
        "heart_rate": None,
        "spo2": None,
    },
}


@dataclass
class IncubatorSim:
    incubator_id: str
    incubator_no: str
    status: str
    has_baby: bool
    profile_name: str
    device_key: str
    rng: random.Random
    state: dict[str, float] = field(default_factory=dict)

    def next_payload(self) -> dict[str, float | int | None]:
        profile = PROFILES[self.profile_name]
        payload: dict[str, float | int | None] = {}
        for key, spec in profile.items():
            if spec is None:
                payload[key] = None
                continue
            prev = self.state.get(key, spec.target)
            # Ornstein-Uhlenbeck-style mean reversion keeps lines smooth and natural.
            pull = 0.15 * (spec.target - prev)
            nxt = prev + pull + self.rng.gauss(0.0, spec.step_std)
            nxt = max(spec.low, min(spec.high, nxt))
            self.state[key] = nxt
            payload[key] = int(round(nxt)) if spec.decimals == 0 else round(nxt, spec.decimals)
        return payload


def _load_keys() -> dict[str, str]:
    if not KEYS_FILE.exists():
        return {}
    try:
        data = json.loads(KEYS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("Ignoring unreadable keys file %s: %s", KEYS_FILE, exc)
        return {}


def _save_keys(keys: dict[str, str]) -> None:
    KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
    KEYS_FILE.write_text(json.dumps(keys, indent=2, sort_keys=True), encoding="utf-8")


def _choose_profile(inc: dict[str, Any], initial_status: str | None = None) -> str | None:
    status = inc.get("status")
    if inc.get("archived_at") is not None or status == "tidak_tersedia":
        return None
    has_baby = inc.get("current_baby") is not None
    if not has_baby:
        return "empty" if INCLUDE_EMPTY else None

    effective = initial_status or status
    if effective == "warning":
        return "warning_desat" if inc.get("incubator_no") == "06" else "warning_warm"
    return "normal"


async def _wait_for_health(client: httpx.AsyncClient, stop: asyncio.Event) -> None:
    delay = 1.0
    while not stop.is_set():
        try:
            r = await client.get(f"{API_URL}/health")
            if r.status_code == 200:
                log.info("Backend healthy at %s", API_URL)
                return
        except httpx.HTTPError as exc:
            log.info("Waiting for backend (%s): %s", API_URL, exc)
        try:
            await asyncio.wait_for(stop.wait(), timeout=delay)
        except asyncio.TimeoutError:
            delay = min(delay * 1.5, 10.0)


async def _login(client: httpx.AsyncClient) -> str:
    r = await client.post(
        f"{API_URL}/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    r.raise_for_status()
    return r.json()["access_token"]


async def _ensure_device_key(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    inc: dict[str, Any],
    keys: dict[str, str],
    force_reprovision: bool = False,
) -> str:
    inc_id = inc["incubator_id"]
    inc_no = inc["incubator_no"]

    if not force_reprovision and inc_id in keys:
        return keys[inc_id]

    existing = await client.get(f"{API_URL}/api/v1/incubators/{inc_id}/device", headers=headers)
    existing.raise_for_status()
    if existing.json() is not None:
        # DB only stores the SHA-256 hash; if our local key file does not have
        # the plaintext (or the key was rejected with 401), replace the binding.
        del_resp = await client.delete(f"{API_URL}/api/v1/incubators/{inc_id}/device", headers=headers)
        del_resp.raise_for_status()

    prov = await client.post(
        f"{API_URL}/api/v1/incubators/{inc_id}/device",
        headers=headers,
        json={"label": f"Sim Sensor — INC-{inc_no}"},
    )
    prov.raise_for_status()
    key = prov.json()["device_key"]
    keys[inc_id] = key
    _save_keys(keys)
    log.info("Provisioned simulated device for INC-%s", inc_no)
    return key


async def _sync_incubators(
    client: httpx.AsyncClient,
    sims: dict[str, IncubatorSim],
    initial_statuses: dict[str, str],
    keys: dict[str, str],
) -> None:
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.get(f"{API_URL}/api/v1/incubators", headers=headers)
    r.raise_for_status()
    incubators = r.json()

    active_ids: set[str] = set()
    for inc in incubators:
        inc_id = inc["incubator_id"]
        inc_no = inc["incubator_no"]
        initial_statuses.setdefault(inc_id, inc["status"])
        profile_name = _choose_profile(inc, initial_statuses[inc_id])
        if profile_name is None:
            continue

        active_ids.add(inc_id)
        key = await _ensure_device_key(client, headers, inc, keys)
        if inc_id in sims:
            sims[inc_id].status = inc["status"]
            sims[inc_id].has_baby = inc.get("current_baby") is not None
            sims[inc_id].profile_name = profile_name
            sims[inc_id].device_key = key
        else:
            sims[inc_id] = IncubatorSim(
                incubator_id=inc_id,
                incubator_no=inc_no,
                status=inc["status"],
                has_baby=inc.get("current_baby") is not None,
                profile_name=profile_name,
                device_key=key,
                rng=random.Random(f"sim-{inc_id}"),
            )

    for removed in set(sims) - active_ids:
        sims.pop(removed, None)

    log.info("Tracking %d active simulated incubators", len(sims))


async def _post_sample(
    client: httpx.AsyncClient,
    sim: IncubatorSim,
    keys: dict[str, str],
) -> None:
    payload = sim.next_payload()
    r = await client.post(
        f"{API_URL}/api/v1/telemetry",
        headers={"X-Device-Key": sim.device_key},
        json=payload,
    )
    if r.status_code == 401:
        log.warning("Key rejected for INC-%s (401); re-provisioning", sim.incubator_no)
        token = await _login(client)
        headers = {"Authorization": f"Bearer {token}"}
        sim.device_key = await _ensure_device_key(
            client,
            headers,
            {"incubator_id": sim.incubator_id, "incubator_no": sim.incubator_no},
            keys,
            force_reprovision=True,
        )
        r = await client.post(
            f"{API_URL}/api/v1/telemetry",
            headers={"X-Device-Key": sim.device_key},
            json=payload,
        )

    if r.status_code not in (201, 202):
        log.warning(
            "INC-%s (%s) returned HTTP %s: %s",
            sim.incubator_no,
            sim.profile_name,
            r.status_code,
            r.text[:200],
        )


async def run() -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            # Windows event loops do not support add_signal_handler.
            pass

    keys = _load_keys()
    sims: dict[str, IncubatorSim] = {}
    initial_statuses: dict[str, str] = {}

    async with httpx.AsyncClient(timeout=10.0) as client:
        await _wait_for_health(client, stop)
        if stop.is_set():
            return

        last_sync = 0.0
        tick = 0
        while not stop.is_set():
            now = loop.time()
            if not sims or (now - last_sync) >= REFRESH_S:
                try:
                    await _sync_incubators(client, sims, initial_statuses, keys)
                    last_sync = now
                except httpx.HTTPError as exc:
                    log.warning("Failed to sync incubators: %s", exc)

            if sims:
                results = await asyncio.gather(
                    *(_post_sample(client, sim, keys) for sim in sims.values()),
                    return_exceptions=True,
                )
                errors = [res for res in results if isinstance(res, Exception)]
                if errors:
                    log.warning("%d sample post(s) failed: %s", len(errors), errors[0])
                tick += 1
                if tick == 1 or tick % 12 == 0:
                    log.info("Streamed batch #%d to %d incubator(s)", tick, len(sims))

            try:
                await asyncio.wait_for(stop.wait(), timeout=INTERVAL_S)
            except asyncio.TimeoutError:
                pass


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
