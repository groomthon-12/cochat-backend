from __future__ import annotations

import httpx

DISCORD_API_BASE = "https://discord.com/api/v10"


class DiscordRestClient:
    def __init__(self, bot_token: str | None = None) -> None:
        self._bot_token = bot_token

    # -------------------------------------------------------------------
    # OAuth2
    # -------------------------------------------------------------------

    async def exchange_code(self, code: str, redirect_uri: str, client_id: str, client_secret: str) -> dict:
        """Authorization Code를 Access Token으로 교환."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{DISCORD_API_BASE}/oauth2/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                auth=(client_id, client_secret),
            )
            response.raise_for_status()
            return response.json()

    async def get_current_user(self, access_token: str) -> dict:
        """Access Token으로 현재 사용자 정보 조회."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{DISCORD_API_BASE}/users/@me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()

    async def get_user_guilds(self, access_token: str) -> list[dict]:
        """사용자가 속한 서버 목록 조회."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{DISCORD_API_BASE}/users/@me/guilds",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()

    # -------------------------------------------------------------------
    # Bot Token
    # -------------------------------------------------------------------

    async def get_guild(self, guild_id: str) -> dict:
        """Bot Token으로 서버 정보 조회."""
        if not self._bot_token:
            raise ValueError("bot_token이 설정되지 않았습니다.")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{DISCORD_API_BASE}/guilds/{guild_id}",
                headers={"Authorization": f"Bot {self._bot_token}"},
            )
            response.raise_for_status()
            return response.json()
