from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    
    telegram_bot_token: str

    enable_embedded_worker: bool = True
    worker_poll_seconds: float = 15.0

    model_config = SettingsConfigDict(
        env_file=".env"
    )


settings = Settings()