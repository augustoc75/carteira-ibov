from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "sqlite:///./ibovespa_local.db"
    playwright_timeout: int = 30000
    log_level: str = "INFO"
    gcs_bucket_name: str = "dadosb3"
    gcs_folder: str = "comp-ibov"
    
    class Config:
        env_file = ".env"


@lru_cache
def get_settings():
    return Settings()
