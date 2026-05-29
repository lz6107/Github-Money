import os
import io
import httpx
import logging
from .ai_processor import generate_text, generate_image
import asyncio

logger = logging.getLogger(__name__)

BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")


def _tg_base():
    return f"https://api.telegram.org/bot{BOT_TOKEN}"


class TelegramPublisher:

    async def publish(self, release: dict):
        if not BOT_TOKEN or not CHANNEL_ID:
            logger.error("❌ 缺少 TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHANNEL_ID")
            return

        repo = release.get("repo", "")
        logger.info(f"⏳ 生成文案和图片: {repo}")

        # 并发生成文案 + 图片
        text, image_bytes = await asyncio.gather(
            generate_text(release),
            generate_image(repo),
        )

        if image_bytes:
            # 先发图（无 caption），再发文字 —— 彻底绕开 1024 字符限制
            sent = await self._send_photo(image_bytes)
            if sent:
                await asyncio.sleep(1)
                await self._send_message(text)
            else:
                # 图片发送失败降级为纯文字
                await self._send_message(text)
        else:
            await self._send_message(text)

        logger.info(f"✅ 推送完成: {repo} {release.get('tag_name')}")

    async def _send_photo(self, image_bytes: bytes) -> bool:
        """发送图片，成功返回 True"""
        try:
            async with httpx.AsyncClient(timeout=40) as client:
                r = await client.post(
                    f"{_tg_base()}/sendPhoto",
                    data={"chat_id": CHANNEL_ID},
                    files={"photo": ("cover.png", io.BytesIO(image_bytes), "image/png")},
                )
                if r.status_code == 200:
                    logger.info("🖼️  图片发送成功")
                    return True
                else:
                    logger.error(f"sendPhoto 失败 [{r.status_code}]: {r.text}")
                    return False
        except Exception as e:
            logger.error(f"sendPhoto 异常: {e}")
            return False

    async def _send_message(self, text: str):
        """发送文字，自动分段避免超 4096 字符限制"""
        chunks = _split_text(text, limit=4000)
        async with httpx.AsyncClient(timeout=20) as client:
            for chunk in chunks:
                r = await client.post(
                    f"{_tg_base()}/sendMessage",
                    json={
                        "chat_id":                  CHANNEL_ID,
                        "text":                     chunk,
                        "parse_mode":               "Markdown",
                        "disable_web_page_preview": True,
                    },
                )
                if r.status_code != 200:
                    logger.error(f"sendMessage 失败 [{r.status_code}]: {r.text}")
                await asyncio.sleep(0.5)


def _split_text(text: str, limit: int = 4000) -> list[str]:
    """按段落切分，保证每段不超过 limit 字符"""
    if len(text) <= limit:
        return [text]
    chunks, current = [], ""
    for para in text.split("\n\n"):
        if len(current) + len(para) + 2 > limit:
            if current:
                chunks.append(current.strip())
            current = para
        else:
            current = (current + "\n\n" + para) if current else para
    if current:
        chunks.append(current.strip())
    return chunks
