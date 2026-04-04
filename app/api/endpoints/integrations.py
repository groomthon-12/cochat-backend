from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.integrations.discord.client import DiscordRestClient
from app.integrations.slack.client import SlackClient
from app.repositories.integration_repository import (
    get_or_create_integration,
    get_or_create_user_integration,
    list_integrations_by_user,
    upsert_token,
)

router = APIRouter(tags=["integrations"])

# Bot server messages need at least VIEW_CHANNEL + READ_MESSAGE_HISTORY.
_DISCORD_BOT_PERMISSIONS = 66560

_SLACK_USER_SCOPES = ",".join([
    "channels:history",
    "channels:read",
    "groups:history",
    "groups:read",
    "im:history",
    "im:read",
    "mpim:history",
    "mpim:read",
    "users:read",
])


def _require_current_user_id(
    x_cochat_user_id: str | None = Header(default=None, alias="X-Cochat-User-Id"),
) -> int:
    """Temporary auth stub until real login/session middleware is wired in."""
    if not x_cochat_user_id:
        raise HTTPException(status_code=401, detail="Missing X-Cochat-User-Id header.")

    try:
        user_id = int(x_cochat_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid X-Cochat-User-Id header.") from exc

    if user_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid X-Cochat-User-Id header.")

    return user_id


def _build_slack_oauth_state(app_user_id: int) -> str:
    payload = {
        "provider": "slack",
        "app_user_id": app_user_id,
        "nonce": secrets.token_urlsafe(16),
        "iat": int(time.time()),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
    secret = settings.SLACK_CLIENT_SECRET.encode()
    signature = hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest().encode()
    token = base64.urlsafe_b64encode(payload_bytes + b"." + signature).decode().rstrip("=")
    return token


def _parse_slack_oauth_state(state: str) -> dict:
    try:
        padded = state + "=" * (-len(state) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode())
        payload_bytes, signature = decoded.rsplit(b".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid Slack OAuth state.") from exc

    expected = hmac.new(
        settings.SLACK_CLIENT_SECRET.encode(),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest().encode()

    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=400, detail="Invalid Slack OAuth state signature.")

    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid Slack OAuth state payload.") from exc

    if payload.get("provider") != "slack":
        raise HTTPException(status_code=400, detail="Unexpected Slack OAuth state provider.")

    if int(time.time()) - int(payload.get("iat", 0)) > 600:
        raise HTTPException(status_code=400, detail="Slack OAuth state expired.")

    return payload


@router.get("/integrations")
def list_integrations():
    return {"integrations": []}


@router.get("/integrations/slack/oauth-url")
def get_slack_oauth_url(
    current_user_id: int = Depends(_require_current_user_id),
):
    """Return a user-scoped Slack OAuth URL for the current application user."""
    state = _build_slack_oauth_state(current_user_id)
    params = urlencode({
        "client_id": settings.SLACK_CLIENT_ID,
        "user_scope": _SLACK_USER_SCOPES,
        "redirect_uri": settings.SLACK_REDIRECT_URI,
        "state": state,
    })
    return {
        "url": f"https://slack.com/oauth/v2/authorize?{params}",
        "state": state,
        "user_id": current_user_id,
    }


@router.get("/integrations/slack/callback")
async def slack_oauth_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """Exchange the Slack OAuth code and persist a user-scoped Slack integration."""
    state_payload = _parse_slack_oauth_state(state)
    app_user_id = int(state_payload["app_user_id"])
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

    authed_user: dict = token_data.get("authed_user", {})
    access_token: str = authed_user.get("access_token") or token_data.get("access_token", "")
    slack_user_id: str = authed_user.get("id", "")
    team: dict = token_data.get("team", {})
    team_id: str = team.get("id", "")
    team_name: str = team.get("name", team_id)

    if not team_id or not slack_user_id or not access_token:
        raise HTTPException(status_code=400, detail="Slack user authorization data is missing.")

    account_identifier = f"{team_id}:{slack_user_id}"

    async with db.begin():
        integration = await get_or_create_user_integration(
            db=db,
            user_id=app_user_id,
            provider="slack",
            account_identifier=account_identifier,
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
        "app_user_id": app_user_id,
        "team_id": team_id,
        "team_name": team_name,
        "slack_user_id": slack_user_id,
        "account_identifier": account_identifier,
    }


@router.get("/integrations/slack/connection")
async def get_slack_connection(
    current_user_id: int = Depends(_require_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Return the current user's Slack connection status."""
    integrations = await list_integrations_by_user(
        db=db,
        user_id=current_user_id,
        provider="slack",
    )
    return {
        "connected": len(integrations) > 0,
        "integrations": [
            {
                "integration_id": integration.id,
                "account_identifier": integration.account_identifier,
                "account_name": integration.account_name,
                "status": integration.status,
            }
            for integration in integrations
        ],
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
