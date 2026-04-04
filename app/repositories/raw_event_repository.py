from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.raw_event import RawEvent


async def save_raw_event(
    db: AsyncSession,
    integration_id: int,
    provider: str,
    provider_event_id: str,
    event_type: str,
    payload: dict,
) -> RawEvent:
    """원본 이벤트를 DB에 저장."""
    raw_event = RawEvent(
        provider=provider,
        integration_id=integration_id,
        provider_event_id=provider_event_id,
        event_type=event_type,
        payload=payload,
    )
    db.add(raw_event)
    await db.flush()  # id 확보
    return raw_event
