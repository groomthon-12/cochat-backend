from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    ASYNC_DATABASE_URL: str
    MASTER_USER_ID: int = 1

    # Discord
    DISCORD_BOT_TOKEN: str = ""
    DISCORD_APPLICATION_ID: str = ""
    DISCORD_CLIENT_ID: str = ""
    DISCORD_CLIENT_SECRET: str = ""
    DISCORD_REDIRECT_URI: str = "http://localhost:8000/api/v1/integrations/discord/callback"

    # Google
    GOOGLE_API_KEY: str = ""

    # Slack
    SLACK_BOT_TOKEN: str = ""
    SLACK_SIGNING_SECRET: str = ""
    SLACK_CLIENT_ID: str = ""
    SLACK_CLIENT_SECRET: str = ""
    SLACK_REDIRECT_URI: str = "http://localhost:8000/api/v1/integrations/slack/callback"

    class Config:
        env_file = ".env"


settings = Settings()
