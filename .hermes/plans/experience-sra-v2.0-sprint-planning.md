# 经验：SRA v2.0 迭代规划与 BMad 工作流整合

## 元数据

- **日期**: 2026-05-10
- **类型**: experience（动作级经验）
- **可复用性**: high
- **置信度**: 5/5
- **分类**: 项目管理 / 敏捷开发流程

## 场景

为 SRA (Skill Runtime Advisor) 项目启动 v2.0 迭代，创建 `feat/v2.0-enforcement-layer` 分支，并将一致性检测整合到 BMad 敏捷开发工作流中。

## 做了什么

1. **迭代规划**：
   - 基于已有的 EPIC-003 文档，创建 Sprint 1 计划（6 个 Story，~14 天）
   - 运行时力度体系从「阻断强度」重设计为「注入覆盖度」（4 级：basic/medium/advanced/omni）
   - 所有计划文档保存在 `.hermes/plans/` 目录下

2. **分支管理**：
   - `git checkout -b feat/v2.0-enforcement-layer`
   - 3 个 commit：初始化分支 → 力度体系设计 → 重构为注入覆盖度模型

3. **一致性检测整合**：
   - 将 `commit-quality-check` 作为 `bmad-method` 的强制依赖
   - 在 BMad 工作流的 Phase 4（实现阶段）加入一致性检测步骤
   - 添加「完成任务先跑一致性检测再提交」的避坑指南
   - 添加设计原则第 6 条：Injection Over Interruption

## 关键发现

### 1. 运行时力度的核心设计原则
- **不要阻断，只注入**：用户的明确偏好是「永不阻断（no blocking）」，强度通过注入覆盖度控制
- 4 个注入层级：
  - L1 basic: 仅用户消息时推荐注入（当前 v1 行为）
  - L2 medium: + 关键工具调用前注入提醒
  - L3 advanced: + 全部工具调用前后核查
  - L4 omni: + 周期性重注入防漂移

### 2. BMad 工作流改进的最佳实践
- **一致性检测应该成为敏捷开发的固定环节**，不是 CI 时才做
- 最佳时机：完成任务后→汇报前→提交前（三步走）
- 避坑指南中强调的教训：「完成任务直接提交跳过一致性检测」是最常见的错误

### 3. 分支策略
- 功能分支命名：`feat/<feature-name>`
- 每个 Sprint 对应一个分支，完成后合并到 master
- 分支起点 commit 包含 Sprint 计划文档

## 可复用模式

```bash
# 启动新迭代的标准流程
1. git checkout -b feat/v2.0-<name>
2. 创建 .hermes/plans/ 下的 Sprint 计划
3. 更新 CHANGELOG.md 和 ROADMAP.md
4. git commit -m "chore(sprint): init <name> iteration"
5. git push origin feat/v2.0-<name>
6. 逐个实现 Story → commit-quality-check → commit
```

## 后续建议

- 下次开始实现 SRA-003-01（Tool 层校验）时，先提交 issue 再实现
- 定期检查 `commit-quality-check` 的 pitfall 列表是否有新补充
