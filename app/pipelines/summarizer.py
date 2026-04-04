from __future__ import annotations

from app.models.notification import Notification


async def generate_briefing(notifications: list[Notification]) -> str:
    """알림 목록을 받아 브리핑 텍스트를 생성.

    TODO: AI 개발자가 이 함수 내부를 Gemini/LangGraph 파이프라인으로 교체.
    현재는 알림을 단순 텍스트로 조합해 반환.
    """
    if not notifications:
        return "집중 세션 중 수신된 알림이 없습니다."

    lines = []
    for n in notifications:
        priority = f"[{n.priority.upper()}]" if n.priority else "[미분류]"
        sender = n.sender_name or "Unknown"
        channel = f"#{n.channel_name}" if n.channel_name else "DM"
        text = n.original_text or "(첨부파일)"
        lines.append(f"{priority} {sender} / {channel}: {text}")

    return "\n".join(lines)
