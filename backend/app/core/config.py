from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Neonatal Care System"
    app_version: str = "1.0.0"
    debug: bool = False
    secret_key: str

    database_url: str

    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    storage_backend: str = "local"
    storage_local_path: str = "./uploads"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_bucket_name: str = ""
    aws_region: str = "ap-southeast-1"

    allowed_origins: str = "http://localhost:3000"

    # Legacy prototype ingest (POST /api/sensors). UNAUTHENTICATED: anything that
    # can reach the port may write vitals, so it is off unless a deployment opts
    # in. Enabled in the lab because the bench rig runs prototype firmware; the
    # authenticated path is POST /api/v1/telemetry with X-Device-Key.
    legacy_sensor_ingest: bool = False

    # Sensor retention (updates03 P4). Raw readings are rolled into 1-minute
    # buckets and then dropped past this window. 0 or less keeps everything —
    # a misread config should err towards keeping too much, never deleting.
    sensor_retention_days: int = 7
    # Hours between automatic runs. 0 disables the in-process job entirely, for
    # deployments that would rather drive it from cron.
    sensor_retention_interval_hours: int = 6

    @field_validator("database_url")
    @classmethod
    def force_async_driver(cls, v: str) -> str:
        # Managed hosts (Render, Neon, Supabase) hand out `postgresql://…`, but
        # every consumer here is SQLAlchemy's async engine, which needs asyncpg.
        for prefix in ("postgresql://", "postgres://"):
            if v.startswith(prefix):
                return "postgresql+asyncpg://" + v[len(prefix):]
        return v

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    class Config:
        env_file = ".env"


settings = Settings()
