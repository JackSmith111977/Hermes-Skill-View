#!/usr/bin/env bash
# ===============================================================
# SRA Hermes Integration — 自动注入 SRA 上下文到 Hermes Agent
# ===============================================================
# 用法:
#   bash scripts/install-hermes-integration.sh [--uninstall] [--verify] [--help]
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
    echo "  启动: sra start"
    return 1
}

# ── 验证集成状态 ──────────────────────────
verify() {
    detect_hermes

    local has_func=false
    local has_inject=false

    if grep -q "_query_sra_context" "$RUN_AGENT"; then
        has_func=true
    fi

    if grep -q "SRA Context Injection" "$RUN_AGENT"; then
        has_inject=true
    fi

    echo ""
    echo "📋 SRA 集成状态:"
    echo "  _query_sra_context 函数: $([ "$has_func" = true ] && echo "✅ 已注入" || echo "❌ 未注入")"
    echo "  run_conversation 注入点: $([ "$has_inject" = true ] && echo "✅ 已注入" || echo "❌ 未注入")"

    if [[ "$has_func" == true ]] && [[ "$has_inject" == true ]]; then
        ok "SRA 集成完整"
    else
        warn "SRA 集成不完整，建议重新安装: bash $0 --install"
    fi

    check_sra_daemon
}

# ── 使用 Python 注入（比 sed 更可靠）──────
inject_sra_code() {
    local target_file="$1"
    python3 << 'PYEOF'
import sys
import re

target = sys.argv[1] if len(sys.argv) > 1 else None
if not target:
    print("ERROR: No target file", file=sys.stderr)
    sys.exit(1)

with open(target, 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.split('\n')

# 1. 查找 class AIAgent 定义
class_line = None
for i, line in enumerate(lines):
    if re.match(r'^class AIAgent\s*:', line):
        class_line = i
        break

if class_line is None:
    print("ERROR: 未找到 class AIAgent 定义", file=sys.stderr)
    sys.exit(1)

# 2. 查找 "# Add user message" 注入点
inject_line = None
for i, line in enumerate(lines):
    if '# Add user message' in line and line.strip().startswith('#'):
        inject_line = i
        break

if inject_line is None:
    print("ERROR: 未找到 '# Add user message' 注入点", file=sys.stderr)
    sys.exit(1)

# 3. 检查是否已注入
if '_query_sra_context' in content:
    print("SKIP: SRA 集成已存在")
    sys.exit(0)

# 4. 定义要注入的代码
sra_function = '''

# =========================================================================
# SRA Context — real-time skill recommendation injection
# =========================================================================
# Added by SRA Hermes Integration (v2.0.4)
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

        result = "\\n".join(lines)
        if len(result) > 2500:
            result = result[:2497] + "..."

        _SRA_CACHE["last_hash"] = _msg_hash
        _SRA_CACHE["last_result"] = result
        return result

    except Exception:
        _SRA_CACHE["last_hash"] = _msg_hash
        _SRA_CACHE["last_result"] = ""
        return ""

'''

sra_inject = '''
        # ── SRA Context Injection ─────────────────────────────────
        # Query SRA Daemon for real-time skill recommendations and
        # inject as a system note prefixed to the user message.
        # This runs on EVERY turn so recs stay fresh.  Silent on failure.
        _sra_ctx = _query_sra_context(user_message)
        if _sra_ctx:
            user_message = f"{_sra_ctx}\\n\\n{user_message}"
        # ───────────────────────────────────────────────────────────
'''

# 5. 注入函数（在 class AIAgent 前）
new_lines = lines[:class_line]
new_lines.append(sra_function.rstrip())
new_lines.extend(lines[class_line:])

# 6. 重新计算注入点（因为前面插入了代码）
# 注意：注入点需要重新查找，因为行号变了
new_inject_line = None
for i, line in enumerate(new_lines):
    if '# Add user message' in line and line.strip().startswith('#'):
        new_inject_line = i
        break

if new_inject_line is None:
    print("ERROR: 重新查找注入点失败", file=sys.stderr)
    sys.exit(1)

# 7. 注入调用代码
final_lines = new_lines[:new_inject_line]
final_lines.append(sra_inject.rstrip())
final_lines.extend(new_lines[new_inject_line:])

# 8. 写入文件
with open(target, 'w', encoding='utf-8') as f:
    f.write('\n'.join(final_lines))

print(f"OK: 已注入 SRA 集成到 {target}")
print(f"  - _query_sra_context 函数: 行 {class_line + 1} 前")
print(f"  - SRA 调用注入点: 行 {new_inject_line + 1} 前")
PYEOF
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

    # 使用 Python 注入（比 sed 更可靠）
    inject_sra_code "$RUN_AGENT"

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
    echo "💡 如需验证: bash $0 --verify"
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
echo "  SRA Hermes 集成 v2.0.4"
echo "=============================================="
echo

case "${1:-install}" in
    install|--install)
        install
        ;;
    uninstall|--uninstall|remove|--remove)
        uninstall
        ;;
    verify|--verify|status|--status)
        verify
        ;;
    help|--help|-h)
        echo "用法: bash scripts/install-hermes-integration.sh [选项]"
        echo ""
        echo "选项:"
        echo "  install     安装 SRA 集成 (默认)"
        echo "  uninstall   卸载 SRA 集成"
        echo "  verify      验证集成状态"
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
