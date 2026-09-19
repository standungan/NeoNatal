from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.assignment_repository import AssignmentRepository
from app.repositories.device_repository import DeviceRepository
from app.repositories.sensor_reading_repository import SensorReadingRepository
from app.repositories.incubator_repository import IncubatorRepository
from app.repositories.monitoring_repository import MonitoringRepository
from app.schemas.dashboard import (
    BabySummary,
    DashboardResponse,
    DashboardStats,
    IncubatorDashboardItem,
    LatestVitals,
)
from app.services.monitoring_service import _check_vital_status


async def get_dashboard(db: AsyncSession) -> DashboardResponse:
    inc_repo = IncubatorRepository(db)
    incubators = await inc_repo.get_all_with_assignment()

    # collect all active baby_ids for a single monitoring batch query
    active_baby_ids = [
        a.baby_id
        for inc in incubators
        for a in inc.assignments
        if a.status == "active"
    ]
    latest_vitals_map = await MonitoringRepository(db).get_latest_per_baby(active_baby_ids)

    # One query for every incubator's device, not one per card.
    incubator_ids = [inc.incubator_id for inc in incubators]
    devices_map = await DeviceRepository(db).get_by_incubator_ids(incubator_ids)
    # One windowed query for every card's sparkline, not one per card — cut at each
    # incubator's current occupancy, so a new baby's card never trends the last one.
    starts = await AssignmentRepository(db).occupancy_starts(incubator_ids)
    sparklines = await SensorReadingRepository(db).sparkline_by_incubator(
        incubator_ids, since=starts
    )

    items: list[IncubatorDashboardItem] = []
    for inc in incubators:
        active = next((a for a in inc.assignments if a.status == "active"), None)

        baby_summary = None
        vitals_summary = None

        if active and active.baby:
            baby = active.baby
            age_days = (date.today() - baby.birth_date).days
            baby_summary = BabySummary(
                baby_id=baby.baby_id,
                baby_name=baby.baby_name,
                age_in_days=age_days,
                birth_weight=baby.birth_weight,
                assigned_at=active.assigned_at,
            )

            latest = latest_vitals_map.get(baby.baby_id)
            if latest:
                vitals_summary = LatestVitals(
                    suhu_bayi=latest.suhu_bayi,
                    heart_rate=latest.heart_rate,
                    spo2=latest.spo2,
                    observation_time=latest.observation_time,
                    vital_status=_check_vital_status(
                        latest.heart_rate, latest.spo2, latest.suhu_bayi
                    ),
                )

        device = devices_map.get(inc.incubator_id)
        items.append(IncubatorDashboardItem(
            incubator_id=inc.incubator_id,
            incubator_no=inc.incubator_no,
            location=inc.location,
            status=inc.status,
            current_baby=baby_summary,
            latest_vitals=vitals_summary,
            has_device=device is not None,
            device_last_seen_at=device.last_seen_at if device else None,
            sparkline=sparklines.get(inc.incubator_id, []),
        ))

    stats = DashboardStats(
        total=len(incubators),
        terisi=sum(1 for i in incubators if i.status == "terisi"),
        kosong=sum(1 for i in incubators if i.status == "kosong"),
        warning=sum(1 for i in incubators if i.status == "warning"),
        tidak_tersedia=sum(1 for i in incubators if i.status == "tidak_tersedia"),
    )

    return DashboardResponse(stats=stats, incubators=items)
