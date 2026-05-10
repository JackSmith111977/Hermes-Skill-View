# SRA 架构标准

> **版本:** v1.0 | **更新:** 2026-05-10 | **适用:** SRA v1.x → v2.x

---

## 1. 架构总览

### 1.1 三层架构

```
┌─────────────────────────────────────────────────────┐
│  Layer 3: 用户接口层 (Interface Layer)               │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │  CLI     │  │  HTTP    │  │  Unix Socket     │  │
│  │  (sra)   │  │  (8536)  │  │  (~/.sra/)      │  │
│  └────┬─────┘  └────┬─────┘  └────────┬─────────┘  │
│       │             │                 │            │
├───────┼─────────────┼─────────────────┼────────────┤
│  Layer 2: 业务逻辑层 (Service Layer)                │
│       │             │                 │            │
│  ┌────┴─────────────┴─────────────────┴─────────┐  │
│  │           SRaDDaemon (daemon.py)              │  │
│  │  ┌─────────────────────────────────────────┐  │  │
│  │  │        SkillAdvisor (advisor.py)        │  │  │
│  │  ├──────────────────┬──────────────────────┤  │  │
│  │  │ SkillMatcher     │ SkillIndexer         │  │  │
│  │  │ (matcher.py)     │ (indexer.py)         │  │  │
│  │  ├──────────────────┼──────────────────────┤  │  │
│  │  │ SceneMemory      │ Synonyms             │  │  │
│  │  │ (memory.py)      │ (synonyms.py)        │  │  │
│  │  └──────────────────┴──────────────────────┘  │  │
│  └────────────────────────────────────────────────┘  │
│                                                     │
├─────────────────────────────────────────────────────┤
│  Layer 1: 数据层 (Data Layer)                        │
│  ┌──────────────┐  ┌──────────────┐                 │
│  │ 技能文件系统  │  │ 持久化数据   │                 │
│  │ ~/.hermes/   │  │ ~/.sra/      │                 │
│  │ skills/      │  │ data/        │                 │
│  └──────────────┘  └──────────────┘                 │
└─────────────────────────────────────────────────────┘
```

### 1.2 核心原则 (API)

| 原则 | 说明 | 违反示例 |
|:---|:---|:---:|
| **单向依赖** | 上层依赖下层，下层不依赖上层 | `daemon.py` import CLI 函数 → ❌ |
| **接口隔离** | 不暴露内部实现细节 | `_handle_request()` 被外部直接调用 → ❌ |
| **单一职责** | 一个模块只做一件事 | `daemon.py` 同时包含守护进程 + CLI 命令 → ❌ |
| **显式优于隐式** | 配置显式化、异常不静默 | `except: pass` → ❌ |

---

## 2. 分层职责

### 2.1 Layer 3 — 接口层

| 模块 | 文件 | 职责 | 约束 |
|:---|:---|:---|:---|
| CLI | `cli.py` | 用户命令行交互、命令解析、参数校验 | ❌ 不直接调业务逻辑（通过 Socket/HTTP） |
| HTTP Server | `daemon.py::_run_http_server` | HTTP API 端点暴露 | ❌ 不做推荐/匹配计算 |
| Socket Server | `daemon.py::_run_socket_server` | Unix Socket API 端点暴露 | ❌ 不做推荐/匹配计算 |

**标准：**
- 接口层只做：输入解析、参数校验、响应格式化
- 所有业务逻辑委托给 Service 层
- 接口层异常不吞没，以标准错误格式返回

### 2.2 Layer 2 — 业务逻辑层

| 模块 | 文件 | 职责 | 对外暴露 |
|:---|:---|:---|:---|
| SkillAdvisor | `advisor.py` | 推荐引擎主入口 | `recommend()`, `record_usage()`, `analyze_coverage()` |
| SkillMatcher | `matcher.py` | 四维匹配引擎 | `score()` |
| SkillIndexer | `indexer.py` | 技能扫描/索引构建 | `build()`, `load_or_build()`, `get_skills()`, `extract_keywords()` |
| SceneMemory | `memory.py` | 场景记忆/使用统计 | `load()`, `save()`, `record_usage()` |
| Synonyms | `synonyms.py` | 同义词映射表 | `SYNONYMS`, `REVERSE_INDEX` |

