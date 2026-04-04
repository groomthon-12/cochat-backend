from __future__ import annotations

from app.integrations.normalizer import NotificationEvent


def normalize_message(
    payload: dict,
    integration_id: int,
    raw_event_id: int,
) -> NotificationEvent:
    """Discord MESSAGE_CREATE payload를 NotificationEvent로 변환."""

    author = payload.get("author") or {}
    sender_name: str | None = author.get("global_name") or author.get("username")

    guild_id: str | None = payload.get("guild_id")
    is_dm = guild_id is None
    channel_name: str | None = None if is_dm else payload.get("channel_name")

    mentions: list = payload.get("mentions", [])
    mention_everyone: bool = payload.get("mention_everyone", False)
    is_direct_target = is_dm or len(mentions) > 0

    attachments: list = payload.get("attachments", [])
    embeds: list = payload.get("embeds", [])
    has_attachments = len(attachments) > 0 or len(embeds) > 0

    return NotificationEvent(
        provider="discord",
        integration_id=integration_id,
        raw_event_id=raw_event_id,
        payload=payload,
        sender_name=sender_name,
        channel_name=channel_name,
        is_broadcast=mention_everyone,
        has_attachments=has_attachments,
    )
