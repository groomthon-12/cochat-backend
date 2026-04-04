from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


ProviderType = Literal["slack", "discord"]

SourceType = Literal["dm", "mention", "channel_message", "thread_reply"]


class NotificationEvent(BaseModel):
    """플랫폼 원본 이벤트를 정규화한 모델.

    normalizer가 채우는 필드와 AI 파이프라인이 채우는 필드가 명확히 구분된다.

    [normalizer 담당]
    - provider, integration_id, raw_event_id
    - source_type, provider_object_id, title
    - original_text (AI 입력용 핵심 텍스트)
    - sender_name, sender_id, channel_name, source_url
    - is_direct_target, is_broadcast, has_attachments
    - occurred_at, received_at
    - payload (원본 보존)

    [AI 파이프라인 담당 — pipeline이 채운 뒤 Notification 저장]
    - priority, priority_score, summary, reason, content_preview
    """

    # ── 메타 ──────────────────────────────────────────────────────────────
    provider: ProviderType = Field(
        description="원본 플랫폼 (slack | discord)",
    )
    integration_id: int = Field(
        description="integration_accounts.id FK",
    )
    raw_event_id: int = Field(
        description="raw_events.id FK",
    )

    # ── AI 파이프라인 입력 ─────────────────────────────────────────────────
    original_text: str = Field(
        description=(
            "AI가 읽는 핵심 텍스트. "
            "플랫폼 마크업(@멘션, 채널링크 등)을 제거한 순수 문자열. "
            "비어있으면 '[첨부파일]' 등 fallback 문자열로 채운다."
        ),
    )
    rich_contents: str | None = Field(
        default=None,
        description=(
            "내부 컴포넌트(Slack Blocks, Discord Embeds 등)의 모든 텍스트를 평탄화한 마크다운 풍부한 텍스트. "
            "LLM RAG 파이프라인과 Redis History에서 주력 문맥으로 활용됩니다."
        ),
    )
    payload: dict[str, Any] = Field(
        description="플랫폼 원본 JSON — raw_events.payload와 동일. AI가 추가 컨텍스트 필요 시 참조.",
    )

    # ── notifications 테이블 직접 매핑 ────────────────────────────────────
    source_type: SourceType = Field(
        description="알림 유형: dm | mention | channel_message | thread_reply",
    )
    provider_object_id: str = Field(
        description="플랫폼 내 메시지 고유 ID. Discord: message.id, Slack: ts",
    )
    title: str = Field(
        description=(
            "알림 제목 (자동 생성). "
            "예) 'DM from 홍길동', '홍길동 mentioned you in #general'"
        ),
    )
    sender_name: str | None = Field(
        default=None,
        description="발신자 표시 이름. 알 수 없으면 None",
    )
    sender_id: str | None = Field(
        default=None,
        description=(
            "플랫폼 발신자 ID. 이름이 바뀌어도 식별 가능하도록 보존. "
            "Discord: user.id, Slack: user field"
        ),
    )
    workspace_id: str | None = Field(
        default=None,
        description="워크스페이스/서버 고유 ID. Slack은 team, Discord는 guild_id",
    )
    channel_id: str | None = Field(
        default=None,
        description="채널 고유 ID. 단기 기억 저장소(Redis)의 주요 Key 속성으로 사용됨",
    )
    channel_name: str | None = Field(
        default=None,
        description="채널명. DM이면 None. Slack은 channel ID만 있으므로 별도 조회 후 채움",
    )
    source_url: str | None = Field(
        default=None,
        description="원본 메시지 링크. Discord: /channels/{guild}/{channel}/{msg}. Slack: 구성 불가 시 None",
    )
    is_direct_target: bool = Field(
        default=False,
        description="나를 직접 겨냥한 메시지 여부. DM이거나 @멘션이면 True. 우선순위 가중치에 영향.",
    )
    is_broadcast: bool = Field(
        default=False,
        description="@everyone/@here 등 전체 공지 여부",
    )
    has_attachments: bool = Field(
        default=False,
        description="첨부파일 또는 Embed/Block 포함 여부",
    )
    occurred_at: datetime = Field(
        description="메시지가 실제 발생한 시각 (UTC). Discord: message.timestamp, Slack: ts 변환",
    )
    received_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="서버가 이벤트를 수신한 시각 (UTC)",
    )