**标准：**
- 业务模块可独立测试（不依赖 daemon / CLI）
- 模块间通过构造函数注入依赖（显式依赖）
- 业务异常使用自定义异常类

### 2.3 Layer 1 — 数据层

| 类型 | 路径 | 格式 |
|:---|:---|:---|
| 技能文件 | `~/.hermes/skills/**/SKILL.md` | YAML frontmatter + Markdown |
| 索引缓存 | `~/.sra/data/skill_full_index.json` | JSON |
| 场景记忆 | `~/.sra/data/skill_usage_stats.json` | JSON |
| 配置 | `~/.sra/config.json` | JSON |
| 状态 | `~/.sra/srad.status.json` | JSON |
| PID 文件 | `~/.sra/srad.pid` | 纯文本 |
| Lock 文件 | `~/.sra/srad.lock` | 二进制（fcntl） |
| Unix Socket | `~/.sra/srad.sock` | 二进制 |
| 日志 | `~/.sra/srad.log` | 文本 |

---

## 3. 模块边界与通信

### 3.1 进程间通信

| 协议 | 用途 | 端口/路径 | 序列化 |
|:---|:---|:---|:---|
| HTTP REST | 外部集成（Hermes Proxy、健康检查） | `http://0.0.0.0:8536` | JSON |
| Unix Socket | 本地 CLI ↔ Daemon 通信 | `~/.sra/srad.sock` | JSON |

### 3.2 进程内通信

| 调用方向 | 方式 | 示例 |
|:---|:---|:---|
| Daemon → Advisor | 直接方法调用 | `self.advisor.recommend(query)` |
| Advisor → Matcher | 方法调用 | `self.matcher.score(input_words, skill, stats)` |
| Advisor → Indexer | 方法调用 | `self.indexer.get_skills()` |
| Advisor → Memory | 方法调用 | `self.memory.load()` |

### 3.3 路由统一（v2.0 目标）

```python
# 统一路由表 — 所有端点在此注册
ROUTER = {
    "recommend": {"handler": "advisor.recommend", "methods": ["POST", "GET"]},
    "record":    {"handler": "advisor.record_usage", "methods": ["POST"]},
    "refresh":   {"handler": "advisor.refresh_index", "methods": ["POST"]},
    "stats":     {"handler": "daemon.get_stats", "methods": ["GET"]},
    "health":    {"handler": "lambda: {"status": "ok"}", "methods": ["GET"]},
    "coverage":  {"handler": "advisor.analyze_coverage", "methods": ["GET"]},
}
```

---

## 4. 设计模式约定

### 4.1 已使用的模式

| 模式 | 位置 | 说明 |
|:---|:---|:---|
| **Singleton (单例)** | daemon.py (目标 SRA-003-12) | 确保一个进程只有一个 Daemon 实例 |
| **Facade (外观)** | advisor.py | SkillAdvisor 封装 Indexer/Matcher/Memory 的复杂交互 |
| **Strategy (策略)** | matcher.py | 四维评分（词法/语义/场景/类别）各自独立 |
| **Adapter (适配器)** | adapters/__init__.py | 适配不同 AI Agent 的 skill 接口 |
| **Proxy (代理)** | daemon.py::_socket_request | CLI 通过 Socket 代理调用 Daemon |

### 4.2 禁止的反模式

| 反模式 | 现状 | 目标 |
|:---|:---|:---|
| **God Object (上帝对象)** | `daemon.py` 789 行包含守护+CLI | 拆分 CLI 到 cli.py |
| **Swallowing Exception (吞异常)** | 16 处 `except: pass` | 全部消除（SRA-003-13） |
| **Magic Numbers (魔法数字)** | matcher.py 14 个硬编码分值 | 命名常量（SRA-003-15） |
| **Copy-Paste Routing (复制路由)** | Socket + HTTP 两套路由 | 统一路由表（SRA-003-16） |

---

## 5. 错误处理规范

### 5.1 异常层级

