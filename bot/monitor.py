import os
import httpx
import logging
from typing import Optional
from .database import Database

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════
#  监控仓库列表  —  可随时增删
#  格式: "owner/repo": "分类"
# ══════════════════════════════════════════════
WATCH_REPOS = {
    # 🤖 AI / LLM 工具
    "lobehub/lobe-chat":               "AI工具",
    "langgenius/dify":                  "AI工具",
    "ollama/ollama":                    "AI工具",
    "open-webui/open-webui":            "AI工具",
    "BerriAI/litellm":                  "AI工具",
    "mudler/LocalAI":                   "AI工具",
    "chatchat-space/Langchain-Chatchat":"AI工具",
    # ⚙️ 自动化 / 赚钱工具
    "n8n-io/n8n":                       "自动化",
    "activepieces/activepieces":        "自动化",
    "nocodb/nocodb":                    "自动化",
    "automatisch/automatisch":          "自动化",
    "AppFlowy-IO/AppFlowy":             "自动化",
    # 🚀 开源 SaaS
    "calcom/cal.com":                   "开源SaaS",
    "formbricks/formbricks":            "开源SaaS",
    "twentyhq/twenty":                  "开源SaaS",
    "documenso/documenso":              "开源SaaS",
    "plausible/analytics":              "开源SaaS",
    "supabase/supabase":                "开源SaaS",
}

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    **({"Authorization": f"Bearer {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}),
}


class GitHubMonitor:
    def __init__(self, db: Database):
        self.db = db

    async def fetch_new_releases(self) -> list[dict]:
        results = []
        async with httpx.AsyncClient(timeout=20) as client:
            for repo, category in WATCH_REPOS.items():
                try:
                    release = await self._get_latest_release(client, repo)
                    if release and not await self.db.is_published(release["id"]):
                        release["repo"] = repo
                        release["category"] = category
                        results.append(release)
                except Exception as e:
                    logger.warning(f"⚠️  {repo}: {e}")
        logger.info(f"共发现 {len(results)} 个未推送 release")
        return results

    async def _get_latest_release(self, client: httpx.AsyncClient, repo: str) -> Optional[dict]:
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        r = await client.get(url, headers=HEADERS)
        if r.status_code == 200:
            return r.json()
        # fallback：获取列表第一条
        url = f"https://api.github.com/repos/{repo}/releases?per_page=1"
        r = await client.get(url, headers=HEADERS)
        if r.status_code == 200:
            items = r.json()
            return items[0] if items else None
        return None
