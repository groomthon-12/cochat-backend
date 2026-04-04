from __future__ import annotations

from sqlalchemy import select
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
    """원본 이벤트를 저장하되, 동일 provider_event_id는 재사용한다."""
    existing = await db.execute(
        select(RawEvent).where(
            RawEvent.provider == provider,
            RawEvent.integration_id == integration_id,
            RawEvent.provider_event_id == provider_event_id,
        )
    )
    raw_event = existing.scalar_one_or_none()
    if raw_event is not None:
        return raw_event

    raw_event = RawEvent(
        provider=provider,
        integration_id=integration_id,
        provider_event_id=provider_event_id,
        event_type=event_type,
        payload=payload,
    )
    db.add(raw_event)
    await db.flush()
    return raw_event
