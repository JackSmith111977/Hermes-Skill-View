"""
SRA 上下文格式化工具 — 将 rag_context 格式化为 [SRA] 前缀文本

格式:
    [SRA] Skill Runtime Advisor 推荐:
    ── [SRA Skill 推荐] ──────────────────────────────
      ⭐ [medium] skill-name (42.5分) — reason1
         [medium] skill-name2 (40.0分) — reason1
    ── ──────────────────────────────────────────────
    ⚡ 建议自动加载: skill-name    # 仅 when should_auto_load=True

与 SRA Daemon 的 POST /recommend 响应格式一致。
"""

from __future__ import annotations

from typing import Optional

# 最大上下文长度（与旧补丁方案一致）
MAX_CONTEXT_LENGTH = 2500


def format_sra_context(
    rag_context: str,
    top_skill: Optional[str] = None,
    should_auto_load: bool = False,
) -> str:
    """将 rag_context 格式化为带 [SRA] 前缀的可读文本。

    Args:
        rag_context: SRA Daemon 返回的原始上下文文本
        top_skill: 最高分 skill 名称
        should_auto_load: 是否强推荐自动加载

    Returns:
        格式化后的字符串。rag_context 为空时返回空字符串。
    """
    if not rag_context or not rag_context.strip():
        return ""

    lines = ["[SRA] Skill Runtime Advisor 推荐:"]
    lines.append(rag_context)

    if should_auto_load and top_skill:
        lines.append(f"[SRA] ⚡ 建议自动加载: {top_skill}")

    result = "\n".join(lines)

    if len(result) > MAX_CONTEXT_LENGTH:
        result = result[: MAX_CONTEXT_LENGTH - 3] + "..."

    return result
