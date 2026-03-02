from pydantic_settings import BaseSettings
from pathlib import Path


class Config(BaseSettings):
    app_name: str = ""
    debug: bool = False

    timescale_user: str = ""
    timescale_password: str = ""
    timescale_dsn: str = "localhost:5432"

    model_config = {
        "env_file": Path(__file__).resolve().parent.parent / ".env",
        "env_file_encoding": "utf-8",
    }

    @property
    def db_timescale_url(self):
        return f"timescaledb+asyncpg://{self.timescale_user}:{self.timescale_password}@{self.timescale_dsn}"


config = Config()
