from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL : str
    JWT_SECRET_KEY : str
    SESSION_SECRET_KEY : str
    ALGORITHM : str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES : int = 30
    SESSION_EXPIRE_MINUTES : int = 30
    GITHUB_CLIENT_ID : str
    GITHUB_CLIENT_SECRET : str
    GOOGLE_CLIENT_ID : str
    GOOGLE_CLIENT_SECRET : str

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()