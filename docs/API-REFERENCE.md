# SRA API 参考文档

> **版本:** v1.2.1 | **更新:** 2026-05-10 | **协议:** HTTP REST + Unix Socket
>
> **文档对齐状态:** 已同步 Sprint 2 (SRA-003-03, SRA-003-04, SRA-003-14)

---

## 1. HTTP API

**基础 URL:** `http://localhost:8536`
**Content-Type:** `application/json; charset=utf-8`

### 1.1 健康检查

```
GET /health
```

**响应示例:**
```json
{
  "status": "ok",
  "version": "1.2.1",
  "uptime_seconds": 3600,
  "skills_count": 313,
  "total_requests": 42,
  "total_recommendations": 38,
  "errors": 0,
  "last_refresh": 1715155200.0,
  "config": {
    "http_port": 8536,
    "auto_refresh_interval": 3600,
    "enable_http": true,
    "enable_unix_socket": true
  }
}
```

**状态码:**
| 码 | 含义 |
|:--:|:---|
| 200 | 服务正常 |
| 503 | 服务不可用 |

---

### 1.2 技能推荐

```
POST /recommend
Content-Type: application/json

{
  "message": "画架构图"
}
```

**兼容格式（v1.0 后支持 `query` 字段）:**
```json
{
  "message": "画架构图",
  "top_k": 5
}
```

**响应示例:**
```json
{
  "rag_context": "── [SRA Skill 推荐] ──────────────────────────────\n  ⭐ [medium] architecture-diagram (85.2分) — 同义词'画图'→'diagram'\n     [medium] excalidraw (63.5分) — 同义词'画图'→'excalidraw'\n── ──────────────────────────────────────────────",
  "recommendations": [
    {
      "skill": "architecture-diagram",
      "score": 85.2,
      "confidence": "high",
      "reasons": ["同义词'画图'→'diagram'", "同义词'架构'→'architecture'"],
      "description": "Generate dark-themed SVG diagrams of software systems"
    }
  ],
  "top_skill": "architecture-diagram",
  "should_auto_load": true,
  "timing_ms": 15.3,
  "provider_latency_ms": 15.3,
  "sra_available": true,
  "sra_version": "1.2.1"
}
```

**参数:**
| 字段 | 类型 | 必需 | 默认 | 说明 |
|:---|:---|:---:|:---:|:---|
| `message` | string | ✅ | — | 用户输入（推荐使用） |
| `query` | string | ✅ | — | 兼容 v1.0 字段 |
| `top_k` | int | ❌ | 5 | 返回前 N 个推荐 |

**字段说明（响应）:**
| 字段 | 类型 | 说明 |
|:---|:---|:---|
| `rag_context` | string | 格式化的推荐文本，直接注入 Agent 上下文 |
| `recommendations[]` | array | 推荐列表 |
| `recommendations[].skill` | string | 技能名称 |
| `recommendations[].score` | float | 匹配得分（0-100） |
| `recommendations[].confidence` | string | `high`(≥80) 或 `medium`(≥40) |
| `recommendations[].reasons` | string[] | 匹配原因（最多 3 条） |
| `top_skill` | string|null | 最佳匹配技能名 |
| `should_auto_load` | bool | 得分≥80 时 true |
| `timing_ms` | float | 处理耗时 |

**状态码:**
| 码 | 含义 |
|:--:|:---|
| 200 | 推荐成功（可能无结果） |
| 400 | 缺少 `message` 或 `query` 字段 |

---

### 1.3 记录使用/查看/跳过

```
POST /record
Content-Type: application/json
```

**旧式用法（记录推荐采纳）:**
```json
{
  "skill": "architecture-diagram",
  "input": "画架构图",
  "accepted": true
}
```

**新式用法（Sprint 2 🆕 技能轨迹追踪）:**
```json
{
  "skill": "architecture-diagram",
  "action": "viewed"
}
{
  "skill": "architecture-diagram",
  "action": "used"
}
{
  "skill": "architecture-diagram",
  "action": "skipped",
  "reason": "not relevant"
}
```

