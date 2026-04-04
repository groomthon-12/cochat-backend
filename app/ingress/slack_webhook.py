from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time

from fastapi import APIRouter, HTTPException, Request, status

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.integrations.slack.client import SlackClient
from app.integrations.slack.events import SlackEventType
from app.integrations.slack.normalizer import normalize_message
from app.repositories.integration_repository import get_integration_by_account
from app.repositories.raw_event_repository import save_raw_event

logger = logging.getLogger(__name__)
router = APIRouter(tags=["webhooks"])


async def _verify_slack_signature(request: Request) -> bytes:
    """Slack HMAC-SHA256 서명 검증.

    Slack이 보내는 X-Slack-Request-Timestamp, X-Slack-Signature 헤더를 검증한다.
    5분 이상 지난 요청은 replay attack 방지를 위해 거부한다.
    """
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")
    body = await request.body()

    if not timestamp or not signature:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Slack signature headers")

    try:
        if abs(time.time() - int(timestamp)) > 300:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request timestamp too old")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid timestamp")

    sig_basestring = f"v0:{timestamp}:{body.decode()}"
    expected = "v0=" + hmac.new(
        settings.SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Slack signature")

    return body


@router.post("/webhooks/slack")
async def slack_webhook(request: Request):
    """Slack Events API 웹훅 수신 엔드포인트.

    처리 순서:
    1. 서명 검증
    2. url_verification challenge 응답 (Slack 포털 URL 등록 시 1회)
    3. 봇 메시지 무시
    4. raw_events 저장
    5. channel_name / sender_name 조회 후 normalize
    """
    body = await _verify_slack_signature(request)

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    # Slack URL 등록 시 challenge 요청에 응답
    if payload.get("type") == "url_verification":
        return {"challenge": payload["challenge"]}

    event: dict = payload.get("event", {})

    # 봇 자신의 메시지 무시
    if event.get("bot_id") or event.get("subtype") == "bot_message":
        return {"ok": True}

    event_type_raw: str = event.get("type", "")
    if event_type_raw not in (SlackEventType.MESSAGE, SlackEventType.APP_MENTION):
        return {"ok": True}

    team_id: str | None = payload.get("team_id") or event.get("team")
    if not team_id:
        logger.warning("team_id를 찾을 수 없는 Slack 이벤트 수신, 무시합니다.")
        return {"ok": True}

    channel_id: str | None = event.get("channel")
    user_id: str | None = event.get("user")
    provider_event_id: str = event.get("ts", "")

    async with AsyncSessionLocal() as db:
        async with db.begin():
            integration = await get_integration_by_account(
                db=db,
                provider="slack",
                account_identifier=team_id,
            )
            if not integration:
                logger.warning(
                    "team_id=%s에 대한 IntegrationAccount가 없습니다. OAuth 연동을 먼저 완료하세요.",
                    team_id,
                )
                return {"ok": True}

            raw_event = await save_raw_event(
                db=db,
                integration_id=integration.id,
                provider="slack",
                provider_event_id=provider_event_id,
                event_type=event_type_raw,
                payload=event,
            )

    # channel_name / sender_name은 Slack API 조회 필요 (트랜잭션 밖에서 수행)
    channel_name: str | None = None
    sender_name: str | None = None

    if settings.SLACK_BOT_TOKEN:
        client = SlackClient(bot_token=settings.SLACK_BOT_TOKEN)
        if channel_id:
            channel_name = await client.get_channel_name(channel_id)
        if user_id:
            sender_name = await client.get_sender_name(user_id)

    notification_event = normalize_message(
        payload=event,
        integration_id=integration.id,
        raw_event_id=raw_event.id,
        channel_name=channel_name,
        sender_name=sender_name,
        event_type=event_type_raw,
    )

    logger.info(
        "NotificationEvent 생성: provider=%s integration_id=%s raw_event_id=%s source_type=%s",
        notification_event.provider,
        notification_event.integration_id,
        notification_event.raw_event_id,
        notification_event.source_type,
    )

    # TODO: AI 파이프라인 연결 시 활성화
    # await process_notification(notification_event)

    return {"ok": True}
