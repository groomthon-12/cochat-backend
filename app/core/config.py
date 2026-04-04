from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    ASYNC_DATABASE_URL: str

    # Discord
    DISCORD_BOT_TOKEN: str = ""
    DISCORD_APPLICATION_ID: str = ""
    DISCORD_CLIENT_ID: str = ""
    DISCORD_CLIENT_SECRET: str = ""
    DISCORD_REDIRECT_URI: str = "http://localhost:8000/api/v1/integrations/discord/callback"

    class Config:
        env_file = ".env"


settings = Settings()
