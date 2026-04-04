from __future__ import annotations

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.briefing import Briefing
from app.models.briefing_notification import BriefingNotification
from app.models.focus_session import FocusSession
from app.models.notification import Notification


async def get_focus_session(db: AsyncSession, session_id: int) -> FocusSession | None:
    result = await db.execute(
        select(FocusSession).where(FocusSession.id == session_id)
    )
    return result.scalar_one_or_none()


async def get_notifications_for_session(
    db: AsyncSession,
    session: FocusSession,
) -> list[Notification]:
    """세션 시작~종료 사이에 발생한 알림 조회. 종료 전이면 현재까지."""
    from datetime import datetime, timezone
    ended_at = session.ended_at or datetime.now(timezone.utc)

    result = await db.execute(
        select(Notification).where(
            Notification.occurred_at >= session.started_at,
            Notification.occurred_at <= ended_at,
        ).order_by(Notification.occurred_at.asc())
    )
    return list(result.scalars().all())


async def save_briefing(
    db: AsyncSession,
    session_id: int,
    content: str,
    notification_ids: list[int],
) -> Briefing:
    briefing = Briefing(session_id=session_id, content=content)
    db.add(briefing)
    await db.flush()

    for nid in notification_ids:
        db.add(BriefingNotification(briefing_id=briefing.id, notification_id=nid))

    await db.flush()
    return briefing


async def get_latest_briefing(db: AsyncSession) -> Briefing | None:
    result = await db.execute(
        select(Briefing)
        .options(selectinload(Briefing.notifications))
        .order_by(desc(Briefing.generated_at))
        .limit(1)
    )
    return result.scalar_one_or_none()
