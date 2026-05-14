#!/usr/bin/env bash
# ===============================================================
# SRA Hermes Integration — 自动注入 SRA 上下文到 Hermes Agent
# ===============================================================
# 用法:
#   bash scripts/install-hermes-integration.sh [--uninstall] [--verify] [--help]
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

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
HERMES_AGENT_DIR="$HERMES_HOME/hermes-agent"
RUN_AGENT="$HERMES_AGENT_DIR/run_agent.py"
BACKUP_SUFFIX=".sra-backup"

detect_hermes() {
    if [[ ! -f "$RUN_AGENT" ]]; then
        error "未找到 Hermes Agent: $RUN_AGENT"
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
    echo "  启动: sra start"
    return 1
}

verify() {
    detect_hermes
    local has_func=false
    local has_inject=false
    grep -q "_query_sra_context" "$RUN_AGENT" && has_func=true
    grep -q "SRA Context Injection" "$RUN_AGENT" && has_inject=true
    
    echo ""
    echo "📋 SRA 集成状态:"
    echo "  _query_sra_context 函数: $([ "$has_func" = true ] && echo "✅ 已注入" || echo "❌ 未注入")"
    echo "  run_conversation 注入点: $([ "$has_inject" = true ] && echo "✅ 已注入" || echo "❌ 未注入")"
    
    [[ "$has_func" == true ]] && [[ "$has_inject" == true ]] && ok "SRA 集成完整" || warn "SRA 集成不完整"
    check_sra_daemon
}

inject_sra_code() {
    python3 - "$1" << 'PYEOF'
import sys, re
target = sys.argv[1]
with open(target, 'r', encoding='utf-8') as f:
    lines = f.read().split('\n')

class_line = next((i for i, l in enumerate(lines) if re.match(r'^class AIAgent\s*:', l)), None)
inject_line = next((i for i, l in enumerate(lines) if '# Add user message' in l and l.strip().startswith('#')), None)

if class_line is None or inject_line is None:
    print(f"ERROR: 未找到注入点 (class={class_line}, inject={inject_line})", file=sys.stderr)
    sys.exit(1)

if '_query_sra_context' in '\n'.join(lines):
    print("SKIP: SRA 集成已存在")
    sys.exit(0)

SRA_FUNC = '''
# =========================================================================
# SRA Context — real-time skill recommendation injection
# =========================================================================
_SRA_CACHE: dict = {}

def _query_sra_context(user_message: str) -> str:
    """Query SRA Daemon for skill recommendations."""
    import urllib.request, json as _json, hashlib
    sra_url = os.environ.get("SRA_PROXY_URL", "http://127.0.0.1:8536")
    _msg_hash = hashlib.md5(user_message.encode("utf-8")).hexdigest()[:12]
    if _SRA_CACHE.get("last_hash") == _msg_hash:
        return _SRA_CACHE.get("last_result", "")
    try:
        req = urllib.request.Request(f"{sra_url}/recommend", method="POST")
        req.data = _json.dumps({"message": user_message}).encode("utf-8")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
        rag = data.get("rag_context", "")
        if not rag:
            _SRA_CACHE["last_hash"] = _msg_hash
            _SRA_CACHE["last_result"] = ""
            return ""
        result = f"[SRA] Skill Runtime Advisor 推荐:\\n{rag}"
        if data.get("should_auto_load") and data.get("top_skill"):
            result += f"\\n[SRA] ⚡ 建议自动加载: {data['top_skill']}"
        _SRA_CACHE["last_hash"] = _msg_hash
        _SRA_CACHE["last_result"] = result[:2500]
        return _SRA_CACHE["last_result"]
    except Exception:
        _SRA_CACHE["last_hash"] = _msg_hash
        _SRA_CACHE["last_result"] = ""
        return ""
'''

SRA_INJECT = '''
        # ── SRA Context Injection ─────────────────────────────────
        _sra_ctx = _query_sra_context(user_message)
        if _sra_ctx:
            user_message = f"{_sra_ctx}\\n\\n{user_message}"
        # ───────────────────────────────────────────────────────────
'''

new_lines = lines[:class_line] + [SRA_FUNC.rstrip()] + lines[class_line:]
new_inject = next((i for i, l in enumerate(new_lines) if '# Add user message' in l and l.strip().startswith('#')), None)
final = new_lines[:new_inject] + [SRA_INJECT.rstrip()] + new_lines[new_inject:]

with open(target, 'w', encoding='utf-8') as f:
    f.write('\n'.join(final))
print(f"OK: 已注入 SRA 集成到 {target}")
PYEOF
}

install() {
    detect_hermes
    grep -q "_query_sra_context" "$RUN_AGENT" && { warn "SRA 集成已安装"; return 0; }
    cp "$RUN_AGENT" "${RUN_AGENT}${BACKUP_SUFFIX}"
    ok "已备份: ${RUN_AGENT}${BACKUP_SUFFIX}"
    inject_sra_code "$RUN_AGENT"
    ok "SRA Hermes 集成安装完成！"
    check_sra_daemon
}

uninstall() {
    detect_hermes
    [[ -f "${RUN_AGENT}${BACKUP_SUFFIX}" ]] && cp "${RUN_AGENT}${BACKUP_SUFFIX}" "$RUN_AGENT" && rm -f "${RUN_AGENT}${BACKUP_SUFFIX}" && ok "已卸载" || warn "无备份文件"
}

echo "=============================================="
echo "  SRA Hermes 集成 v2.0.4"
echo "=============================================="
echo

case "${1:-install}" in
    install|--install) install ;;
    uninstall|--uninstall|remove|--remove) uninstall ;;
    verify|--verify|status|--status) verify ;;
    help|--help|-h) echo "用法: bash $0 [--install|--uninstall|--verify|--help]" ;;
    *) install ;;
esac
