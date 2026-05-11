"""
SRA Agent 适配器 — 让 SRA 能接入任何 AI Agent 系统

适配器将 SRA 的推荐结果转换成特定 Agent 能理解的格式。
每种 Agent 一个适配器类，统一接口。

支持的 Agent:
  - Hermes Agent (原生)
  - Claude Code (Anthropic CLI)
  - OpenAI Codex CLI
  - OpenCode CLI
  - 通用 OpenAI API 格式
"""

import json
import os
import socket
import sys
from typing import Dict, List

# ── Socket 客户端 ───────────────────────────

SOCKET_FILE = os.path.expanduser("~/.sra/srad.sock")


def _sra_socket_request(request: dict, timeout: float = 5.0) -> dict:
    """通过 Unix Socket 向 SRA Daemon 发送请求"""
    if not os.path.exists(SOCKET_FILE):
        return {"error": "SRA Daemon 未运行", "suggestion": "请先运行 'sra start'"}

    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.settimeout(timeout)
        client.connect(SOCKET_FILE)
        client.sendall(json.dumps(request).encode("utf-8"))
        response = client.recv(65536).decode("utf-8")
        client.close()
        return json.loads(response)
    except socket.timeout:
        return {"error": "SRA Daemon 超时"}
    except ConnectionRefusedError:
        return {"error": "SRA Daemon 连接被拒", "suggestion": "请检查 'sra status'"}
    except Exception as e:
        return {"error": str(e)}


# ── 基础适配器接口 ─────────────────────────

class BaseAdapter:
    """所有 Agent 适配器的基类"""

    def __init__(self, socket_path: str = SOCKET_FILE):
        self.socket_path = socket_path

    def recommend(self, query: str, top_k: int = 3) -> List[Dict]:
        """推荐技能 — 所有适配器共享的核心逻辑"""
        result = _sra_socket_request({
            "action": "recommend",
            "params": {"query": query, "top_k": top_k},
        })
        if "error" in result:
            return []
        return result.get("result", {}).get("recommendations", [])

    def format_suggestion(self, recommendations: List[Dict]) -> str:
        """将推荐结果格式化为该 Agent 的提示文本"""
        raise NotImplementedError

    def ping(self) -> bool:
        """检查 SRA Daemon 是否运行"""
        result = _sra_socket_request({"action": "ping"})
        return result.get("pong", False) and result.get("status") == "ok"


# ── Hermes Agent 适配器 ─────────────────────

class HermesAdapter(BaseAdapter):
    """Hermes Agent 适配器 — 生成 <available_skills> 增强块"""

    def format_suggestion(self, recommendations: List[Dict]) -> str:
        if not recommendations:
            return ""

        lines = ["💡 SRA 技能推荐:"]
        for r in recommendations:
            icon = "✅" if r.get("confidence") == "high" else "💡"
            lines.append(
                f"  {icon} `{r['skill']}` (得分: {r['score']})"
            )
            if r.get("reasons"):
                lines.append(f"     理由: {'; '.join(r['reasons'][:2])}")

        top = recommendations[0]
        if top.get("confidence") == "high":
            lines.append(f"\n⚡ 建议自动加载: skill_view('{top['skill']}')")

        return "\n".join(lines)

    def to_system_prompt_block(self, skills_count: int = None) -> str:
        """生成增强版 system prompt 块"""
        stats = _sra_socket_request({"action": "stats"})
        if "error" in stats:
            return ""

        s = stats.get("stats", stats)
        count = skills_count or s.get("skills_count", 0)

        return (
            f"\n## SRA Runtime ({s.get('version', '1.2.1')})\n"
            f"SRA 是一个独立运行的技能推荐引擎。\n"
            f"当前管理 {count} 个技能。\n"
            f"API: Unix Socket ({SOCKET_FILE}) / HTTP (:{s.get('config', {}).get('http_port', 8536)})\n"
            f"使用 'sra --query <输入>' 或 HTTP POST 查询推荐。\n"
        )

    def to_proxy_format(self, message: str) -> dict:
        """以 Proxy 格式获取推荐（消息前置推理用）
        
        POST /recommend 请求 {'message': msg} 的响应格式。
        返回 rag_context + should_auto_load + recommendations。
        """
        result = _sra_socket_request({
            "action": "recommend",
            "params": {"query": message, "top_k": 5},
        })
        if "error" in result:
            return {
                "rag_context": "",
                "recommendations": [],
                "top_skill": None,
                "should_auto_load": False,
                "sra_available": False,
            }

        recs = result.get("result", {}).get("recommendations", [])
        top_skill = None
        should_auto_load = False
        rag_lines = []

        if recs:
            top = recs[0]
            top_skill = top["skill"]
            score = top["score"]
            should_auto_load = score >= 80

            rag_lines.append("── [SRA Skill 推荐] ──────────────────────────────")
            for i, r in enumerate(recs[:5]):
                flag = "⭐" if i == 0 else "  "
                conf = r["confidence"]
                s_name = r["skill"]
                s_score = r["score"]
                s_reasons = " | ".join(r.get("reasons", [])[:2])
                rag_lines.append(f"  {flag} [{conf:>6}] {s_name} ({s_score:.1f}分) — {s_reasons}")

            if should_auto_load:
                rag_lines.append(f"\n  ⚡ 强推荐自动加载: {top_skill}")
            else:
                rag_lines.append("\n  💡 建议: 可参考上述 skill")

            rag_lines.append("── ──────────────────────────────────────────────")

        return {
            "rag_context": "\n".join(rag_lines),
            "recommendations": [
                {
                    "skill": r["skill"],
                    "score": r["score"],
                    "confidence": r["confidence"],
                    "reasons": r.get("reasons", []),
                    "description": r.get("description", ""),
                }
                for r in recs[:5]
            ],
            "top_skill": top_skill,
            "should_auto_load": should_auto_load,
            "sra_available": True,
        }


