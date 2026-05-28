import os
import httpx
import logging

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GPT_MODEL = "gpt-4o-mini"
IMAGE_MODEL = "dall-e-3"
IMAGE_SIZE = "1024x1024"   # DALL-E 3 最低规格，省钱

# ══════════════════════════════════════════════
#  文案 Prompt
# ══════════════════════════════════════════════
SYSTEM_PROMPT = """你是一个专注「用开源工具搞副业赚钱」的科技博主，受众是想用 AI/自动化工具做副业的普通人。

收到 GitHub 项目信息后，输出一篇结构严格的 Telegram 推文，**必须包含且仅包含以下六个板块**，用 emoji 标题分隔：

🔧 **项目介绍**
（1-2句，说清楚这是什么、解决什么问题，中文）

💰 **变现途径**
（2-3条，具体的赚钱方式，例如：接私单/卖服务/部署SaaS收费）

🛠️ **怎么上手**
（3-4步，最核心的操作步骤，不废话）

📚 **技术要求 & 上手难度**
（需要什么基础，难度用 ⭐ 表示：1-5颗星）

🔗 **项目地址**
（原样保留 GitHub 链接）

规则：
- 全程中文
- 总字数控制在 300 字以内
- 禁止废话（"本项目"、"值得关注"、"总的来说" 之类全删）
- 语气轻松直接，像朋友推荐不像说明书"""


async def generate_text(release: dict) -> str:
    repo = release.get("repo", "")
    tag = release.get("tag_name", "")
    name = release.get("name", tag) or tag
    body = (release.get("body") or "")[:1500]
    category = release.get("category", "")
    url = release.get("html_url", f"https://github.com/{repo}")
    short_name = repo.split("/")[-1]

    user_msg = f"""项目名: {short_name}
仓库: {repo}
分类: {category}
版本: {tag}
标题: {name}
更新内容:
{body if body else "（无说明）"}
链接: {url}"""

    if not OPENAI_API_KEY:
        logger.warning("未设置 OPENAI_API_KEY，使用备用模板")
        return _fallback(release)

    try:
        async with httpx.AsyncClient(timeout=40) as client:
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GPT_MODEL,
                    "max_tokens": 700,
                    "temperature": 0.7,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_msg},
                    ],
                },
            )
            data = r.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"GPT 文案生成失败: {e}")
        return _fallback(release)


async def generate_image(repo: str) -> bytes | None:
    """用 DALL-E 3 生成极简线条风格项目图，返回 PNG bytes"""
    if not OPENAI_API_KEY:
        return None

    short_name = repo.split("/")[-1]
    prompt = (
        f"Minimal flat line-art icon for a software project called '{short_name}'. "
        "Pure white background, single thin black outline, geometric shapes only, "
        "no color fills, no text, no gradients, no shadows. "
        "Style: ultra-minimal SVG icon, similar to Material Design outlined icons."
    )

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                "https://api.openai.com/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": IMAGE_MODEL,
                    "prompt": prompt,
                    "n": 1,
                    "size": IMAGE_SIZE,
                    "response_format": "url",
                },
            )
            data = r.json()
            img_url = data["data"][0]["url"]

            # 下载图片 bytes
            img_r = await client.get(img_url, timeout=30)
            return img_r.content
    except Exception as e:
        logger.error(f"DALL-E 图片生成失败: {e}")
        return None


def _fallback(release: dict) -> str:
    repo = release.get("repo", "")
    tag = release.get("tag_name", "")
    url = release.get("html_url", f"https://github.com/{repo}")
    short_name = repo.split("/")[-1]
    cat_emoji = {"AI工具": "🤖", "自动化": "⚙️", "开源SaaS": "🚀"}.get(
        release.get("category", ""), "📦"
    )
    return f"""{cat_emoji} **{short_name}** 发布 {tag}

🔧 **项目介绍**
开源项目 {short_name} 发布新版本。

💰 **变现途径**
可基于此项目搭建服务并收费。

🛠️ **怎么上手**
1. Star 项目  2. 阅读文档  3. 本地部署

📚 **技术要求 & 上手难度**
基础编程能力 ⭐⭐⭐

🔗 **项目地址**
{url}"""
