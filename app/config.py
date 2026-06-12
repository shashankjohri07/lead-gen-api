from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/leadgen"
    REDIS_URL: str = "redis://localhost:6379/0"
    GOOGLE_MAPS_API_KEY: str = ""
    TRUECALLER_API_KEY: str = ""
    HUNTER_API_KEY: str = ""
    API_SECRET_KEY: str = "changeme"

    class Config:
        env_file = ".env"


settings = Settings()