```python
class SRAError(Exception):          # 所有 SRA 异常的基类
class ConfigError(SRAError):        # 配置相关错误
class IndexError(SRAError):         # 索引相关错误
class DaemonError(SRAError):        # 守护进程相关错误
class APIError(SRAError):           # API 请求错误
```

### 5.2 异常处理铁律

| 级别 | 规则 | 示例 |
|:---|:---|:---|
| 🔴 CRITICAL | 必须传播，不可捕获 | 配置加载失败、端口绑定失败 |
| 🟡 WARNING | 需要记录，但不中断流程 | YAML 解析单个 skill 失败 |
| 🟢 INFO | 静默处理，记录到 DEBUG | socket.timeout、文件不存在 |

### 5.3 禁止

```python
# ❌ 禁止：完全静默
except:
    pass

# ✅ 应该：至少记录
except Exception as e:
    logger.warning("操作失败: %s", e)

# ✅ 更好：区分异常类型
except FileNotFoundError:
    logger.debug("文件不存在，跳过")
except YAMLError as e:
    logger.error("YAML 解析错误: %s", e)
    raise
```

---

## 6. 配置规范

### 6.1 配置层级

```yaml
# 优先级：命令行参数 > 环境变量 > 用户配置 > 默认配置
1. 默认值: DEFAULT_CONFIG (代码硬编码)
2. 用户配置: ~/.sra/config.json
3. 环境变量: SRA_HTTP_PORT, SRA_LOG_LEVEL, SRA_SKILLS_DIR
4. 命令行: sra start --port 9000
```

### 6.2 配置 Schema 定义

```json
{
  "skills_dir": {"type": "string", "default": "~/.hermes/skills"},
  "http_port": {"type": "integer", "default": 8536, "min": 1024, "max": 65535},
  "log_level": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR"], "default": "INFO"},
  "enable_http": {"type": "boolean", "default": true},
  "enable_unix_socket": {"type": "boolean", "default": true},
  "watch_skills_dir": {"type": "boolean", "default": true},
  "auto_refresh_interval": {"type": "integer", "default": 3600, "min": 60}
}
```

---

## 7. 并发与安全

| 资源 | 保护方式 | 状态 |
|:---|:---|:---:|
| HTTP 端口 | `SO_REUSEADDR` + 端口活性探测 | 🟡 需加固 (SRA-003-12) |
| PID 文件 | `fcntl.flock` OS 级锁 | ❌ 缺失 (SRA-003-12) |
| stats 计数器 | `threading.Lock` | ✅ 已部分实现 |
| status 文件写 | `threading.Lock` | ❌ 缺失 (SRA-003-16) |
| memory 文件写 | `fcntl.flock` | ❌ 缺失 (SRA-003-16) |

---

## 8. 模块演化规则

### 8.1 开发流程铁律

任何代码变更必须按以下顺序进行，**不可跳过、不可重排**：

```
① 实现代码 + 测试
    ↓
② 全量测试验证：pytest tests/ -v
    ↓
③ 🔴 加载 commit-quality-check → 执行完整质量检查
    ↓
④ 修复检查发现的问题
    ↓
⑤ 再次全量测试验证
    ↓
⑥ git add + git commit + git push
    ↓
⑦ 向主人汇报结果（含质量检查报告）
```

**🚨 铁律：完成任何产生文件变更的任务后，必须先跑 commit-quality-check 才能提交或汇报。**

### 8.2 添加新模块

1. 在 `skill_advisor/` 下创建 `.py` 文件
2. 在 `__init__.py` 中导出
3. 在 `ROUTER` 中注册 API 端点
4. 添加对应的 `tests/test_<module>.py`
5. 更新 `docs/API-REFERENCE.md`

### 8.2 修改现有模块

1. 保持向后兼容（新参数加默认值）
2. 废弃的 API 标记 `@deprecated` + 保留一个版本
3. 同步更新所有文档
4. 测试覆盖率不得低于修改前

### 8.3 禁止行为

- ❌ 修改 `__init__.py` 中导出的 `__all__` 不通知
- ❌ 删除公开 API 不经过弃用周期
- ❌ 引入新依赖不更新 `pyproject.toml`
- ❌ 模块间循环依赖

---

> **本文件是 SRA 项目的架构宪法。任何架构变更必须先更新此文件，再改代码。**
