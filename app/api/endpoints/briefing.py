from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.pipelines.summarizer import generate_briefing
from app.repositories.briefing_repository import (
    create_focus_session,
    end_focus_session,
    get_active_session,
    get_briefing_by_id,
    get_focus_session,
    get_latest_briefing,
    get_notifications_for_session,
    save_briefing,
)

router = APIRouter(tags=["briefing"])


def _serialize_notification(n) -> dict:
    return {
        "id": n.id,
        "title": n.title,
        "sender_name": n.sender_name,
        "channel_name": n.channel_name,
        "source_type": n.source_type,
        "priority": n.priority,
        "original_text": n.original_text,
        "occurred_at": n.occurred_at,
        "source_url": n.source_url,
        "is_direct_target": n.is_direct_target,
    }


# ── Focus Session ─────────────────────────────────────────────────────────────

class CreateFocusSessionRequest(BaseModel):
    user_id: int
    planned_duration_minutes: int = Field(gt=0, description="계획된 집중 시간 (분)")


@router.post("/focus-sessions", status_code=201)
async def start_focus_session(
    body: CreateFocusSessionRequest,
    db: AsyncSession = Depends(get_db),
):
    """집중 세션 시작.

    이미 진행 중인 세션이 있으면 409 반환.
    """
    async with db.begin():
        existing = await get_active_session(db, body.user_id)
        if existing:
            return {
                "session_id": existing.id,
                "user_id": existing.user_id,
                "planned_duration_minutes": existing.planned_duration_minutes,
                "started_at": existing.started_at,
                "status": existing.status,
            }

        session = await create_focus_session(
            db=db,
            user_id=body.user_id,
            planned_duration_minutes=body.planned_duration_minutes,
        )

    return {
        "session_id": session.id,
        "user_id": session.user_id,
        "planned_duration_minutes": session.planned_duration_minutes,
        "started_at": session.started_at,
        "status": session.status,
    }


@router.patch("/focus-sessions/{session_id}")
async def finish_focus_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    """집중 세션 종료."""
    async with db.begin():
        session = await get_focus_session(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        if session.status != "active":
            raise HTTPException(status_code=400, detail="이미 종료된 세션입니다.")

        session = await end_focus_session(db, session)

    return {
        "session_id": session.id,
        "started_at": session.started_at,
        "ended_at": session.ended_at,
        "status": session.status,
    }


# ── Briefing ──────────────────────────────────────────────────────────────────

class CreateBriefingRequest(BaseModel):
    session_id: int


@router.post("/briefings", status_code=201)
async def create_briefing(
    body: CreateBriefingRequest,
    db: AsyncSession = Depends(get_db),
):
    """집중 세션의 알림을 요약해 브리핑 생성.

    세션이 아직 진행 중이면 자동으로 종료 후 브리핑 생성.
    """
    async with db.begin():
        session = await get_focus_session(db, body.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

        # 아직 진행 중이면 자동 종료
        if session.status == "active":
            session = await end_focus_session(db, session)

        notifications = await get_notifications_for_session(db, session)
        content = await generate_briefing(notifications)

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
        "notifications": [_serialize_notification(n) for n in notifications],
    }


@router.get("/briefings/latest")
async def get_latest_briefing_endpoint(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    """유저의 가장 최근 브리핑 조회."""
    briefing = await get_latest_briefing(db, user_id)
    if not briefing:
        raise HTTPException(status_code=404, detail="브리핑이 없습니다.")

    return {
        "briefing_id": briefing.id,
        "session_id": briefing.session_id,
        "content": briefing.content,
        "generated_at": briefing.generated_at,
        "notification_count": len(briefing.notifications),
        "notifications": [_serialize_notification(n) for n in briefing.notifications],
    }


@router.get("/briefings/{briefing_id}")
async def get_briefing(
    briefing_id: int,
    db: AsyncSession = Depends(get_db),
):
    """특정 브리핑 조회."""
    briefing = await get_briefing_by_id(db, briefing_id)
    if not briefing:
        raise HTTPException(status_code=404, detail="브리핑을 찾을 수 없습니다.")

    return {
        "briefing_id": briefing.id,
        "session_id": briefing.session_id,
        "content": briefing.content,
        "generated_at": briefing.generated_at,
        "notification_count": len(briefing.notifications),
        "notifications": [_serialize_notification(n) for n in briefing.notifications],
    }
