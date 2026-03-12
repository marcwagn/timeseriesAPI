from pydantic_settings import BaseSettings
from pathlib import Path


class Config(BaseSettings):
    app_name: str = ""
    debug: bool = False

    timescale_user: str = ""
    timescale_password: str = ""
    timescale_dsn: str = ""

    migration_user: str = "postgres"
    migration_password: str = "postgres"

    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    log_level: str = "INFO"

    model_config = {
        "env_file": Path(__file__).resolve().parent.parent / ".env",
        "env_file_encoding": "utf-8",
    }

    @property
    def db_host(self) -> str:
        return self.timescale_dsn.split("/")[0].split(":")[0]

    @property
    def db_port(self) -> int:
        return int(self.timescale_dsn.split("/")[0].split(":")[1])

    @property
    def db_name(self) -> str:
        return self.timescale_dsn.split("/")[-1]

    @property
    def db_timescale_url(self) -> str:
        return f"timescaledb+asyncpg://{self.timescale_user}:{self.timescale_password}@{self.timescale_dsn}"

    @property
    def db_migration_url(self) -> str:
        return f"timescaledb+asyncpg://{self.migration_user}:{self.migration_password}@{self.timescale_dsn}"


config = Config()
