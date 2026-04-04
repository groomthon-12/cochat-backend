from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.slack.client import SlackClient
from app.repositories.raw_event_repository import save_raw_event


def _resolve_conversation_type(conversation: dict) -> str:
    if conversation.get("is_im"):
        return "im"
    if conversation.get("is_mpim"):
        return "mpim"
    if conversation.get("is_private"):
        return "private_channel"
    return "channel"


async def list_accessible_conversations(
    access_token: str,
    limit: int = 100,
) -> list[dict]:
    client = SlackClient(token=access_token)
    conversations = await client.list_conversations(limit=limit)

    results: list[dict] = []
    for conversation in conversations:
        channel_id = conversation.get("id")
        if not channel_id:
            continue

        display_name = await client.get_channel_name(channel_id)
        results.append({
            "channel_id": channel_id,
            "channel_type": _resolve_conversation_type(conversation),
            "is_im": bool(conversation.get("is_im")),
            "is_mpim": bool(conversation.get("is_mpim")),
            "is_private": bool(conversation.get("is_private")),
            "display_name": display_name,
            "name": conversation.get("name") or conversation.get("name_normalized"),
        })

    return results


async def sync_conversation_raw_events(
    db: AsyncSession,
    integration_id: int,
    access_token: str,
    channel_id: str,
    limit: int = 30,
) -> dict:
    client = SlackClient(token=access_token)
    messages = await client.get_conversation_history(channel_id=channel_id, limit=limit)

    raw_event_ids: list[int] = []
    provider_event_ids: list[str] = []

    for message in reversed(messages):
        ts = message.get("ts")
        if not ts:
            continue

        raw_event = await save_raw_event(
            db=db,
            integration_id=integration_id,
            provider="slack",
            provider_event_id=f"{channel_id}:{ts}",
            event_type=message.get("type", "message"),
            payload={
                **message,
                "channel": channel_id,
            },
        )
        raw_event_ids.append(raw_event.id)
        provider_event_ids.append(raw_event.provider_event_id)

    return {
        "channel_id": channel_id,
        "processed_messages": len(raw_event_ids),
        "raw_event_ids": raw_event_ids,
        "provider_event_ids": provider_event_ids,
    }


async def sync_accessible_conversations(
    db: AsyncSession,
    integration_id: int,
    access_token: str,
    conversation_limit: int = 100,
    message_limit: int = 30,
) -> dict:
    """Sync recent messages from all accessible conversations for one Slack integration."""
    conversations = await list_accessible_conversations(
        access_token=access_token,
        limit=conversation_limit,
    )

    synced_conversations: list[dict] = []
    total_messages = 0

    for conversation in conversations:
        result = await sync_conversation_raw_events(
            db=db,
            integration_id=integration_id,
            access_token=access_token,
            channel_id=conversation["channel_id"],
            limit=message_limit,
        )
        total_messages += result["processed_messages"]
        synced_conversations.append({
            "channel_id": conversation["channel_id"],
            "display_name": conversation["display_name"],
            "channel_type": conversation["channel_type"],
            "processed_messages": result["processed_messages"],
            "raw_event_ids": result["raw_event_ids"],
        })

    return {
        "integration_id": integration_id,
        "conversation_count": len(conversations),
        "processed_messages": total_messages,
        "conversations": synced_conversations,
    }
