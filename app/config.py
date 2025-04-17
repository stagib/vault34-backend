from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ORIGINS: list
    API_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"

    # db
    DATABASE_URL: str
    NEO4J_URI: str
    NEO4J_USER: str
    NEO4J_PASSWORD: str

    class Config:
        env_file = ".env"


settings = Settings()
