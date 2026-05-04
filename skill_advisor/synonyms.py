"""
30+ 大类同义词映射表 — 中英文双向匹配
"""

SYNONYMS = {
    # === 画图/可视化 ===
    "画图": ["draw", "diagram", "chart", "graph", "可视化", "图表", "绘图", "制图"],
    "架构图": ["architecture diagram", "架构图", "系统架构图", "架构设计图"],
    "架构": ["architecture", "design", "system", "结构", "设计", "体系"],
    "手绘": ["excalidraw", "hand-drawn", "手绘风格", "草图", "whiteboard"],
    "信息图": ["infographic", "baoyu", "信息图", "可视化摘要", "infographics"],
    "像素": ["pixel", "pixel-art", "像素画", "retro", "像素风"],
    "ascii": ["ascii", "ascii-art", "字符画", "文本艺术", "text art"],
    "mermaid": ["uml", "流程图", "时序图", "类图", "状态图", "甘特图"],
    "可视化": ["visualization", "diagram", "chart", "graph", "可视化"],

    # === 文档/写作 ===
    "文档": ["document", "doc", "pdf", "word", "docx", "报告", "文档生成", "documentation"],
    "pdf": ["pdf", "reportlab", "weasyprint", "pdf生成", "pdf排版", "pdf-layout"],
    "docx": ["word", "docx", "office", "word文档", "python-docx"],
    "markdown": ["md", "markdown", "pandoc", "写作", "markdown转换"],
    "latex": ["latex", "学术", "论文", "期刊", "技术报告"],
    "epub": ["epub", "ebook", "电子书", "ebooklib"],
    "写作": ["write", "writing", "作文", "创作", "撰稿", "撰写", "文案"],
    "排版": ["layout", "typesetting", "排版", "设计", "format"],

    # === 搜索/信息获取 ===
    "搜索": ["search", "crawl", "scrape", "fetch", "抓取", "采集", "gather", "查询"],
    "调研": ["research", "investigate", "survey", "分析", "调查", "study"],
    "新闻": ["news", "rss", "订阅", "简报", "briefing", "newsletter", "报刊"],

    # === 学习/研究 ===
    "学习": ["learn", "study", "research", "研究", "探索", "掌握", "了解", "搞懂", "熟悉"],
    "沉淀": ["extract", "refine", "总结", "归纳", "提炼", "整合", "consolidate"],
    "反思": ["reflect", "review", "复盘", "总结", "retrospective", "回顾"],

    # === 代码/开发 ===
    "编程": ["code", "program", "develop", "coding", "编程", "开发", "写代码"],
    "调试": ["debug", "调试", "排错", "bug", "错误", "修复", "fix", "问题排查"],
    "git": ["git", "github", "版本控制", "提交", "commit", "push", "pull", "rebase"],
    "代码审查": ["code review", "review", "审查", "审核", "cr"],
    "review": ["review", "审查", "审核", "代码审查", "code review", "cr"],
    "重构": ["refactor", "重构", "优化", "优化代码", "代码重构"],
    "测试": ["test", "verify", "check", "validate", "验证", "单元测试", "自动化测试", "testing"],
    "部署": ["deploy", "publish", "upload", "发布", "上传", "同步", "ci/cd"],
    "prd": ["product requirement", "产品需求", "prd", "产品文档", "需求文档"],
    "计划": ["plan", "planning", "规划", "设计", "方案", "architecture"],

    # === 工具/操作 ===
    "文件": ["file", "organize", "manage", "整理", "管理", "分类", "文件操作"],
    "代理": ["proxy", "mihomo", "clash", "sing-box", "代理配置", "梯子", "翻墙"],
    "定时": ["schedule", "cron", "timer", "定时任务", "计划", "周期性", "cronjob", "调度"],
    "翻译": ["translate", "convert", "转换", "翻译", "translation", "i18n"],
    "邮件": ["email", "mail", "message", "消息", "himalaya", "发邮件"],
    "微信": ["wechat", "weixin", "微信", "公众号", "wx", "企业微信"],
    "飞书": ["feishu", "lark", "飞书", "开放平台"],

    # === 数据/分析 ===
    "金融": ["stock", "finance", "股票", "基金", "akshare", "金融数据", "行情"],
    "数据": ["data", "dataset", "数据分析", "analysis", "数据处理", "pandas", "统计"],
    "excel": ["spreadsheet", "excel", "表格", "xlsx", "电子表格", "openpyxl"],

    # === 多媒体 ===
    "ppt": ["powerpoint", "presentation", "幻灯片", "演示", "pptx", "python-pptx"],
    "视频": ["video", "animation", "manim", "动画", "视频", "movie"],
    "音乐": ["music", "song", "suno", "作曲", "歌词", "生成音乐", "audio"],
    "图片": ["image", "picture", "photo", "照片", "图片生成", "生成图", "illustration"],
    "gif": ["gif", "动图", "表情包", "tenor"],

    # === 沟通/协作 ===
    "汇报": ["report", "summary", "日报", "周报", "报告", "总结"],
    "通知": ["notify", "notification", "alert", "提醒", "推送", "广播"],
    "分享": ["share", "share到", "发到", "发送到", "post to"],

    # === 系统/运维 ===
    "服务器": ["server", "ubuntu", "linux", "运维", "ops", "system", "管理"],
    "浏览器": ["browser", "chrome", "headless", "自动化浏览器", "web自动化"],
    "监控": ["monitor", "watch", "监控", "日志", "健康检查", "health check"],
    "健康检查": ["health check", "诊断", "报错", "429", "健康检查"],

    # === AI/ML ===
    "ai": ["ai", "llm", "model", "人工智能", "大模型", "大语言模型", "agent", "gpt"],
    "agent": ["agent", "智能体", "多agent", "multi-agent", "ai agent", "autonomous"],
    "机器学习": ["machine learning", "ml", "深度学习", "neural network", "神经网络"],
    "微调": ["finetune", "fine-tuning", "微调", "lora", "sft", "trl"],
    "llm": ["llm", "大模型", "语言模型", "gpt", "claude"],

    # === 游戏/娱乐 ===
    "游戏": ["game", "gaming", "minecraft", "pokemon", "游戏开发", "游戏设计", "gdd"],
    "minecraft": ["mc", "minecraft", "我的世界", "mod", "模组", "服务器"],

    # === Hermes 自身 ===
    "技能": ["skill", "hermes skill", "工作流", "workflow", "学习流程", "boku"],
    "记忆": ["memory", "记忆", "长期记忆", "persistent memory", "remember"],
    "hermes": ["hermes", "小玛", "艾玛", "emma", "小喵", "猫娘", "女仆"],
    "播报": ["broadcast", "播报", "广播", "通知", "播报状态", "智能播报"],
    "飞书": ["feishu", "lark", "飞书"],
}

# 构建反向索引（同义词值 → 同义词键）
REVERSE_INDEX = {}
for key, syns in SYNONYMS.items():
    for syn in syns:
        syn_lower = syn.lower()
        if syn_lower not in REVERSE_INDEX:
            REVERSE_INDEX[syn_lower] = []
        REVERSE_INDEX[syn_lower].append(key.lower())
