from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AlgoPlatform - Indian Stock Exchange"
    version: str = "1.0.0"
    database_url: str = "sqlite+aiosqlite:///./algoplatform.db"
    initial_capital: float = 1_000_000.0  # ₹10 Lakh paper trading capital

    # OpenAlgo broker integration settings (loaded from .env or environment variables)
    openalgo_host: str = "http://127.0.0.1:5000"
    openalgo_api_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
