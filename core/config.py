from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ENV: str = "development"
    TRUSTED_HOSTS: list[str] = ["127.0.0.1"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Singleton — import this everywhere instead of instantiating Settings() again
settings = Settings()
