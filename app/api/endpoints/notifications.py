from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.notification import Notification

router = APIRouter(tags=["notifications"])


@router.post("/webhooks/slack", status_code=200)
def slack_webhook(payload: dict = {}):
    """Slack 웹훅 수신"""
    return {"status": "received"}


@router.get("/notifications")
async def list_notifications(db: AsyncSession = Depends(get_db)):
    """알림 목록 조회"""
    result = await db.execute(
        select(Notification)
        .options(selectinload(Notification.integration))
        .order_by(Notification.created_at.desc())
        .limit(100)
    )
    notifications = result.scalars().all()

    priority_map = {
        "Emergency": "critical",
        "High": "high",
        "Normal": "medium",
        "Low": "low",
    }

    return {
        "notifications": [
            {
                "id": str(n.id),
                "integrationId": str(n.integration_id),
                "rawEventId": str(n.raw_event_id) if n.raw_event_id else None,
                "priority": priority_map.get(n.priority, "low"),
                "summary": n.summary or n.content_preview or n.title,
                "actor": n.sender_name,
                "channel": n.channel_name or n.channel_id or "general",
                "channelId": n.channel_id or "",
                "workspaceId": n.integration.account_identifier if n.integration else "",
                "provider": n.integration.provider if n.integration else "discord",
                "status": n.status or "unread",
                "createdAt": n.created_at.isoformat() if n.created_at else "",
            }
            for n in notifications
        ]
    }


@router.patch("/notifications/{notificationId}")
async def update_notification(
    notificationId: str,
    db: AsyncSession = Depends(get_db),
):
    """알림 상태 업데이트 (읽음 처리 등)"""
    result = await db.execute(
        select(Notification).where(Notification.id == int(notificationId))
    )
    notification = result.scalar_one_or_none()
    if notification:
        notification.status = "read"
        await db.commit()
    return {"notificationId": notificationId, "status": "updated"}
