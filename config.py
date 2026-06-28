from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    playwright_timeout: int = 60000
    log_level: str = "INFO"
    gcs_bucket_name: str = "dadosb3"
    gcs_folder: str = "comp-ibov"
    
    class Config:
        env_file = ".env"


@lru_cache
def get_settings():
    return Settings()
