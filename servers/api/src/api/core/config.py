from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True

    # Security (switchable)
    bypass_auth: bool = True  # Set False when Firebase auth is implemented
    bypass_cors: bool = True  # Set False for stricter CORS in production

    # CORS origins (only used if bypass_cors=False)
    cors_origins: list[str] = [
        "chrome-extension://*",
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    # Hardcoded user ID (only used when bypass_auth=True)
    default_user_id: str = "hardcoded-user-123"

# Lazy initialization (singleton)
_settings: Settings | None = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
