from __future__ import annotations

import re
from datetime import datetime, timezone

from app.integrations.normalizer import NotificationEvent, SourceType


_MENTION_RE = re.compile(r"<[@#&!][^>]+>")


def _clean_text(text: str) -> str:
    return _MENTION_RE.sub("", text).strip()


def _resolve_source_type(
    is_dm: bool,
    has_mentions: bool,
) -> SourceType:
    if is_dm:
        return "dm"
    if has_mentions:
        return "mention"
    return "channel_message"


def _build_title(
    source_type: SourceType,
    sender_name: str | None,
    channel_name: str | None,
) -> str:
    display = sender_name or "Unknown"
    if source_type == "dm":
        return f"DM from {display}"
    if source_type == "mention":
        ch = f"#{channel_name}" if channel_name else "채널"
        return f"{display} mentioned you in {ch}"
    ch = f"#{channel_name}" if channel_name else "채널"
    return f"{display} in {ch}"


def normalize_message(
    payload: dict,
    integration_id: int,
    raw_event_id: int,
) -> NotificationEvent:
    """전처리된 Discord payload → NotificationEvent.

    payload 구조:
    {
        "message_id": str,
        "content": str,
        "timestamp": str,              # ISO8601
        "author": {
            "user_id": str,
            "username": str,
            "global_name": str | None,
        },
        "location": {
            "guild_id": str | None,    # None이면 DM
            "channel_id": str,
            "channel_name": str | None,
        },
        "metadata": {
            "attachments": list,
            "mentions": list[str],     # user id 목록
            "mention_everyone": bool,
        }
    }
    """
    author: dict = payload.get("author") or {}
    location: dict = payload.get("location") or {}
    metadata: dict = payload.get("metadata") or {}

    sender_id: str | None = author.get("user_id")
    sender_name: str | None = author.get("global_name") or author.get("username")

    guild_id: str | None = location.get("guild_id")
    channel_name: str | None = location.get("channel_name")
    channel_id: str | None = location.get("channel_id")
    message_id: str = payload.get("message_id", "")

    is_dm = guild_id is None
    mentions: list = metadata.get("mentions", [])
    has_mentions = len(mentions) > 0
    mention_everyone: bool = metadata.get("mention_everyone", False)

    attachments: list = metadata.get("attachments", [])
    has_attachments = len(attachments) > 0

    raw_text: str = payload.get("content") or ""
    original_text = _clean_text(raw_text) if raw_text else ("[첨부파일]" if has_attachments else "")

    source_type = _resolve_source_type(is_dm, has_mentions)
    title = _build_title(source_type, sender_name, channel_name)

    source_url = (
        f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"
        if guild_id and channel_id and message_id
        else None
    )

    raw_ts: str | None = payload.get("timestamp")
    occurred_at = (
        datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
        if raw_ts
        else datetime.now(timezone.utc)
    )

    return NotificationEvent(
        provider="discord",
        integration_id=integration_id,
        raw_event_id=raw_event_id,
        original_text=original_text,
        payload=payload,
        source_type=source_type,
        provider_object_id=message_id,
        title=title,
        sender_name=sender_name,
        sender_id=sender_id,
        channel_name=channel_name,
        source_url=source_url,
        is_direct_target=is_dm or has_mentions,
        is_broadcast=mention_everyone,
        has_attachments=has_attachments,
        occurred_at=occurred_at,
    )
