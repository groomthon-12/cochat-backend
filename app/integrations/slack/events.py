from __future__ import annotations

import re
from enum import Enum


class SlackEventType(str, Enum):
    MESSAGE = "message"
    APP_MENTION = "app_mention"


_MENTION_RE = re.compile(r"<@([A-Z0-9]+)>")


def _resolve_channel_type(event: dict) -> str | None:
    channel_type = event.get("channel_type")
    if channel_type:
        return channel_type

    channel_id = event.get("channel", "")
    if channel_id.startswith("D"):
        return "im"
    if channel_id.startswith("G"):
        return "group"
    if channel_id.startswith("C"):
        return "channel"
    return None


def _extract_mentions(text: str) -> list[str]:
    return _MENTION_RE.findall(text or "")


def to_normalizer_payload(payload: dict) -> dict:
    """Slack Events API envelope을 Slack normalizer 입력 형식으로 변환."""
    event = payload.get("event") or {}
    authorizations = payload.get("authorizations") or []
    authorization = authorizations[0] if authorizations else {}

    text = event.get("text") or ""

    return {
        "workspace_id": payload.get("team_id") or payload.get("context_team_id") or event.get("team"),
        "event_id": payload.get("event_id") or event.get("event_ts") or event.get("ts"),
        "event_time": payload.get("event_time"),
        "channel_id": event.get("channel"),
        "channel_type": _resolve_channel_type(event),
        "sender_user_id": event.get("user"),
        "authorized_user_id": authorization.get("user_id"),
        "authorized_is_bot": bool(authorization.get("is_bot")),
        "message_id": event.get("ts"),
        "thread_ts": event.get("thread_ts"),
        "text": text,
        "mentions": _extract_mentions(text),
        "has_files": bool(event.get("files")),
        "has_attachments": bool(event.get("attachments")),
    }
