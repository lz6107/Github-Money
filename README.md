# GitHub → GPT → Telegram 自动推送 Bot

每天自动从 GitHub 抓取 AI工具 / 自动化 / 开源SaaS 新版本，用 **GPT-4o-mini** 生成六要素解读推文，**DALL-E 3** 配上极简线条插图，定时推送到 Telegram 频道。

## 推文结构（每条固定格式）

```
[极简线条配图]

🔧 项目介绍
💰 变现途径
🛠️ 怎么上手
📚 技术要求 & 上手难度（⭐ 评分）
🔗 项目地址
```

## 费用估算（每天 5 条）

| 费用项 | 单价 | 每天用量 | 月费 |
|--------|------|----------|------|
| GPT-4o-mini 文案 | $0.15/1M tokens | ~3500 tokens/天 | ~$0.02 |
| DALL-E 3 配图 | $0.04/张（1024²） | 5 张/天 | ~$6 |
| Railway Hobby | 固定 | — | $5 |
| **合计** | | | **≈ $11/月** |

> 💡 若觉得 DALL-E 配图贵，可在 `bot/ai_processor.py` 把 `generate_image` 改为返回 `None`，自动降级为纯文本推送，月费降至 **~$5**。

## 快速部署

### 第一步：准备三个 Token

**① OpenAI API Key**
→ [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

**② Telegram Bot Token**
1. 打开 Telegram，找 `@BotFather`
2. 发 `/newbot` 按提示操作
3. 把 Bot 加为频道管理员（需要"发送消息"权限）

**③ 频道 ID**
- 公开频道直接用 `@频道用户名`
- 私有频道：Bot 加入后发条消息，访问：
  `https://api.telegram.org/bot<TOKEN>/getUpdates`
  找 `"chat":{"id":...}` 的数字

### 第二步：部署到 Railway

```bash
# 1. 把本项目 push 到你的 GitHub 仓库

# 2. railway.app → New Project → Deploy from GitHub repo → 选仓库

# 3. 添加环境变量（Dashboard → Variables → Raw Editor 粘贴）：
OPENAI_API_KEY=sk-...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHANNEL_ID=@your_channel
POST_HOUR=2          # UTC 2 = 北京时间 10:00
POSTS_PER_DAY=5

# 4. 添加持久化 Volume（防重启后重复推送）
#    Dashboard → Add Volume → Mount Path 填 /data
```

### 本地测试

```bash
pip install -r requirements.txt
cp .env.example .env   # 填入真实值
python main.py
```

## 自定义

### 修改监控仓库
编辑 `bot/monitor.py` 顶部的 `WATCH_REPOS`：
```python
WATCH_REPOS = {
    "owner/repo": "分类标签",
    "vercel/next.js": "前端工具",
}
```

### 关闭配图（省钱）
`bot/ai_processor.py` → `generate_image` 函数第一行加：
```python
return None
```

### 调整推文风格
`bot/ai_processor.py` → 修改 `SYSTEM_PROMPT`。

## 目录结构

```
├── main.py                 # 入口 + APScheduler 定时
├── bot/
│   ├── monitor.py          # GitHub API 抓取新 release
│   ├── ai_processor.py     # GPT-4o-mini 文案 + DALL-E 3 配图
│   ├── publisher.py        # Telegram sendPhoto / sendMessage
│   └── database.py         # SQLite 去重记录
├── requirements.txt
├── railway.toml
└── .env.example
```
