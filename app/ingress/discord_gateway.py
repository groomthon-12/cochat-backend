from __future__ import annotations

import asyncio
import logging

import discord

from app.core.config import settings

logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True  # Privileged Intent — Developer Portal에서 활성화 필수
intents.guilds = True
intents.dm_messages = True

# lifespan에서 참조하기 위한 전역 bot 인스턴스
_bot: CoChatDiscordBot | None = None


class CoChatDiscordBot(discord.Client):
    async def on_ready(self) -> None:
        logger.info("Discord 봇 연결 성공: %s (id: %s)", self.user, self.user.id)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        payload = {
            "id": str(message.id),
            "content": message.content,
            "author": {
                "id": str(message.author.id),
                "username": message.author.name,
                "global_name": getattr(message.author, "global_name", None),
            },
            "channel_id": str(message.channel.id),
            "channel_name": getattr(message.channel, "name", None),
            "guild_id": str(message.guild.id) if message.guild else None,
            "timestamp": message.created_at.isoformat(),
            "attachments": [str(a.url) for a in message.attachments],
            "mentions": [str(u.id) for u in message.mentions],
            "mention_everyone": message.mention_everyone,
        }

        logger.debug("Discord 메시지 수신: %s", payload)

        # TODO: DB 연결 후 아래 코드 활성화
        # raw_event = await save_raw_event(db_session, payload, integration_id)
        # event = normalize_message(payload, integration_id=integration_id, raw_event_id=raw_event.id)
        # await enqueue_notification(event)


async def start_gateway() -> asyncio.Task:
    """FastAPI lifespan에서 호출. 봇을 백그라운드 태스크로 시작하고 Task를 반환."""
    global _bot
    token = settings.DISCORD_BOT_TOKEN
    if not token:
        logger.warning("DISCORD_BOT_TOKEN이 설정되지 않아 Discord 봇을 시작하지 않습니다.")
        return None

    _bot = CoChatDiscordBot(intents=intents)
    task = asyncio.create_task(_bot.start(token), name="discord_gateway")
    logger.info("Discord 게이트웨이 백그라운드 태스크 시작")
    return task


async def stop_gateway(task: asyncio.Task | None) -> None:
    """FastAPI lifespan 종료 시 호출. 봇 연결을 닫고 태스크를 정리."""
    global _bot
    if _bot and not _bot.is_closed():
        await _bot.close()
        logger.info("Discord 봇 연결 종료")

    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


async def run_discord_gateway() -> None:
    """Discord Bot을 단독 실행하는 함수 (로컬 테스트용)."""
    token = settings.DISCORD_BOT_TOKEN
    if not token:
        raise ValueError(
            "DISCORD_BOT_TOKEN이 설정되지 않았습니다. .env 파일을 확인하세요."
        )
    bot = CoChatDiscordBot(intents=intents)
    await bot.start(token)
