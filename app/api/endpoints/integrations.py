from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.integrations.discord.client import DiscordRestClient
from app.integrations.slack.client import SlackClient
from app.repositories.integration_repository import get_or_create_integration, upsert_token

router = APIRouter(tags=["integrations"])

# Bot server messages need at least VIEW_CHANNEL + READ_MESSAGE_HISTORY.
_DISCORD_BOT_PERMISSIONS = 66560


@router.get("/integrations")
def list_integrations():
    return {"integrations": []}


@router.get("/integrations/slack/oauth-url")
def get_slack_oauth_url():
    """Return the Slack OAuth installation URL."""
    scopes = "channels:history,channels:read,chat:write,groups:read,im:history,im:read,mpim:read,users:read"
    params = urlencode({
        "client_id": settings.SLACK_CLIENT_ID,
        "scope": scopes,
        "redirect_uri": settings.SLACK_REDIRECT_URI,
    })
    return {"url": f"https://slack.com/oauth/v2/authorize?{params}"}


@router.get("/integrations/slack/callback")
async def slack_oauth_callback(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """Exchange the Slack OAuth code and persist workspace/token data."""
    client = SlackClient(token="")

    try:
        token_data = await client.exchange_code(
            code=code,
            client_id=settings.SLACK_CLIENT_ID,
            client_secret=settings.SLACK_CLIENT_SECRET,
            redirect_uri=settings.SLACK_REDIRECT_URI,
        )
    except Exception as exc:  # pragma: no cover - delegated SDK failure
        raise HTTPException(status_code=400, detail="Slack authorization code exchange failed.") from exc

    access_token: str = token_data.get("access_token", "")
    team: dict = token_data.get("team", {})
    team_id: str = team.get("id", "")
    team_name: str = team.get("name", team_id)

    if not team_id:
        raise HTTPException(status_code=400, detail="Slack workspace information is missing.")

    async with db.begin():
        integration = await get_or_create_integration(
            db=db,
            provider="slack",
            account_identifier=team_id,
            account_name=team_name,
        )
        await upsert_token(
            db=db,
            integration_id=integration.id,
            access_token=access_token,
        )

    return {
        "status": "ok",
        "integration_id": integration.id,
        "team_id": team_id,
        "team_name": team_name,
    }


@router.get("/integrations/discord/oauth-url")
def get_discord_oauth_url():
    """Return the Discord bot installation URL."""
    params = urlencode({
        "client_id": settings.DISCORD_CLIENT_ID,
        "permissions": _DISCORD_BOT_PERMISSIONS,
        "scope": "bot identify guilds",
        "redirect_uri": settings.DISCORD_REDIRECT_URI,
        "response_type": "code",
    })
    return {"url": f"https://discord.com/oauth2/authorize?{params}"}


@router.get("/integrations/discord/callback")
async def discord_oauth_callback(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """Exchange the Discord OAuth code and persist guild/token data."""
    client = DiscordRestClient(bot_token=settings.DISCORD_BOT_TOKEN)

    try:
        token_data = await client.exchange_code(
            code=code,
            redirect_uri=settings.DISCORD_REDIRECT_URI,
            client_id=settings.DISCORD_CLIENT_ID,
            client_secret=settings.DISCORD_CLIENT_SECRET,
        )
    except Exception as exc:  # pragma: no cover - delegated SDK failure
        raise HTTPException(status_code=400, detail="Discord authorization code exchange failed.") from exc

    access_token: str = token_data["access_token"]
    refresh_token: str | None = token_data.get("refresh_token")
    expires_in: int | None = token_data.get("expires_in")
    expires_at: datetime | None = (
        datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        if expires_in
        else None
    )

    guild: dict | None = token_data.get("guild")
    if not guild:
        raise HTTPException(status_code=400, detail="Discord guild information is missing. Retry the bot install flow.")

    guild_id: str = guild["id"]
    guild_name: str = guild.get("name", guild_id)

    async with db.begin():
        integration = await get_or_create_integration(
            db=db,
            provider="discord",
            account_identifier=guild_id,
            account_name=guild_name,
        )
        await upsert_token(
            db=db,
            integration_id=integration.id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
        )

    return {
        "status": "ok",
        "integration_id": integration.id,
        "guild_id": guild_id,
        "guild_name": guild_name,
    }
