from __future__ import annotations

import logging

from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

logger = logging.getLogger(__name__)


class SlackClient:
    def __init__(self, token: str) -> None:
        self._client = AsyncWebClient(token=token)

    async def get_channel_name(self, channel_id: str) -> str | None:
        """Resolve a human-readable Slack conversation name from a channel id."""
        try:
            res = await self._client.conversations_info(channel=channel_id)
            channel = res["channel"]

            name = channel.get("name") or channel.get("name_normalized")
            if name:
                return name

            if channel.get("is_im") and channel.get("user"):
                return await self.get_sender_name(channel["user"])

            if channel.get("is_mpim"):
                purpose = (channel.get("purpose") or {}).get("value")
                if purpose:
                    return purpose

            return None
        except SlackApiError as e:
            logger.warning("Slack channel name lookup failed channel_id=%s: %s", channel_id, e.response["error"])
            return None

    async def get_sender_name(self, user_id: str) -> str | None:
        """Resolve a human-readable Slack user name from a user id."""
        try:
            res = await self._client.users_info(user=user_id)
            user = res["user"]
            profile = user.get("profile", {})
            return profile.get("display_name") or profile.get("real_name") or user.get("real_name")
        except SlackApiError as e:
            logger.warning("Slack user name lookup failed user_id=%s: %s", user_id, e.response["error"])
            return None

    async def exchange_code(
        self,
        code: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ) -> dict:
        """Exchange a Slack OAuth code for an access token."""
        res = await self._client.oauth_v2_access(
            client_id=client_id,
            client_secret=client_secret,
            code=code,
            redirect_uri=redirect_uri,
        )
        return res.data
