from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


ProviderType = Literal["slack", "jira", "discord", "gmail"]


class NotificationEvent(BaseModel):
    """다양한 플랫폼에서 들어온 원본 웹훅 이벤트를 정규화한 모델.

    AI 파이프라인의 입력값으로 사용된다.
    """

    provider: ProviderType = Field(
        description="원본 플랫폼 이름 (slack | jira | discord | gmail)",
    )
    integration_id: int = Field(
        description="연동 계정을 식별하는 ID",
    )
    raw_event_id: int = Field(
        description="원본 웹훅 이벤트 레코드를 참조하는 ID",
    )
    payload: dict[str, Any] = Field(
        description="플랫폼에서 수신한 원본 JSON 데이터",
    )
    sender_name: str | None = Field(
        default=None,
        description="알림 발신자 이름. 알 수 없는 경우 None",
    )
    channel_name: str | None = Field(
        default=None,
        description="알림이 발생한 채널명. DM인 경우 None",
    )
    is_broadcast: bool = Field(
        default=False,
        description="@everyone, @here 등 전체 공지성 메시지 여부",
    )
    has_attachments: bool = Field(
        default=False,
        description="첨부파일 또는 Embed 포함 여부",
    )
    received_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="이벤트 수신 시간 (UTC)",
    )
