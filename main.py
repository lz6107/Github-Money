import os
import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bot.monitor import GitHubMonitor
from bot.publisher import TelegramPublisher
from bot.database import Database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

POSTS_PER_DAY = int(os.getenv("POSTS_PER_DAY", "5"))
POST_HOUR = int(os.getenv("POST_HOUR", "10"))   # 每天几点开始推送（UTC）
POST_INTERVAL_MINUTES = int(os.getenv("POST_INTERVAL_MINUTES", "60"))  # 每条间隔分钟


async def main():
    db = Database()
    await db.init()

    monitor = GitHubMonitor(db)
    publisher = TelegramPublisher()

    async def daily_job():
        logger.info("🔍 开始抓取新 releases...")
        releases = await monitor.fetch_new_releases()
        to_send = releases[:POSTS_PER_DAY]
        logger.info(f"📦 今日推送 {len(to_send)} / {len(releases)} 条")

        for i, release in enumerate(to_send):
            logger.info(f"📤 [{i+1}/{len(to_send)}] {release['repo']} {release['tag_name']}")
            await publisher.publish(release)
            await db.mark_published(release["id"], release["repo"], release["tag_name"])
            if i < len(to_send) - 1:
                await asyncio.sleep(POST_INTERVAL_MINUTES * 60)

    scheduler = AsyncIOScheduler(timezone="UTC")
    # 每天 POST_HOUR 点触发
    scheduler.add_job(daily_job, "cron", hour=POST_HOUR, minute=0)
    scheduler.start()

    logger.info(f"🚀 Bot 启动，每天 UTC {POST_HOUR}:00 推送 {POSTS_PER_DAY} 条")

    # 首次启动立即运行一次（方便测试）
    if os.getenv("RUN_ON_START", "true").lower() == "true":
        await daily_job()

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
