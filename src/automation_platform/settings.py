from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Load .env automatically
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    
    SQLALCHEMY_DATABASE_URI: str
    MS_CLIENT_ID: str
    MS_CLIENT_SECRET: str
    MS_TENANT_ID: str
    SECRET_KEY: str

settings = Settings()
