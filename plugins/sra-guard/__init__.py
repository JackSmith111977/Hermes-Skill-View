"""
SRA Guard — Hermes 插件：实时技能推荐与工具校验

在 Hermes 的 pre_llm_call 钩子中注入 SRA 技能推荐上下文，
在 pre_tool_call 钩子中校验工具调用前是否已加载对应技能。

架构:
  - register(ctx): Hermes 插件系统自动调用的注册入口
  - _on_pre_llm_call(): pre_llm_call hook 回调（Phase 1）
  - _on_pre_tool_call(): pre_tool_call hook 回调（Phase 2）
  - SraClient: SRA Daemon 通信模块
  - _SRA_CACHE: 消息去重缓存

依赖:
  - SRA Daemon (http://127.0.0.1:8536 或 ~/.sra/srad.sock)
"""

from __future__ import annotations

import hashlib
import importlib.util
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional, Set, Union

logger = logging.getLogger("sra-guard")

# ── 全局状态 ──────────────────────────────────────────────
_client: Any = None  # SraClient 实例，延迟初始化
_SRA_CACHE: Dict[str, str] = {}  # msg_md5 → formatted_context
_last_record_time: Dict[str, float] = {}  # tool_name → timestamp（去重）
_turn_counter: int = 0  # 对话轮数计数器（Phase 4 重注入）
RECHECK_INTERVAL: int = 5  # 每 N 轮强制重查 SRA

# ── Force Level ───────────────────────────────────────────
# 与 SRA Daemon 的 force.py 定义对齐
DEFAULT_FORCE_LEVEL = "medium"

# pre_tool_call 监控的工具集合
KEY_TOOLS = {"write_file", "patch", "terminal", "execute_code"}

FORCE_TOOL_MAP: Dict[str, Union[Set[str], str]] = {
    "basic":    set(),       # 不监控任何工具
    "medium":   KEY_TOOLS,   # 仅监控关键工具
    "advanced": "__all__",   # 监控全部工具
    "omni":     "__all__",   # 监控全部工具
}

# ── 轨迹追踪 ──────────────────────────────────────────────
# 技能相关工具 — 记录为 action="viewed"
SKILL_TOOLS: Set[str] = {"skill_view", "skills_list", "skill_manage"}

# 内部工具 — 不记录
IGNORE_TOOLS: Set[str] = {"todo", "memory", "session_search", "delegate_task"}

# 去重间隔（秒）
DEDUP_INTERVAL = 2.0


def _should_validate(tool_name: str, force_level: str = DEFAULT_FORCE_LEVEL) -> bool:
    """根据力度级别判断是否需要对指定工具进行校验

    Args:
        tool_name: 工具名称
        force_level: 力度级别 (basic/medium/advanced/omni)

    Returns:
        是否需要校验
    """
    monitored = FORCE_TOOL_MAP.get(force_level, KEY_TOOLS)
    if monitored == "__all__":
        return True
    return tool_name in monitored


# ── 缓存 ──────────────────────────────────────────────────

def _cache_key(message: str) -> str:
    """生成消息的缓存 key（MD5 前 12 位）"""
    return hashlib.md5(message.encode("utf-8")).hexdigest()[:12]


def _get_cached(message: str) -> str:
    """从缓存获取格式化上下文"""
    return _SRA_CACHE.get(_cache_key(message), "")


def _set_cached(message: str, context: str) -> None:
    """写入缓存"""
    _SRA_CACHE[_cache_key(message)] = context


# ── 格式化 ──────────────────────────────────────────────────