**参数:**
| 字段 | 类型 | 必需 | 默认 | 说明 |
|:---|:---|:---:|:---:|:---|
| `skill` | string | ✅ | — | 技能名称 |
| `input` | string | ✅* | — | *旧式用法必需，新式用法忽略 |
| `accepted` | bool | ❌ | true | 是否采纳推荐（旧式用法） |
| `action` | string | ❌ | — | 新式：`viewed`/`used`/`skipped` |
| `reason` | string | ❌ | — | 跳过原因（仅 `skipped`） |

**响应:**
```json
{"status": "ok"}
```
或
```json
{"error": "missing skill or input"}
```

---

### 1.4 刷新索引

```
POST /refresh
```

**响应:**
```json
{"status": "ok", "count": 313}
```

| 字段 | 类型 | 说明 |
|:---|:---|:---|
| `count` | int | 已索引的技能总数 |

---

### 1.5 获取统计

```
GET /stats
```

**响应:**
```json
{
  "version": "1.2.1",
  "status": "running",
  "uptime_seconds": 3600,
  "skills_count": 313,
  "total_requests": 42,
  "total_recommendations": 38,
  "errors": 0,
  "last_refresh": 1715155200.0,
  "config": { ... }
}
```

### 1.6 状态查询

```
GET /status
```

**响应:**
```json
{
  "status": "ok",
  "sra_engine": true,
  "version": "1.2.1",
  "stats": {
    "skills_scanned": 313
  },
  "config": {
    "host": "0.0.0.0",
    "port": 8536,
    "high_threshold": 80,
    "medium_threshold": 40
  }
}
```

---

### 1.7 技能遵循率统计 🆕

```
GET /stats/compliance
```

**响应:**
```json
{
  "status": "ok",
  "compliance": {
    "summary": {
      "total_views": 42,
      "total_uses": 35,
      "total_skips": 7,
      "overall_compliance_rate": 0.83
    },
    "per_skill": {
      "architecture-diagram": {
        "view_count": 5,
        "use_count": 4,
        "skip_count": 1,
        "compliance_rate": 0.8,
        "acceptance_rate": 1.0
      }
    },
    "recent_events": [
      {"skill": "...", "type": "used", "timestamp": "..."}
    ]
  }
}
```

| 字段 | 类型 | 说明 |
|:---|:---|:---|
| `summary.total_views` | int | 总查看次数 |
| `summary.total_uses` | int | 总使用次数 |
| `summary.total_skips` | int | 总跳过次数 |
| `summary.overall_compliance_rate` | float | 整体遵循率 (uses/(uses+skips)) |
| `per_skill` | object | 按技能维度的详细统计 |
| `recent_events` | array | 最近 20 条事件记录 |

---

### 1.8 工具调用校验 🆕

```
POST /validate
Content-Type: application/json

{
  "tool": "write_file",
  "args": {"path": "output.md"},
  "loaded_skills": ["markdown-guide"]
}
```

**参数:**
| 字段 | 类型 | 必需 | 说明 |
|:---|:---|:---:|:---|
| `tool` | string | ✅ | 工具名称（`write_file`/`patch`/`terminal` 等） |
| `args` | object | ✅ | 工具参数 |
| `loaded_skills` | string[] | ❌ | 已加载的技能列表 |

**响应:**
```json
{
  "compliant": false,
  "missing": ["markdown-guide"],
  "severity": "warning",
  "message": "检测到文件类型 `.md`，建议加载 skill: markdown-guide"
}
```

| 字段 | 类型 | 说明 |
|:---|:---|:---|
| `compliant` | bool | 是否合规 |
| `missing` | string[] | 缺失的技能列表 |
| `severity` | string | `info`/`warning`/`block` |
| `message` | string | 人类可读的提示信息 |

---

### 1.9 长任务上下文漂移重检 🆕

```
POST /recheck
Content-Type: application/json

{
  "conversation_summary": "正在配置 Hermes 网关和飞书集成",
  "loaded_skills": ["hermes-agent", "feishu"]
}
```

**参数:**
| 字段 | 类型 | 必需 | 说明 |
|:---|:---|:---:|:---|
| `conversation_summary` | string | ✅ | 当前对话摘要 |
| `loaded_skills` | string[] | ❌ | 已加载的技能列表 |

**响应:**
```json
{
  "status": "ok",
  "recheck": {
    "has_drift": true,
    "drift_score": 0.8,
    "missing_skills": [
      {"skill": "blackbox", "score": 64.2, "confidence": "medium", ...}
    ],
    "recommendations": [...],
    "loaded_skills_count": 2,
    "processing_ms": 56.6
  }
}
```

