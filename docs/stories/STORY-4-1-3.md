---
story: STORY-4-1-3
title: "SRA Daemon 通信模块 — client.py"
status: completed
created: 2026-05-15
updated: 2026-05-15
spec: SPEC-4-1
epic: EPIC-004
estimated_hours: 1
test_data:
  source: tests/fixtures/skills
  ci_independent: true
  pattern_reference: "skill_advisor/adapters/__init__.py"
spec_references:
  - EPIC-004.md
  - SPEC-4-1.md
  - ~/projects/sra/skill_advisor/adapters/__init__.py
dependencies:
  - STORY-4-1-1
out_of_scope:
  - 格式化 [SRA] 上下文的 UI 逻辑（Phase 1）
  - 工具调用校验逻辑（Phase 2）
  - 轨迹追踪逻辑（Phase 3）
  - 修改 SRA Daemon 端代码
---

# STORY-4-1-3: SRA Daemon 通信模块 — client.py

## 用户故事

> As a **sra-guard 插件**,
> I want **一个可靠的 SRA Daemon 通信客户端**,
> So that **插件可以通过 HTTP 或 Unix Socket 与 SRA Daemon 通信，获取技能推荐和执行校验**。

---

## 验收标准

### AC-1: SraClient.recommend() — 获取推荐
- [x] 条件: 调用 `SraClient.recommend("帮我画架构图")` 
- [x] 验证方式: 启动 mock HTTP 服务器返回模拟响应
- [x] 预期结果: 返回 JSON 中的 `rag_context` 字符串

### AC-2: SraClient.validate() — 工具校验
- [x] 条件: 调用 `SraClient.validate("write_file", {"path": "test.html"})`
- [x] 验证方式: mock HTTP 服务器
- [x] 预期结果: 返回 `{"compliant": bool, "missing": [], "severity": "..."}`

### AC-3: SraClient.record() — 轨迹记录
- [x] 条件: 调用 `SraClient.record("architecture-diagram", "used")`
- [x] 验证方式: mock HTTP 服务器
- [x] 预期结果: 返回 `True`（记录成功）

### AC-4: SraClient.health() — 健康检查
- [x] 条件: 调用 `SraClient.health()`
- [x] 验证方式: mock HTTP 服务器
- [x] 预期结果: SRA 运行时返回 `True`，否则返回 `False`

### AC-5: 超时保护
- [x] 条件: SRA Daemon 响应超过 2 秒
- [x] 验证方式: mock 慢响应服务器
- [x] 预期结果: 超时返回空字符串/False，不抛出异常

### AC-6: HTTP 故障自动降级到 Unix Socket
- [x] 条件: HTTP 连接失败
- [x] 验证方式: 关闭 HTTP 端口，确认 Socket 通路可用
- [x] 预期结果: 自动切换到 `~/.sra/srad.sock`

### AC-7: 所有异常被捕获
- [x] 条件: 网络错误/JSON 解析错误/连接被拒
- [x] 验证方式: 模拟各种异常
- [x] 预期结果: 返回空字符串/False，记录 WARNING 日志，不传播异常

---

## 技术要求

- HTTP 客户端使用 **httpx**（与 Hermes 一致，避免引入 urllib.request）
- Unix Socket 使用标准库 `socket`（无额外依赖）
- 超时默认 2 秒（与 INTEGRATION.md 一致）
- 复用 `skill_advisor/adapters/__init__.py` 中已验证的 Socket 通信模式
- **不引入任何外部依赖**（httpx 已是 Hermes 的依赖）

### 双协议自动降级策略

```python
# 优先级: HTTP (httpx) → Unix Socket
def _request(self, endpoint, payload):
    try:
        return self._http_request(endpoint, payload)
    except (httpx.ConnectError, httpx.TimeoutException):
        logger.debug("HTTP 请求失败，降级到 Socket")
        return self._socket_request(endpoint, payload)
```

### API 设计

```python
class SraClient:
    def __init__(self, http_url="http://127.0.0.1:8536",
                 socket_path="~/.sra/srad.sock",
                 timeout=2.0):
        ...

    def recommend(self, message: str) -> str:
        """POST /recommend → 返回 rag_context 字符串"""
        ...

    def validate(self, tool: str, args: dict,
                 loaded_skills: list = None) -> dict:
        """POST /validate → 返回校验结果"""
        ...

    def record(self, skill: str, action: str) -> bool:
        """POST /record → 返回是否成功"""
        ...

    def health(self) -> bool:
        """GET /health → 返回 SRA 是否可用"""
        ...
```

---

## 实施计划

### Task 1: 创建 client.py
- **文件**: `~/.hermes/hermes-agent/plugins/sra-guard/client.py`
- **操作**: 实现 `SraClient` 类
  - HTTP 通信模块（httpx）
  - Unix Socket 通信模块（socket）
  - 双协议自适应
  - 超时保护
  - 日志记录
- **验证**: `python3 -c "from sra_guard.client import SraClient; c=SraClient(); print(c.health())"`

### Task 2: 集成到 plugin.py
- **文件**: `~/.hermes/hermes-agent/plugins/sra-guard/plugin.py`
- **操作**: 在 `SRAGuardPlugin.__init__` 中实例化 `SraClient`
- **验证**: `python3 -c "from sra_guard import SRAGuardPlugin; print('OK')"`

### Task 3: 编写测试
- **文件**: `~/.hermes/hermes-agent/plugins/sra-guard/tests/test_client.py`
- **操作**: 
  - 启动 mock HTTP 服务器测试各端点
  - 测试超时场景
  - 测试异常降级
- **验证**: `python3 -m pytest tests/test_client.py -v`

---

## 测试策略

- **Fixture**: `tests/fixtures/mock_sra_server.py` — 轻量级 mock SRA HTTP 服务器
- **新测试文件**: `tests/test_client.py`
- **CI 环境**: 完全独立（不依赖真实 SRA Daemon）

---

## 完成检查清单

- [x] 所有 AC 通过
- [x] `SraClient` 支持 HTTP + Socket 双协议
- [x] 超时保护正常工作（2s）
- [x] 异常降级链路验证通过
- [x] 测试覆盖正常/超时/异常场景
- [x] 代码 + 文档同次 commit
