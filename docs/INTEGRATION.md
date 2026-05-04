# 集成指南

## 作为 Hermes Agent 插件

### 前置层集成

在 `learning-workflow` 中插入 SRA 作为前置层：

```python
# 在 learning-workflow 的强制拦截流程中
from sra_agent import SkillAdvisor

advisor = SkillAdvisor()
result = advisor.recommend(user_input)

if result["recommendations"]:
    top = result["recommendations"][0]
    if top["confidence"] == "high":
        # 得分 ≥ 80: 直接加载该 skill
        skill_view(top["skill"])
    elif top["confidence"] == "medium":
        # 得分 ≥ 40: 附加提示
        print(f"💡 建议使用 skill: {top['skill']} ({top['score']}分)")
```

### System Prompt 增强

在 `<available_skills>` 块中增加 triggers 信息：

```bash
sra --enhanced-prompt
```

输出包含 triggers 的增强版 skill 列表：
```
<available_skills>
  creative:
    - architecture-diagram: Generate dark-themed SVG diagrams [triggers: architecture diagram/architecture-diagram]
    - mermaid-guide: Mermaid 图表生成指南 [triggers: mermaid guide/mermaid-guide]
  ...
</available_skills>
```

## 作为独立服务

### CLI 模式

```bash
# 安装
pip install sra-agent

# 推荐
sra --query "帮我画个架构图"

# 刷新索引
sra --refresh

# 查看统计
sra --stats
```

### HTTP 服务（后续版本）

```python
# TODO: Flask/FastAPI 集成
```

## 迁移指南

### 从旧版 SRA 迁移

旧版 SRA（单脚本 skill-advisor.py）的数据可以自动迁移：

```bash
# 旧版数据位置
~/.hermes/skills/skill-advisor/data/

# 新版数据位置（默认）
~/.sra_agent/data/
```

复制数据文件即可：

```bash
cp ~/.hermes/skills/skill-advisor/data/*.json ~/.sra_agent/data/
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `SRA_SKILLS_DIR` | 技能目录路径 | `~/.hermes/skills` |
| `SRA_DATA_DIR` | 数据持久化路径 | `~/.sra_agent/data` |
