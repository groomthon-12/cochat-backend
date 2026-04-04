from __future__ import annotations

import discord

from app.core.config import settings

intents = discord.Intents.default()
intents.message_content = True  # Privileged Intent — Developer Portal에서 활성화 필수
intents.guilds = True
intents.dm_messages = True


class CoChatDiscordBot(discord.Client):
    async def on_ready(self) -> None:
        print(f"✅ 연결 성공: {self.user} (id: {self.user.id})")

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

        print(payload)

        # TODO: DB 연결 후 아래 코드 활성화
        # raw_event = await save_raw_event(db_session, payload, integration_id)
        # event = normalize_message(payload, integration_id=integration_id, raw_event_id=raw_event.id)
        # await enqueue_notification(event)


async def run_discord_gateway() -> None:
    """Discord Bot을 단독 실행하는 함수 (로컬 테스트용)."""
    token = settings.DISCORD_BOT_TOKEN
    if not token:
        raise ValueError(
            "DISCORD_BOT_TOKEN이 설정되지 않았습니다. .env 파일을 확인하세요."
        )
    bot = CoChatDiscordBot(intents=intents)
    await bot.start(token)