| 字段 | 类型 | 说明 |
|:---|:---|:---|
| `has_drift` | bool | 是否检测到上下文漂移 |
| `drift_score` | float | 漂移程度 (0-1)，≥0.2 触发告警 |
| `missing_skills` | array | 推荐但未加载的技能列表 |
| `recommendations` | array | 完整推荐结果（同 /recommend） |
| `processing_ms` | float | 处理耗时 |

---

## 2. Unix Socket API

**Socket 路径:** `~/.sra/srad.sock`
**协议:** JSON-over-Socket（单次请求-响应）
**超时:** 5 秒

### 2.1 请求格式

```json
{
  "action": "<action_name>",
  "params": { ... }
}
```

### 2.2 支持的动作

| Action | params | 说明 | Sprint |
|:---|:---|:---|:---:|
| `recommend` | `{query, top_k?}` | 技能推荐 | v1.x |
| `record` | `{skill, action?, input?, accepted?}` | 记录使用/查看/跳过 | Sprint 2 🆕 |
| `refresh` | `{}` | 刷新索引 | v1.x |
| `stats` | `{}` | 获取统计 | v1.x |
| `stats/compliance` | `{}` | 遵循率统计 🆕 | Sprint 2 |
| `coverage` | `{}` | 覆盖率分析 | v1.x |
| `validate` | `{tool, args, loaded_skills?}` | 工具调用校验 🆕 | Sprint 1 |
| `recheck` | `{conversation_summary, loaded_skills?}` | 漂移重检 🆕 | Sprint 2 |
| `ping` | `{}` | 心跳检测 | v1.x |
| `stop` | `{}` | 远程停止守护进程 | v1.x |

### 2.3 示例

```python
import socket, json

client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
client.connect(os.path.expanduser("~/.sra/srad.sock"))
client.sendall(json.dumps({
    "action": "recommend",
    "params": {"query": "画架构图"}
}).encode("utf-8"))
response = client.recv(65536).decode("utf-8")
client.close()
print(json.loads(response))
```

---

## 3. CLI 命令参考

### 3.1 守护进程管理

| 命令 | 说明 | 示例 |
|:---|:---|:---:|
| `sra start` | 启动守护进程（后台） | `sra start` |
| `sra stop` | 停止守护进程 | `sra stop` |
| `sra restart` | 重启守护进程 | `sra restart` |
| `sra status` | 查看运行状态 | `sra status` |
| `sra attach` | 前台运行（调试用） | `sra attach` |

### 3.2 查询命令

| 命令 | 说明 | 示例 |
|:---|:---|:---:|
| `sra recommend <query>` | 技能推荐 | `sra recommend 画架构图` |
| `sra query <query>` | 同 recommend | `sra query 生成PDF` |
| `sra stats` | 查看统计 | `sra stats` |
| `sra coverage` | 覆盖率分析 | `sra coverage` |
| `sra compliance` | 技能遵循率统计 🆕 | `sra compliance` |
| `sra refresh` | 刷新索引 | `sra refresh` |

### 3.3 管理命令

| 命令 | 说明 | 示例 |
|:---|:---|:---:|
| `sra record <skill> <input>` | 记录使用 | `sra record pdf-layout "生成PDF"` |
| `sra config [show\|set\|reset]` | 配置管理 | `sra config set http_port 9000` |
| `sra install <agent>` | 安装到 Agent | `sra install hermes` |
| `sra upgrade [-V <version>]` | 升级 SRA | `sra upgrade -V 1.2.0` |
| `sra uninstall [--all]` | 卸载 SRA | `sra uninstall --all` |
| `sra version` | 版本信息 | `sra version` |
| `sra list-adapters` | 列出 Agent 适配器 | `sra list-adapters` |

### 3.4 降级策略

所有 CLI 命令在 Daemon 未运行时自动降级为本地模式：
```bash
$ sra recommend 画架构图
# 如果 Daemon 未运行:
⚠️  SRA Daemon 未运行，使用本地模式
🔍 查询: '画架构图'
⚡ 15.3ms | 📊 313 skills
🎯 推荐技能:
  ✅ architecture-diagram (得分: 85.2)
```
`compliance`、`coverage`、`stats`、`refresh`、`record` 等命令同样支持降级。

