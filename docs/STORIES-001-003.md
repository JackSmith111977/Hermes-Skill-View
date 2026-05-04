# Story 1: Hermes run_agent.py 注入 — 消息前置推理（已实现 ✅）

> **Story ID:** SRA-001
> **关联 Epic:** SRA-EPIC-001
> **状态:** ✅ **已实现 (v1.1.0)**
> **估算:** 2小时（实际 ~1小时）

## 用户故事

作为 Hermes Agent 用户，我希望每次发消息时 SRA 自动推荐技能——**不需要在 AGENTS.md 或 SOUL.md 中写规则劝告模型**，而是代码层强制拦截每轮消息，100% 确保模型感知到技能推荐。

## 验收状态

- [x] 在 `run_agent.py` 中新增 `_query_sra_context()` 函数
- [x] 在 `run_conversation()` 方法中注入 SRA 调用点
- [x] 每次消息自动调 SRA Daemon (`POST :8536/recommend`)
- [x] rag_context 注入到 user_message 前（作为 `[SRA]` 前缀）
- [x] should_auto_load≥80 时在上下文标记建议加载的 skill
- [x] SRA Daemon 不可用时优雅降级（静默，不阻塞）
- [x] 回复开头看到 `[SRA]` 推荐标记
- [x] 模块级缓存（MD5 hash）避免相同消息重复调 SRA
- [x] 2 秒超时保护

## 技术方案（实际实现）

### `_query_sra_context()` 函数

在 `run_agent.py` 的 `class AIAgent` 定义前插入：

```python
_SRA_CACHE: dict = {}

def _query_sra_context(user_message: str) -> str:
    """每次消息自动调 SRA Daemon 获取技能推荐。"""
    import urllib.request
    import json as _json
    import hashlib
    
    sra_url = os.environ.get("SRA_PROXY_URL", "http://127.0.0.1:8536")
    
    # 模块级缓存（MD5 hash）
    _msg_hash = hashlib.md5(user_message.encode("utf-8")).hexdigest()[:12]
    _cached = _SRA_CACHE.get("last_hash")
    if _cached == _msg_hash:
        return _SRA_CACHE.get("last_result", "")
    
    try:
        req = urllib.request.Request(f"{sra_url}/recommend", method="POST")
        payload = _json.dumps({"message": user_message}).encode("utf-8")
        req.data = payload
        req.add_header("Content-Type", "application/json")
        
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
        
        rag_context = data.get("rag_context", "")
        should_auto_load = data.get("should_auto_load", False)
        top_skill = data.get("top_skill")
        
        if not rag_context:
            _SRA_CACHE["last_hash"] = _msg_hash
            _SRA_CACHE["last_result"] = ""
            return ""
        
        lines = ["[SRA] Skill Runtime Advisor 推荐:"]
        lines.append(rag_context)
        if should_auto_load and top_skill:
            lines.append(f"[SRA] ⚡ 建议自动加载: {top_skill}")
        
        result = "\n".join(lines)
        if len(result) > 2500:
            result = result[:2497] + "..."
        
        _SRA_CACHE["last_hash"] = _msg_hash
        _SRA_CACHE["last_result"] = result
        return result
    
    except Exception:
        _SRA_CACHE["last_hash"] = _msg_hash
        _SRA_CACHE["last_result"] = ""
        return ""
```

### `run_conversation()` 中的注入点

```python
def run_conversation(self, user_message, ...):
    ...
    # ── SRA Context Injection ─────────────────
    _sra_ctx = _query_sra_context(user_message)
    if _sra_ctx:
        user_message = f"{_sra_ctx}\n\n{user_message}"
    # ──────────────────────────────────────────
    
    # Add user message
    self.messages.append({"role": "user", "content": user_message})
    ...
```

### 为什么不是 Hook 方案？

Hermes 的 `gateway/hooks.py` 第 170 行注释：
```python
# errors are caught and logged but never block
```
Hook 系统是异步非阻塞的，可以"看到"消息但无法修改上下文。注入 `run_agent.py` 是唯一能 100% 确保每轮消息触发 SRA 的方案。

---

# Story 2: 补丁 + 安装脚本 + 测试（已实现 ✅）

> **Story ID:** SRA-002
> **关联 Epic:** SRA-EPIC-001
> **状态:** ✅ **已实现 (v1.1.0)**

## 验收状态

- [x] 创建 `patches/hermes-sra-integration.patch` — V4A 格式补丁
- [x] 创建 `scripts/install-hermes-integration.sh` — 一键安装/卸载脚本
- [x] 脚本支持备份恢复
- [x] 脚本支持 SRA Daemon 运行状态检测
- [x] 测试验证：38/38 全部通过

## 安装脚本使用

```bash
# 安装
bash scripts/install-hermes-integration.sh

# 卸载
bash scripts/install-hermes-integration.sh --uninstall

# 帮助
bash scripts/install-hermes-integration.sh --help
```

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `HERMES_HOME` | `~/.hermes` | Hermes Agent 家目录 |
| `SRA_PROXY_URL` | `http://127.0.0.1:8536` | SRA Daemon 地址 |

---

# Story 3: 文档更新（已实现 ✅）

> **Story ID:** SRA-003
> **关联 Epic:** SRA-EPIC-001
> **状态:** ✅ **已实现 (v1.1.0)**

## 验收状态

- [x] 更新 README.md — 新增"Hermes 原生集成"章节
- [x] 更新 INTEGRATION.md — 重写为 v1.1.0 集成方案（非旧版 Hook 方案）
- [x] 更新 EPIC-001 — 标记为已实现，更新架构为实际方案
- [x] 更新 STORIES-001-003 — 标记为已实现，更新技术细节
