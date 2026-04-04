from __future__ import annotations

import logging

from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)


class SlackClient:
    def __init__(self, bot_token: str) -> None:
        self._client = AsyncWebClient(token=bot_token)

    async def get_channel_name(self, channel_id: str) -> str | None:
        """conversations.info로 채널 이름 조회. 실패 시 None 반환."""
        try:
            res = await self._client.conversations_info(channel=channel_id)
            return res["channel"].get("name")
        except SlackApiError as e:
            logger.warning("채널 이름 조회 실패 channel_id=%s: %s", channel_id, e.response["error"])
            return None

    async def get_sender_name(self, user_id: str) -> str | None:
        """users.info로 표시 이름 조회. 실패 시 None 반환."""
        try:
            res = await self._client.users_info(user=user_id)
            user = res["user"]
            # display_name 우선, 없으면 real_name
            return user["profile"].get("display_name") or user["profile"].get("real_name")
        except SlackApiError as e:
            logger.warning("유저 이름 조회 실패 user_id=%s: %s", user_id, e.response["error"])
            return None

    async def exchange_code(self, code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
        """OAuth code → Bot Token 교환."""
        res = await self._client.oauth_v2_access(
            client_id=client_id,
            client_secret=client_secret,
            code=code,
            redirect_uri=redirect_uri,
        )
        return res.data