---

## 4. Python API（程序内调用）

### 4.1 SkillAdvisor

```python
from skill_advisor import SkillAdvisor

advisor = SkillAdvisor(
    skills_dir="~/.hermes/skills",    # 技能目录
    data_dir="~/.sra/data",           # 数据持久化目录
)

# 构建索引
advisor.refresh_index() -> int

# 推荐技能
advisor.recommend(query: str, top_k: int = 3) -> Dict

# 记录使用
advisor.record_usage(skill_name: str, user_input: str, accepted: bool = True)
# 🆕 记录查看/使用/跳过
advisor.record_view(skill_name: str)
advisor.record_use(skill_name: str)
advisor.record_skip(skill_name: str, reason: str = "")

# 🆕 长任务漂移重检
advisor.recheck(conversation_summary: str, loaded_skills: List[str] = None, top_k: int = 5) -> Dict

# 获取统计
advisor.show_stats() -> Dict

# 🆕 遵循率统计
advisor.get_compliance_stats() -> Dict

# 覆盖率分析
advisor.analyze_coverage() -> Dict
```

### 4.2 SRaDDaemon

```python
from skill_advisor import SRaDDaemon

daemon = SRaDDaemon(config: dict = None)
daemon.start()      # 启动守护进程（后台线程）
daemon.attach()     # 前台运行（调试用）
daemon.stop()       # 停止守护进程
daemon.get_stats() -> Dict
```

---

## 5. 内部模块 API

### 5.1 SkillIndexer (`indexer.py`)

```python
indexer = SkillIndexer(skills_dir: str, data_dir: str)
indexer.build() -> int                           # 扫描并构建索引
indexer.load_or_build() -> List[Dict]             # 加载缓存或构建
indexer.get_skills() -> List[Dict]                # 获取技能列表
indexer.extract_keywords(text: str) -> Set[str]   # 中英文关键词提取
indexer.expand_with_synonyms(words: Set) -> Set   # 同义词扩展
```

### 5.2 SkillMatcher (`matcher.py`)

```python
matcher = SkillMatcher(synonyms: Dict)
matcher.score(input_words: Set, skill: Dict, stats: Dict) -> Tuple[float, Dict, List[str]]
# 返回: (总分, {lexical, semantic, scene, category}, 匹配原因列表)
```

### 5.3 SceneMemory (`memory.py`)

```python
memory = SceneMemory(data_dir: str)
memory.load() -> Dict                               # 加载场景记忆
memory.save()                                       # 持久化

# 旧式 API（推荐采纳）
memory.record_usage(skill, input, accepted)          # 记录使用

# 🆕 新式 API（技能轨迹追踪）
memory.record_view(skill_name: str)                  # 记录技能被查看
memory.record_use(skill_name: str)                   # 记录技能被使用
memory.record_skip(skill_name: str, reason: str = "") # 记录技能被跳过

# 🆕 遵循率
memory.get_compliance_stats() -> Dict                # 获取遵循率统计

# 基础操作
memory.increment_recommendations()                   # 增加推荐计数
memory.get_skill_stats(name) -> Dict                 # 获取技能统计
```

---

## 6. 错误码大全

### 6.1 HTTP 状态码

| 码 | 含义 | 触发场景 |
|:--:|:---|:---|
| 200 | 成功 | 正常响应 |
| 400 | 参数错误 | 缺少 `message`/`query`、参数格式错误、未知 action |
| 404 | 端点不存在 | 访问未知路径 |
| 500 | 服务器内部错误 | 未捕获的异常 |
| 503 | 服务不可用 | 守护进程未启动 |

### 6.2 Socket 错误响应

```json
{"error": "invalid_json"}
{"error": "SRA Daemon 未运行", "suggestion": "请先运行 'sra start'"}
{"error": "unknown action: xxx"}
{"error": "missing conversation_summary"}
{"error": "unknown action type: xxx"}
```

---

> **本文件是 SRA 的完整 API 参考。所有端点和参数以实际代码为准。**
> **文档对齐协议：** 每次代码变更后需运行 `skill_view(name="doc-alignment")` 同步此文档。
