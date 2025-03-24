from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ORIGINS: list
    API_URL: str
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"

    class Config:
        env_file = ".env"


settings = Settings()
