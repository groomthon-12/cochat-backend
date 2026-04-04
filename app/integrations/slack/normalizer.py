from __future__ import annotations

import re
from datetime import datetime, timezone

from app.integrations.normalizer import NotificationEvent, SourceType


_MENTION_RE = re.compile(r"<[^>]+>")


def _clean_text(text: str) -> str:
    return _MENTION_RE.sub("", text).strip()


def _resolve_source_type(
    channel_type: str | None,
    is_thread: bool,
    has_mentions: bool,
) -> SourceType:
    if channel_type in ("im", "mpim"):
        return "dm"
    if is_thread:
        return "thread_reply"
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
    if source_type == "thread_reply":
        ch = f"#{channel_name}" if channel_name else "스레드"
        return f"{display} replied in {ch}"
    ch = f"#{channel_name}" if channel_name else "채널"
    return f"{display} in {ch}"


def normalize_message(
    payload: dict,
    integration_id: int,
    raw_event_id: int,
    sender_name: str | None = None,
    channel_name: str | None = None,
) -> NotificationEvent:
    """전처리된 Slack payload → NotificationEvent.

    payload 구조:
    {
        "workspace_id": str,
        "event_id": str,
        "event_time": int,           # unix timestamp
        "channel_id": str,
        "channel_type": str,         # "channel" | "im" | "mpim" | "group"
        "sender_user_id": str,
        "authorized_user_id": str,
        "authorized_is_bot": bool,
        "message_id": str,           # ts (고유 ID)
        "thread_ts": str | None,     # None이면 일반 메시지, 값 있으면 스레드 답글
        "text": str,
        "mentions": list[str],       # user id 목록
        "has_files": bool,
        "has_attachments": bool,
    }

    sender_name: users.info로 조회한 표시 이름 (없으면 sender_user_id로 fallback)
    channel_name: conversations.info로 조회한 채널 이름 (없으면 channel_id로 fallback)
    """
    sender_id: str | None = payload.get("sender_user_id")
    message_id: str = payload.get("message_id", "")
    thread_ts: str | None = payload.get("thread_ts")
    channel_type: str | None = payload.get("channel_type")
    event_time: int | None = payload.get("event_time")

    is_thread = bool(thread_ts)
    is_dm = channel_type in ("im", "mpim")
    mentions: list = payload.get("mentions", [])
    has_mentions = len(mentions) > 0
    has_attachments = payload.get("has_files", False) or payload.get("has_attachments", False)

    raw_text: str = payload.get("text") or ""
    original_text = _clean_text(raw_text) if raw_text else ("[첨부파일]" if has_attachments else "")

    display_sender = sender_name or sender_id or "Unknown"
    display_channel = channel_name

    workspace_id = payload.get("workspace_id")
    channel_id = payload.get("channel_id")

    source_type = _resolve_source_type(channel_type, is_thread, has_mentions)
    title = _build_title(source_type, display_sender, display_channel)

    occurred_at = (
        datetime.fromtimestamp(event_time, tz=timezone.utc)
        if event_time
        else datetime.now(timezone.utc)
    )

    return NotificationEvent(
        provider="slack",
        integration_id=integration_id,
        raw_event_id=raw_event_id,
        original_text=original_text,
        payload=payload,
        source_type=source_type,
        provider_object_id=message_id,
        title=title,
        sender_name=sender_name,
        sender_id=sender_id,
        workspace_id=workspace_id,
        channel_id=channel_id,
        channel_name=channel_name,
        source_url=None,
        is_direct_target=is_dm or has_mentions,
        is_broadcast=False,
        has_attachments=has_attachments,
        occurred_at=occurred_at,
    )
