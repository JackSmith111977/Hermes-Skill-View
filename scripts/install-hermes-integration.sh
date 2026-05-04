#!/usr/bin/env bash
# ===============================================================
# SRA Hermes Integration — 自动注入 SRA 上下文到 Hermes Agent
# ===============================================================
# 用法:
#   bash scripts/install-hermes-integration.sh [--uninstall] [--help]
#
# 功能:
#   修改 Hermes Agent 的 run_agent.py，在每次用户消息前自动调 SRA
#   获取技能推荐并注入到消息上下文中。
#
# 原理:
#   在 AIAgent.run_conversation() 的 user_message 处理流程中插入
#   SRA 查询。每次消息都调 SRA Daemon (http://127.0.0.1:8536/recommend)，
#   将返回的 rag_context 作为 [SRA] 前缀注到用户消息前。
#
# 效果:
#   [SRA] Skill Runtime Advisor 推荐:
#   ── [SRA Skill 推荐] ──────────────────────────────
#     ⭐ [medium] architecture-diagram (47.2分) — ...
#   ── ──────────────────────────────────────────────
#
#   用户消息原文...
# ===============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ── 路径 ──────────────────────────────────
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
HERMES_AGENT_DIR="$HERMES_HOME/hermes-agent"
RUN_AGENT="$HERMES_AGENT_DIR/run_agent.py"
BACKUP_SUFFIX=".sra-backup"

# ── 检测 ──────────────────────────────────
detect_hermes() {
    if [[ ! -f "$RUN_AGENT" ]]; then
        error "未找到 Hermes Agent: $RUN_AGENT"
        echo "  请确保 Hermes Agent 已安装 ($HERMES_AGENT_DIR)"
        echo "  或设置 HERMES_HOME 环境变量指向正确路径"
        exit 1
    fi
    ok "Hermes Agent 已发现: $RUN_AGENT"
}

check_sra_daemon() {
    if command -v curl &>/dev/null; then
        if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8536/health 2>/dev/null | grep -q 200; then
            ok "SRA Daemon 运行中 (127.0.0.1:8536)"
            return 0
        fi
    fi
    warn "SRA Daemon 未检测到运行 (http://127.0.0.1:8536)"
    echo "  集成会安装但不会生效，请确保先启动 SRA Daemon"
    echo "  启动: cd /path/to/sra-agent && python3 -m skill_advisor.runtime.daemon"
    return 1
}

