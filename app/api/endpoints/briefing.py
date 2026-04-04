from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.pipelines.summarizer import generate_briefing
from app.repositories.briefing_repository import (
    get_focus_session,
    get_latest_briefing,
    get_notifications_for_session,
    save_briefing,
)

router = APIRouter(tags=["briefing"])


class CreateBriefingRequest(BaseModel):
    session_id: int


@router.post("/briefings", status_code=201)
async def create_briefing(
    body: CreateBriefingRequest,
    db: AsyncSession = Depends(get_db),
):
    """집중 세션의 알림을 AI로 요약해 브리핑 생성."""
    session = await get_focus_session(db, body.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Focus session을 찾을 수 없습니다.")

    notifications = await get_notifications_for_session(db, session)
    content = await generate_briefing(notifications)

    async with db.begin():
        briefing = await save_briefing(
            db=db,
            session_id=session.id,
            content=content,
            notification_ids=[n.id for n in notifications],
        )

    return {
        "briefing_id": briefing.id,
        "session_id": briefing.session_id,
        "content": briefing.content,
        "generated_at": briefing.generated_at,
        "notification_count": len(notifications),
    }


@router.get("/briefings/latest")
async def get_latest_briefing_endpoint(
    db: AsyncSession = Depends(get_db),
):
    """가장 최근 브리핑 조회."""
    briefing = await get_latest_briefing(db)
    if not briefing:
        raise HTTPException(status_code=404, detail="브리핑이 없습니다.")

    return {
        "briefing_id": briefing.id,
        "session_id": briefing.session_id,
        "content": briefing.content,
        "generated_at": briefing.generated_at,
        "notifications": [
            {
                "id": n.id,
                "title": n.title,
                "sender_name": n.sender_name,
                "channel_name": n.channel_name,
                "source_type": n.source_type,
                "priority": n.priority,
                "original_text": n.original_text,
                "occurred_at": n.occurred_at,
                "source_url": n.source_url,
            }
            for n in briefing.notifications
        ],
    }
