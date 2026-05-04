# Story 1: SRA Hook 模块 — Gateway 消息前置推理

> **Story ID:** SRA-001
> **关联 Epic:** SRA-EPIC-001
> **状态:** 📋 待实现
> **优先级:** 🔴 高
> **估算:** 2小时

## 用户故事

作为 Hermes Gateway 用户，我希望每次发消息时 SRA 自动推荐技能，这样我就不用手动指定用哪个 skill。

## 验收标准

- [ ] 创建 `~/.hermes/hooks/sra-recommend/` 目录
- [ ] 创建 `HOOK.yaml` 声明绑定 `agent:start` 事件
- [ ] 创建 `handler.py` 实现自动调 SRA Daemon
- [ ] rag_context 注入到 system prompt 中
- [ ] should_auto_load≥80 时自动在上下文标记建议加载的 skill
- [ ] SRA Daemon 不可用时优雅降级
- [ ] 在回复开头标注 `[SRA]` 推荐结果

## 技术方案

### HOOK.yaml

```yaml
name: sra-recommend
description: 在每次消息处理前自动调 SRA 获取技能推荐
events:
  - agent:start
```

### handler.py 逻辑

```
1. 从 context 中提取 message
2. curl POST http://127.0.0.1:8536/recommend
3. 如果成功 → 提取 rag_context
4. 如果 should_auto_load=true → 标记需自动加载的 skill
5. 将 rag_context 写入某个位置供 LLM 感知
6. 如果失败 → 静默降级（只记日志）
```

### 上下文注入策略

**方案A（推荐）：通过环境变量传递**
- 将 rag_context 写入 `HERMES_SESSION_SRA_CONTEXT` 环境变量
- 在 system prompt 构建时读取该变量

**方案B：通过文件传递**
- 写入临时文件 `~/.sra/latest_context.txt`
- system prompt 中引用该文件

---

# Story 2: CLI 模式集成

> **Story ID:** SRA-002
> **关联 Epic:** SRA-EPIC-001
> **状态:** 📋 待实现
> **优先级:** 🟡 中
> **估算:** 1小时

## 用户故事

作为 CLI 用户，我也可以在终端中使用 SRA 的自动推荐能力。

## 验收标准

- [ ] CLI 模式每次消息前调 SRA
- [ ] rag_context 作为 system note 注入
- [ ] 与 Gateway 模式共用 Hook 模块
- [ ] CLI 模式测试通过

---

# Story 3: 测试 + 文档

> **Story ID:** SRA-003
> **关联 Epic:** SRA-EPIC-001
> **状态:** 📋 待实现
> **优先级:** 🟡 中
> **估算:** 1小时

## 验收标准

- [ ] 单元测试覆盖 Hook handler
- [ ] 集成测试覆盖 SRA Daemon 正常/降级场景
- [ ] 更新 README 的集成指南
- [ ] 更新 DESIGN.md 的架构图