# ── 安装 ──────────────────────────────────
install() {
    detect_hermes
    
    # 检查是否已安装
    if grep -q "_query_sra_context" "$RUN_AGENT"; then
        warn "SRA 集成已安装，跳过"
        info "如需重新安装，先运行 --uninstall"
        return 0
    fi

    # 备份
    cp "$RUN_AGENT" "${RUN_AGENT}${BACKUP_SUFFIX}"
    ok "已备份: ${RUN_AGENT}${BACKUP_SUFFIX}"

    # ── 插入 _query_sra_context 函数 ──
    # 找到 _qwen_portal_headers 函数结束位置（在 class AIAgent 之前）
    local insert_point
    insert_point=$(grep -n "^class AIAgent" "$RUN_AGENT" | head -1 | cut -d: -f1)
    if [[ -z "$insert_point" ]]; then
        error "未找到 class AIAgent 定义，集成失败"
        cp "${RUN_AGENT}${BACKUP_SUFFIX}" "$RUN_AGENT"
        exit 1
    fi

    # 在 class AIAgent 前插入 SRA 函数
    local sra_fn
    sra_fn=$(cat << 'PYEOF'


# =========================================================================
# SRA Context — real-time skill recommendation injection
# =========================================================================
# Added by SRA Hermes Integration (v1.1.0)
_SRA_CACHE: dict = {}  # module-level cache


def _query_sra_context(user_message: str) -> str:
    """Query SRA Daemon for skill recommendations and return formatted context.

    Called on every conversation turn.  Uses module-level cache keyed on
    message hash to avoid redundant queries when the agent retries the same
    turn.  Returns empty string on any failure — never blocks the agent.

    The result is formatted as a system note prefixed to the user message
    so the model sees skill recommendations before responding.
    """
    import urllib.request
    import json as _json
    import hashlib

    sra_url = os.environ.get("SRA_PROXY_URL", "http://127.0.0.1:8536")

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


PYEOF
)

    # 用 sed 在 class AIAgent 前插入
    sed -i "${insert_point}i\\$(echo "$sra_fn" | sed 's/$/\\/g' | sed '$s/\\$//')" "$RUN_AGENT"
    
    # ── 在 run_conversation 中插入调用 ──
    # 找到 "# Add user message" 这一行（SRA 注入点）
    local inject_line
    inject_line=$(grep -n "^        # Add user message" "$RUN_AGENT" | head -1 | cut -d: -f1)
    if [[ -z "$inject_line" ]]; then
        error "未找到注入点，恢复备份"
        cp "${RUN_AGENT}${BACKUP_SUFFIX}" "$RUN_AGENT"
        exit 1
    fi

    local sra_inject
    sra_inject=$(cat << 'PYEOF'

        # ── SRA Context Injection ─────────────────────────────────
        # Query SRA Daemon for real-time skill recommendations and
        # inject as a system note prefixed to the user message.
        # This runs on EVERY turn so recs stay fresh.  Silent on failure.
        _sra_ctx = _query_sra_context(user_message)
        if _sra_ctx:
            user_message = f"{_sra_ctx}\n\n{user_message}"
        # ───────────────────────────────────────────────────────────

PYEOF
)

    sed -i "${inject_line}i\\$(echo "$sra_inject" | sed 's/$/\\/g' | sed '$s/\\$//')" "$RUN_AGENT"

    ok "SRA Hermes 集成安装完成！"
    echo ""
    echo "📋 改动内容:"
    echo "  1. run_agent.py — 新增 _query_sra_context() 函数"
    echo "  2. run_agent.py — run_conversation() 中注入 SRA 上下文"
    echo ""
    echo "✅ 效果: 每次消息都会自动调 SRA 并注入 [SRA] 上下文"
    echo "📌 要求: SRA Daemon 运行在 http://127.0.0.1:8536"
    echo ""
    check_sra_daemon
    echo ""
    echo "💡 如需卸载: bash $0 --uninstall"
    echo "💡 如需重启 Gateway: hermes gateway restart"
}

# ── 卸载 ──────────────────────────────────
uninstall() {
    detect_hermes

    if [[ -f "${RUN_AGENT}${BACKUP_SUFFIX}" ]]; then
        cp "${RUN_AGENT}${BACKUP_SUFFIX}" "$RUN_AGENT"
        rm -f "${RUN_AGENT}${BACKUP_SUFFIX}"
        ok "SRA 集成已卸载 (从备份恢复)"
    else
        # 尝试手动清理
        if grep -q "_query_sra_context" "$RUN_AGENT"; then
            warn "未找到备份文件，尝试手动清理..."
            warn "请手动恢复: git checkout -- run_agent.py"
        else
            info "SRA 集成未安装"
        fi
    fi
}

# ── 主流程 ──────────────────────────────
echo "=============================================="
echo "  SRA Hermes 集成 v1.1.0"
echo "=============================================="
echo

case "${1:-install}" in
    install|--install)
        install
        ;;
    uninstall|--uninstall|remove|--remove)
        uninstall
        ;;
    help|--help|-h)
        echo "用法: bash scripts/install-hermes-integration.sh [选项]"
        echo ""
        echo "选项:"
        echo "  install     安装 SRA 集成 (默认)"
        echo "  uninstall   卸载 SRA 集成"
        echo "  help        显示帮助"
        echo ""
        echo "环境变量:"
        echo "  HERMES_HOME     Hermes Agent 家目录 (默认: ~/.hermes)"
        echo "  SRA_PROXY_URL   SRA Daemon 地址 (默认: http://127.0.0.1:8536)"
        ;;
    *)
        install
        ;;
esac
