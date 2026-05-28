import os
import io
import httpx
import logging
from .ai_processor import generate_text, generate_image

logger = logging.getLogger(__name__)

BOT_TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHANNEL_ID   = os.getenv("TELEGRAM_CHANNEL_ID", "")
TG_BASE      = f"https://api.telegram.org/bot{BOT_TOKEN}"


class TelegramPublisher:

    async def publish(self, release: dict):
        if not BOT_TOKEN or not CHANNEL_ID:
            logger.error("❌ 缺少 TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHANNEL_ID")
            return

        repo = release.get("repo", "")

        # 并发生成文案和图片
        import asyncio
        text, image_bytes = await asyncio.gather(
            generate_text(release),
            generate_image(repo),
        )

        if image_bytes:
            await self._send_photo(image_bytes, text)
        else:
            await self._send_message(text)

        logger.info(f"✅ 已推送: {repo} {release.get('tag_name')}")

    # ── 带图推送 ──────────────────────────────
    async def _send_photo(self, image_bytes: bytes, caption: str):
        # Telegram caption 上限 1024 字符，超出截断
        cap = caption[:1020] + "…" if len(caption) > 1024 else caption
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{TG_BASE}/sendPhoto",
                data={"chat_id": CHANNEL_ID, "caption": cap, "parse_mode": "Markdown"},
                files={"photo": ("cover.png", io.BytesIO(image_bytes), "image/png")},
            )
            if r.status_code != 200:
                logger.error(f"sendPhoto 失败: {r.text}")
                # 降级：纯文本
                await self._send_message(caption)

    # ── 纯文本推送（降级用）──────────────────
    async def _send_message(self, text: str):
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"{TG_BASE}/sendMessage",
                json={
                    "chat_id": CHANNEL_ID,
                    "text": text,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                },
            )
            if r.status_code != 200:
                logger.error(f"sendMessage 失败: {r.text}")
