import os
import httpx
import logging

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GPT_MODEL  = "gpt-4o-mini"
IMAGE_MODEL = "dall-e-3"
IMAGE_SIZE  = "1024x1024"

# ══════════════════════════════════════════════
#  文案 Prompt
# ══════════════════════════════════════════════
SYSTEM_PROMPT = """你是一个在摸索用 AI 和自动化工具做副业的普通人，偶尔在 Telegram 上分享自己用过或研究过的工具。

收到 GitHub 项目信息后，写一篇分享帖，包含以下五个板块，顺序不变：

🔧 **是什么**
用类比的方式说清楚，比如"有点像自建版的 Zapier，但免费"。1-2句，不啰嗦。

💰 **能怎么赚**
写 3-4 条，每条都要有具体数字或场景。
举例风格："帮连锁美甲店搭一套自动回复+预约系统，一次性收费 2000-3000，后续按月维护再收 300"。
至少一条说冷门但可行的方向，末尾可以加一句自己的判断（"我觉得""说实话"开头）。

🛠️ **怎么上手**
写 4-5 步，每步说清楚做什么、大概要多久、有没有坑。
比如："第二步：用 Docker 一键部署到自己服务器，第一次弄大概需要半小时，主要卡在端口配置上"。

📚 **门槛**
两句话：第一句说需要什么基础，第二句说最难的地方在哪。
结尾标注：🟢 新手友好 / 🟡 需要一点技术 / 🔴 有开发经验更好

🔍 **去哪找**
不放链接，说清楚搜什么词能找到，一句话。
比如："GitHub 搜项目名，或者直接谷歌搜『项目名 self-host』"。

---
硬规则：
- 禁止出现：该项目 / 本工具 / 值得关注 / 非常强大 / 总的来说 / 欢迎
- 禁止任何 URL、域名、@ 符号、结尾号召语
- 口语化，偶尔夹一两句自己的感受，别全程像说明书
- 字数 320-380 字，不要超"""


async def generate_text(release: dict) -> str:
    repo       = release.get("repo", "")
    tag        = release.get("tag_name", "")
    name       = release.get("name", tag) or tag
    body       = (release.get("body") or "")[:1500]
    category   = release.get("category", "")
    short_name = repo.split("/")[-1]

    user_msg = f"""项目名: {short_name}
分类: {category}
版本: {tag}
标题: {name}
更新内容:
{body if body else "（无更新说明）"}"""

    if not OPENAI_API_KEY:
        logger.warning("未设置 OPENAI_API_KEY，使用备用模板")
        return _fallback(release)

    try:
        async with httpx.AsyncClient(timeout=45) as client:
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GPT_MODEL,
                    "max_tokens": 900,
                    "temperature": 0.75,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user",   "content": user_msg},
                    ],
                },
            )
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"GPT 文案生成失败: {e}")
        return _fallback(release)


async def generate_image(repo: str) -> bytes | None:
    """DALL-E 3 极简线条图，返回 PNG bytes；失败返回 None"""
    if not OPENAI_API_KEY:
        return None

    short_name = repo.split("/")[-1]
    prompt = (
        f"Minimal flat line-art tech icon representing a software tool called '{short_name}'. "
        "Pure white background. Single thin black stroke outlines only. "
        "Geometric and symbolic shapes — no text, no color fills, no gradients, no shadows, no photorealism. "
        "Think: clean app icon in the style of Material Design outlined symbols."
    )

    try:
        # Step 1: 请求 DALL-E 生成，拿到临时 URL
        async with httpx.AsyncClient(timeout=90) as gen_client:
            r = await gen_client.post(
                "https://api.openai.com/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model":           IMAGE_MODEL,
                    "prompt":          prompt,
                    "n":               1,
                    "size":            IMAGE_SIZE,
                    "response_format": "url",
                },
            )
            r.raise_for_status()
            data    = r.json()
            img_url = data["data"][0]["url"]
            logger.info(f"🎨 DALL-E 图片生成成功，开始下载...")

        # Step 2: 用独立 client 立刻下载（URL 有效期约1小时，但越快越好）
        async with httpx.AsyncClient(timeout=60) as dl_client:
            img_r = await dl_client.get(img_url)
            img_r.raise_for_status()
            logger.info(f"✅ 图片下载完成，大小: {len(img_r.content) // 1024} KB")
            return img_r.content

    except Exception as e:
        logger.error(f"DALL-E 图片生成/下载失败: {e}")
        return None


def _fallback(release: dict) -> str:
    repo       = release.get("repo", "")
    short_name = repo.split("/")[-1]
    cat_emoji  = {"AI工具": "🤖", "自动化": "⚙️", "开源SaaS": "🚀"}.get(
        release.get("category", ""), "📦"
    )
    return f"""{cat_emoji} **{short_name}**

🔧 **是什么**
一个开源工具，可以自己部署来搭建服务或做副业。

💰 **能怎么赚**
• 帮中小商家搭建自动化流程，收一次性部署费
• 自己搭一套 SaaS 对外收订阅费
• 接自由职业单子，按需定制

🛠️ **怎么上手**
1. 搜索项目名找到官方文档（10分钟）
2. 按文档在本地跑起来（30-60分钟）
3. 试着用 Docker 部署到云服务器（1-2小时）
4. 摸清功能后想想自己能做什么场景

📚 **门槛**
需要基础的命令行操作能力，最难的地方是第一次部署时的环境配置。🟡 需要一点技术

🔍 **去哪找**
GitHub 搜项目名，文档和安装说明都在那儿"""