# ── Claude Code 适配器 ──────────────────────

class ClaudeCodeAdapter(BaseAdapter):
    """Anthropic Claude Code CLI 适配器"""

    def format_suggestion(self, recommendations: List[Dict]) -> str:
        if not recommendations:
            return ""

        lines = ["[SRA Skill Recommendation]"]
        for r in recommendations[:2]:
            lines.append(f"- {r['skill']} (confidence: {r.get('confidence', 'medium')})")
            if r.get("description"):
                lines.append(f"  {r['description'][:80]}")

        return "\n".join(lines)

    def to_claude_tool_format(self, recommendations: List[Dict]) -> List[Dict]:
        """转换为 Claude Tool Use 格式"""
        tools = []
        for r in recommendations[:3]:
            tools.append({
                "name": r["skill"],
                "description": r.get("description", "")[:200],
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "string",
                            "description": f"Use {r['skill']} to handle the user request"
                        }
                    },
                    "required": ["task"]
                }
            })
        return tools


# ── OpenAI Codex CLI 适配器 ─────────────────

class CodexAdapter(BaseAdapter):
    """OpenAI Codex CLI 适配器"""

    def format_suggestion(self, recommendations: List[Dict]) -> str:
        if not recommendations:
            return ""

        lines = ["# SRA recommended skills"]
        for r in recommendations:
            lines.append(f"# - {r['skill']}: {r.get('description', '')[:80]}")

        return "\n".join(lines)

    def to_openai_tool_format(self, recommendations: List[Dict]) -> List[Dict]:
        """转换为 OpenAI Function Calling 格式"""
        return [
            {
                "type": "function",
                "function": {
                    "name": r["skill"],
                    "description": r.get("description", "")[:200],
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": f"The task for {r['skill']}"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
            for r in recommendations[:3]
        ]


# ── 通用 CLI 适配器 ─────────────────────────

class GenericCLIAdapter(BaseAdapter):
    """通用 CLI Agent 适配器 — 输出纯文本格式"""

    def format_suggestion(self, recommendations: List[Dict]) -> str:
        if not recommendations:
            return ""

        lines = ["=== SRA Skill Recommendation ==="]
        for i, r in enumerate(recommendations[:3], 1):
            lines.append(f"{i}. {r['skill']}")
            lines.append(f"   Score: {r['score']} | Confidence: {r.get('confidence', 'medium')}")
            if r.get("description"):
                lines.append(f"   {r['description'][:100]}")
        lines.append("=" * 35)

        return "\n".join(lines)


# ── 适配器工厂 ──────────────────────────────

ADAPTER_REGISTRY = {
    "hermes": HermesAdapter,
    "claude": ClaudeCodeAdapter,
    "codex": CodexAdapter,
    "opencode": GenericCLIAdapter,
    "generic": GenericCLIAdapter,
}


def get_adapter(agent_type: str = "hermes") -> BaseAdapter:
    """获取对应 Agent 的适配器"""
    adapter_class = ADAPTER_REGISTRY.get(agent_type.lower(), GenericCLIAdapter)
    return adapter_class()


def list_adapters() -> List[str]:
    """列出所有支持的 Agent 类型"""
    return list(ADAPTER_REGISTRY.keys())


# ── 独立测试 ────────────────────────────────

if __name__ == "__main__":
    import sys

    agent = sys.argv[1] if len(sys.argv) > 1 else "hermes"
    query = sys.argv[2] if len(sys.argv) > 2 else "帮我画个架构图"

    adapter = get_adapter(agent)
    recs = adapter.recommend(query)

    print(f"Agent: {agent}")
    print(f"Query: {query}")
    print()
    print(adapter.format_suggestion(recs))
