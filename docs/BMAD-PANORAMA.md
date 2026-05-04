# SRA 项目全景审视 — BMAD 文档一致性检查

> 生成时间：2026-05-04
> 方法：BMAD Doc Sync + 全景审视

---

## 一、项目元信息

| 项目 | 值 |
|------|-----|
| 名称 | SRA — Skill Runtime Advisor |
| 版本 | v1.1.0 |
| Python | 3.8+ |
| 依赖 | pyyaml（唯一！） |
| CLI 入口 | `skill_advisor.cli:main` → `sra` |
| Daemon 入口 | `skill_advisor.runtime.daemon:cmd_start` → `srad` |
| GitHub | JackSmith111977/Hermes-Skill-View |
| 当前分支 | `feat/design-philosophy-overhaul` |
| Daemon 状态 | 运行中 (PID 911859, 279 skills, 端口 8536) |

---

## 二、BMAD 三问：目标 / 现状 / 未来

### 🎯 最初的目标（Why SRA exists）

SRA 诞生的**核心痛点**是：

> **Hermes Agent 的 skill 发现机制完全依赖 prompt 中的 `<available_skills>` 列表，而该列表是静态的、人工维护的。当技能库扩大到 60+ 时，AI Agent 经常忽略合适的技能。**

具体痛点：
1. Agent 不知道"自己有什么能力"，每次都要在长列表中翻找
2. 新加一个 SKILL.md，Agent 不会立即知道
3. 技能的 triggers/description 写得不好，Agent 就完全不会用
4. 没有反馈闭环——Agent 用了哪个技能、效果如何，不可追踪

**SRA 的定位：为 Hermes Agent 提供一个实时的、语义感知的 skill 发现机制——一个运行时中间件。**

### 📍 目前的现状（What SRA has now）

**内核能力（已实现）：**
- ✅ 守护进程：7x24 运行，Unix Socket + HTTP 双协议
- ✅ 语义引擎：同义词扩展 + TF-IDF + 共现矩阵的混合匹配
- ✅ Proxy 模式：消息前置推理，返回 rag_context
- ✅ 场景记忆：记录哪些输入触发了哪些 skill
- ✅ 覆盖率分析：发现技能库中的知识盲区
- ✅ 多 Agent 适配器：Hermes / Claude / Codex / 通用
- ✅ 自动索引刷新（定时 1h）
- ✅ 环境自检脚本（check-sra.py）

**文档/部署现状（已验证）：**
- ✅ README 已精简（但定位可能偏差）
- ✅ check-sra.py 工作正常
- ✅ install.sh 有多路径降级策略
- ⚠️ 缺少作为"运行时"的定位说明
- ❌ 新增的 SKILL.md 不适用（SRA 不是技能）
- ❌ .claude-plugin/ 不必要
- ❌ watch_skills_dir 文件监听未生效

### 🚀 未来的提升方向（What SRA should become）

**近期（当前分支要做的）：**
1. 修正定位文档：从"技能"思维切换到"运行时"思维
2. 删除不适用的文件（SKILL.md, .claude-plugin/）
3. 修正 README 定位描述
4. 新增 **RUNTIME.md** — 给 Hermes Agent 看的运行时集成说明
5. 修复 watch_skills_dir 自动监听

**中期（下个版本）：**
1. 推荐质量提升：解决"设计数据库"被推荐为 PDF 排版的问题
2. 覆盖率提升：36 个未识别技能需要分析原因并改进匹配策略
3. daemon 自动重启机制（目前依赖 systemd）
4. Hermes Agent 的消息拦截自动化（当前需要手动配 AGENTS.md）

**远期（v2.0 方向）：**
1. 主动学习：根据场景记忆自动调整推荐权重
2. 多级推荐：不仅是 skill 级别，还能推荐 skill 内的具体章节
3. 插件生态：允许第三方开发者贡献新的匹配策略
4. Agent 反馈回路：Agent 用了推荐技能后自动反馈结果给 SRA

---

## 三、分支改动审查

### ✅ 合理改进（保留）

| 改动 | 理由 | 验证 |
|------|------|------|
| README 精简至 ~175 行 | 信息过载解决，AI 友好度提升 | ✅ 已验证 |
| install.sh 多路径策略 | 降低安装失败概率 | ✅ 已验证 |
| check-sra.py | 环境自检核心，大幅提升 AI 可观测性 | ✅ 已验证 |
| install.sh 末尾增加自检指引 | 安装后自动提示自检 | ✅ 已验证 |

### ❌ 不合适的照抄（需删除/修正）

| 改动 | 照抄来源 | 为什么不合适 |
|------|---------|-------------|
| SKILL.md（仿 web-access 格式） | web-access | SRA 是**运行时**不是**技能**，SKILL.md 格式只适用于 Agent 可加载的工具 |
| .claude-plugin/marketplace.json | web-access | SRA 不面向 Claude Code，它的用户是 Hermes Agent |
| .claude-plugin/plugin.json | web-access | 同上 |
| SKILL.md 中的"前置检查→哲学→命令→故障排除"结构 | web-access | 运行时应该有自己的文档结构，不是技能格式 |

### ⚠️ 需要修正的内容（在保留基础上修正）

| 当前内容 | 问题 | 修正方式 |
|---------|------|---------|
| README 中"让 AI Agent 拥有运行时技能推荐能力的轻量级引擎" | 核心定位可以，但"引擎"一词不够准确 | 改为"运行时消息前置推理中间件" |
| "核心能力"表格中的描述 | 从技能视角写的 | 改为运行时视角 |
| "设计哲学"章节 | 三个原则不错但侧重偏了 | 重写为运行时的设计原则 |

---

## 四、修正行动计划

```
DELETE:
  .claude-plugin/marketplace.json    # SRA 不需要 Claude Code 集成
  .claude-plugin/plugin.json          # 同上
  SKILL.md                            # SRA 不是技能，不需要 SKILL.md 格式

CREATE:
  RUNTIME.md                          # 给 Hermes Agent 看的运行时集成文档
                                      # 解释 SRA 如何在消息管道中工作

MODIFY:
  README.md                           # 修正定位：运行时中间件
                                      # 精简设计哲学章节
                                      # 引用 RUNTIME.md 作为详细参考
```
