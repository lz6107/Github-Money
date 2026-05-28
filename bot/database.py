import os
import aiosqlite
import logging

logger = logging.getLogger(__name__)
DB_PATH = os.getenv("DB_PATH", "/data/releases.db")


class Database:
    def __init__(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self.path = DB_PATH

    async def init(self):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS published (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    release_id  TEXT UNIQUE NOT NULL,
                    repo        TEXT,
                    tag         TEXT,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
        logger.info(f"✅ DB ready: {self.path}")

    async def is_published(self, release_id) -> bool:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                "SELECT 1 FROM published WHERE release_id = ?", (str(release_id),)
            ) as cur:
                return await cur.fetchone() is not None

    async def mark_published(self, release_id, repo: str = "", tag: str = ""):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO published (release_id, repo, tag) VALUES (?,?,?)",
                (str(release_id), repo, tag),
            )
            await db.commit()