def _format_context(rag_context: str, top_skill: str = "", should_auto_load: bool = False) -> str:
    """将 SRA 返回的 rag_context 格式化为 [SRA] 前缀文本"""
    try:
        formatter_path = Path(__file__).parent / "formatter.py"
        spec = importlib.util.spec_from_file_location(
            "sra_guard.formatter", str(formatter_path)
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.format_sra_context(rag_context, top_skill, should_auto_load)
    except Exception as exc:
        logger.warning("格式化失败，返回原始上下文: %s", exc)
        return rag_context


# ── Client ──────────────────────────────────────────────────

def _get_client():
    """获取 SraClient 实例（延迟初始化）

    由于插件目录名含连字符（sra-guard），不能用标准 import，
    使用 importlib 从文件路径加载 client 模块。
    """
    global _client
    if _client is None:
        try:
            client_path = Path(__file__).parent / "client.py"
            spec = importlib.util.spec_from_file_location(
                "sra_guard.client", str(client_path)
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _client = mod.SraClient()
        except Exception as exc:
            logger.warning("SraClient 初始化失败: %s", exc)
            _client = None
    return _client


# ── Hook 回调: pre_llm_call ───────────────────────────────

def _on_pre_llm_call(messages, session_id, **kwargs):
    """pre_llm_call hook 回调 — 在 LLM 调用前注入 SRA 推荐。

    流程:
      1. 提取最后一条 user message
      2. 检查缓存（MD5 hash）
      3. 缓存命中 → 直接返回缓存结果
      4. 缓存未命中 → 调 SRA /recommend → 格式化 → 更新缓存
      5. 异常时静默降级，不阻塞 Hermes

    Args:
        messages: 当前对话消息列表
        session_id: 当前会话 ID
        **kwargs: 其他参数（由 Hermes 传递）

    Returns:
        dict | None: {"context": str} 或 None
    """
    try:
        global _turn_counter
        if not messages or not isinstance(messages, list):
            return None
        last = messages[-1]
        if not isinstance(last, dict):
            return None
        if last.get("role") != "user":
            return None
        text = last.get("content", "")
        if not text or not isinstance(text, str):
            return None

        # 递增轮数计数器（每次 pre_llm_call 都 +1）
        _turn_counter += 1

        # 检查缓存
        cached = _get_cached(text)
        if cached:
            # Phase 4: 达到重查间隔时清除缓存 → 强制走 SRA
            if _turn_counter >= RECHECK_INTERVAL:
                _turn_counter = 0
                _SRA_CACHE.pop(_cache_key(text), None)  # 清除当前消息缓存
                logger.debug("SRA 缓存已清除，准备重查")
            else:
                logger.debug("SRA 缓存命中")
                return {"context": cached}

        client = _get_client()
        if client is None:
            _turn_counter = 0  # 重置计数器
            return None

        rag_context = client.recommend(text)
        if not rag_context:
            _turn_counter = 0  # 重置计数器
            return None

        # 格式化
        formatted = _format_context(rag_context)

        # 更新缓存
        _set_cached(text, formatted)

        _turn_counter = 0  # 重置计数器

        return {"context": formatted}
    except Exception:
        logger.warning("SRA pre_llm_call 异常", exc_info=True)
    return None


# ── Hook 回调: pre_tool_call ─────────────────────────────

def _on_pre_tool_call(tool_name, args, task_id="", session_id="", tool_call_id="", **kwargs):
    """pre_tool_call hook 回调 — 在工具调用前校验技能加载。

    流程:
      1. 根据 force level 决定是否校验
      2. 调 SRA /validate
      3. severity=block → 阻断工具
      4. warning/info → 放行
      5. 异常/不可用 → 放行（优雅降级）

    Args:
        tool_name: 工具名称 (write_file, patch, terminal, ...)
        args: 工具参数字典
        task_id: 任务 ID
        session_id: 会话 ID
        tool_call_id: 工具调用 ID
        **kwargs: 其他参数

    Returns:
        None（放行）或 {"action": "block", "message": "..."}（阻断）
    """
    try:
        # Force level 检查
        if not _should_validate(tool_name):
            return None

        # 确保 args 是 dict
        if not isinstance(args, dict):
            args = {}

        client = _get_client()
        if client is None:
            return None

        result = client.validate(tool_name, args, loaded_skills=[])
        if not result:
            return None

        # compliant → 放行
        if result.get("compliant", True):
            return None

        # 根据 severity 决定是否阻断
        severity = result.get("severity", "info")
        if severity == "block":
            message = result.get("message", f"工具 '{tool_name}' 缺少对应技能")
            logger.info("SRA 阻断工具: %s — %s", tool_name, message)
            return {"action": "block", "message": message}

        # warning/info → 放行（仅记录）
        if severity == "warning":
            logger.info("SRA 警告: %s — %s", tool_name, result.get("message", ""))

        return None
    except Exception:
        logger.warning("SRA pre_tool_call 异常", exc_info=True)
    return None


# ── Hook 回调: post_tool_call ─────────────────────────────

def _on_post_tool_call(
    tool_name,
    args=None,
    result="",
    task_id="",
    session_id="",
    tool_call_id="",
    duration_ms=0,
    **kwargs,
):
    """post_tool_call hook 回调 — 在工具调用后记录轨迹到 SRA。

    流程:
      1. skill_view/skills_list/skill_manage → action="viewed"
      2. 内部工具 (todo/memory/...) → 忽略（不记录）
      3. 其他工具 → action="used"
      4. 同工具 2s 内去重防刷屏
      5. 异常时静默降级

    Args:
        tool_name: 工具名称
        args: 工具参数
        result: 工具执行结果
        task_id: 任务 ID
        session_id: 会话 ID
        tool_call_id: 工具调用 ID
        duration_ms: 执行耗时（毫秒）
        **kwargs: 其他参数

    Returns:
        None（观察性 hook，返回值被框架忽略）
    """
    try:
        client = _get_client()
        if client is None:
            return None

        if not isinstance(tool_name, str):
            return None

        # 技能工具 → action="viewed"
        if tool_name in SKILL_TOOLS:
            skill_name = ""
            if isinstance(args, dict):
                skill_name = args.get("name", "")
            client.record(skill=skill_name, action="viewed")
            return None

        # 内部工具 → 忽略
        if tool_name in IGNORE_TOOLS:
            return None

        # 常规工具 → 去重检查
        now = time.time()
        last = _last_record_time.get(tool_name, 0.0)
        if now - last < DEDUP_INTERVAL:
            return None
        _last_record_time[tool_name] = now

        # 记录 used
        client.record(skill="", action="used")
        return None
    except Exception:
        logger.warning("SRA post_tool_call 异常", exc_info=True)
    return None


# ── 插件注册入口 ──────────────────────────────────────────

def register(ctx) -> None:
    """Hermes 插件系统自动调用的注册入口。

    参数 ``ctx`` 是 PluginRegistrationContext 实例，提供：
      - register_hook(name, callback)
      - register_command(name, handler, description)
    """
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
    ctx.register_hook("pre_tool_call", _on_pre_tool_call)
    ctx.register_hook("post_tool_call", _on_post_tool_call)
    logger.info("sra-guard 插件已注册 (v0.2.0) — pre_llm_call + pre_tool_call + post_tool_call")
