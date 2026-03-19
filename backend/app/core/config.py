from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AlgoPlatform - Indian Stock Exchange"
    version: str = "1.0.0"
    database_url: str = "sqlite+aiosqlite:///./algoplatform.db"
    initial_capital: float = 1_000_000.0  # ₹10 Lakh paper trading capital

    # Zerodha Kite Connect credentials (loaded from .env or environment variables)
    # These are convenience env-var overrides; the UI stores credentials in the DB.
    kite_api_key: str = ""
    kite_access_token: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

