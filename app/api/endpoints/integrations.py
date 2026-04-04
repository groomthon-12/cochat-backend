from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.integrations.discord.client import DiscordRestClient
from app.repositories.integration_repository import get_or_create_integration, upsert_token

router = APIRouter(tags=["integrations"])

# Bot이 서버에서 메시지를 읽기 위한 최소 권한
# VIEW_CHANNEL(1024) + READ_MESSAGE_HISTORY(65536)
_DISCORD_BOT_PERMISSIONS = 66560


@router.get("/integrations")
def list_integrations():
    """연동된 플랫폼 목록 조회"""
    return {"integrations": []}


@router.get("/integrations/slack/oauth-url")
def get_slack_oauth_url():
    """Slack OAuth 인증 URL 반환"""
    return {"url": ""}


@router.get("/integrations/slack/callback")
def slack_oauth_callback(code: str = "", state: str = ""):
    """Slack OAuth 콜백 처리"""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Discord
# ---------------------------------------------------------------------------


@router.get("/integrations/discord/oauth-url")
def get_discord_oauth_url():
    """Discord 봇 초대 + 사용자 인증 URL 반환.

    반환된 URL로 사용자를 리다이렉트하면 Discord가 서버 선택 화면을 보여준다.
    인증 완료 후 /integrations/discord/callback 으로 code가 전달된다.
    """
    params = urlencode({
        "client_id": settings.DISCORD_CLIENT_ID,
        "permissions": _DISCORD_BOT_PERMISSIONS,
        "scope": "bot identify guilds",
        "redirect_uri": settings.DISCORD_REDIRECT_URI,
        "response_type": "code",
    })
    url = f"https://discord.com/oauth2/authorize?{params}"
    return {"url": url}


@router.get("/integrations/discord/callback")
async def discord_oauth_callback(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """Discord OAuth 콜백 처리.

    1. code → access_token 교환
    2. 사용자 정보 조회
    3. IntegrationAccount + IntegrationToken DB 저장
    """
    client = DiscordRestClient(bot_token=settings.DISCORD_BOT_TOKEN)

    try:
        token_data = await client.exchange_code(
            code=code,
            redirect_uri=settings.DISCORD_REDIRECT_URI,
            client_id=settings.DISCORD_CLIENT_ID,
            client_secret=settings.DISCORD_CLIENT_SECRET,
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Discord 인증 코드 교환에 실패했습니다.")

    access_token: str = token_data["access_token"]
    refresh_token: str | None = token_data.get("refresh_token")
    expires_in: int | None = token_data.get("expires_in")
    expires_at: datetime | None = (
        datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        if expires_in
        else None
    )

    try:
        user = await client.get_current_user(access_token)
    except Exception:
        raise HTTPException(status_code=400, detail="Discord 사용자 정보 조회에 실패했습니다.")

    user_id: str = user["id"]
    username: str = user.get("global_name") or user.get("username", user_id)

    async with db.begin():
        integration = await get_or_create_integration(
            db=db,
            provider="discord",
            account_identifier=user_id,
            account_name=username,
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
        "account_name": username,
    }
