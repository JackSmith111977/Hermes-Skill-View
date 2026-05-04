#!/usr/bin/env bash
# ===============================================================
# SRA — Skill Runtime Advisor 一键安装脚本
# ===============================================================
# 用法:
#   curl -fsSL https://raw.githubusercontent.com/JackSmith111977/Hermes-Skill-View/main/scripts/install.sh | bash
#   或
#   bash install.sh [--help] [--prefix=/path] [--agent=hermes]
# ===============================================================

set -e

# ── 颜色 ───────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ── 默认配置 ──────────────────────────────
PREFIX="${SRA_PREFIX:-$HOME/.local}"
AGENT_TYPE="${SRA_AGENT:-hermes}"
SKILLS_DIR="${SRA_SKILLS_DIR:-$HOME/.hermes/skills}"
INSTALL_SYSTEMD=false
SKIP_PIP=false

# ── 参数解析 ──────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --prefix=*) PREFIX="${1#*=}"; shift ;;
        --agent=*)  AGENT_TYPE="${1#*=}"; shift ;;
        --skills=*) SKILLS_DIR="${1#*=}"; shift ;;
        --systemd)  INSTALL_SYSTEMD=true; shift ;;
        --skip-pip) SKIP_PIP=true; shift ;;
        --help)
            echo "SRA — Skill Runtime Advisor 一键安装脚本"
            echo
            echo "选项:"
            echo "  --prefix=PATH    安装前缀 (默认: ~/.local)"
            echo "  --agent=TYPE     Agent 类型 (默认: hermes)"
            echo "                  可选: hermes, claude, codex, opencode, generic"
            echo "  --skills=PATH    技能目录路径 (默认: ~/.hermes/skills)"
            echo "  --systemd        安装 systemd 服务（需要 sudo）"
            echo "  --skip-pip       跳过 pip 安装（用于已安装的情况）"
            echo "  --help           显示本帮助"
            exit 0
            ;;
        *) error "未知参数: $1"; exit 1 ;;
    esac
done

# ── 步骤 1: 检查环境 ──────────────────────
echo "=============================================="
echo "  SRA — Skill Runtime Advisor 安装"
echo "=============================================="
echo

info "系统信息: $(uname -a)"
info "Python: $(python3 --version 2>&1)"
info "安装前缀: $PREFIX"
info "Agent 类型: $AGENT_TYPE"
info "技能目录: $SKILLS_DIR"
echo

# 检查 Python 版本
PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if [[ $(echo "$PY_VERSION < 3.8" | bc) -eq 1 ]]; then
    error "需要 Python >= 3.8，当前: $PY_VERSION"
    exit 1
fi

# ── 步骤 2: 安装 Python 包 ────────────────
if [[ "$SKIP_PIP" != "true" ]]; then
    info "安装 SRA Python 包..."
    
    # 检查是否在源码目录
    if [[ -f "setup.py" ]]; then
        pip install --user -e . 2>/dev/null || pip install -e . 2>/dev/null || {
            warn "editable install 失败，尝试普通安装"
            pip install --user . 2>/dev/null || pip install . 2>/dev/null
        }
    else
        pip install --user sra-agent 2>/dev/null || pip install sra-agent 2>/dev/null || {
            warn "pip 安装失败，尝试从 GitHub 安装"
            pip install --user git+https://github.com/JackSmith111977/Hermes-Skill-View.git 2>/dev/null || {
                error "安装失败。请参照 README 从源码安装"
                exit 1
            }
        }
    fi
    ok "SRA Python 包安装完成"
fi

# ── 步骤 3: 创建配置 ──────────────────────
info "创建配置..."
SRA_HOME="$HOME/.sra"
mkdir -p "$SRA_HOME/data"

cat > "$SRA_HOME/config.json" << EOF
{
    "skills_dir": "$SKILLS_DIR",
    "data_dir": "$SRA_HOME/data",
    "socket_path": "$SRA_HOME/srad.sock",
    "http_port": 8532,
    "auto_refresh_interval": 3600,
    "enable_http": true,
    "enable_unix_socket": true,
    "log_level": "INFO",
    "watch_skills_dir": true
}
EOF
ok "配置文件已生成: $SRA_HOME/config.json"

# ── 步骤 4: 启动守护进程 ──────────────────
info "启动 SRA Daemon..."
# 查找 sra 命令
SRA_CMD=$(which sra 2>/dev/null || echo "$PREFIX/bin/sra")
if [[ -x "$SRA_CMD" ]]; then
    $SRA_CMD start 2>/dev/null || {
        warn "手动启动失败，请稍后运行: sra start"
    }
else
    warn "sra 命令未找到，尝试直接启动..."
    python3 -m skill_advisor.runtime.daemon &
fi

# 等待启动
sleep 1

# ── 步骤 5: 验证安装 ──────────────────────
info "验证安装..."
if command -v sra &>/dev/null; then
    ok "sra 命令可用"
    sra version 2>/dev/null || true
else
    warn "sra 命令不在 PATH 中"
    warn "请添加 $PREFIX/bin 到 PATH"
fi

# 测试守护进程
if [[ -S "$SRA_HOME/srad.sock" ]]; then
    ok "SRA Daemon 运行中 (socket: $SRA_HOME/srad.sock)"
    sra status 2>/dev/null || true
else
    warn "SRA Daemon 未启动，请稍后运行: sra start"
fi

# ── 步骤 6: 安装 systemd 服务 ────────────
if [[ "$INSTALL_SYSTEMD" == "true" ]]; then
    info "安装 systemd 服务..."
    sra install service 2>/dev/null || {
        warn "systemd 服务安装失败，请手动安装: sra install service"
    }
fi

# ── 步骤 7: 集成到 Agent ─────────────────
echo
info "将 SRA 集成到 $AGENT_TYPE Agent..."

case "$AGENT_TYPE" in
    hermes)
        echo
        echo "📝 将以下配置添加到 Hermes 的 learning-workflow 前置层:"
        echo
        echo "  from sra_agent.adapters import get_adapter"
        echo "  adapter = get_adapter('hermes')"
        echo "  recs = adapter.recommend(user_input)"
        echo "  if recs:"
        echo "      print(adapter.format_suggestion(recs))"
        ;;
    claude)
        echo "📝 Claude Code 集成:"
        echo "  在 Claude Code 的配置中添加 SRA tool use"
        echo "  sra install claude"
        ;;
    codex)
        echo "📝 OpenAI Codex 集成:"
        echo "  使用 Function Calling 格式"
        echo "  sra install codex"
        ;;
    *)
        echo "📝 通用集成:"
        echo "  sra install generic"
        ;;
esac

# ── 完成 ──────────────────────────────────
echo
echo "=============================================="
echo -e "${GREEN}  ✅ SRA 安装完成！${NC}"
echo "=============================================="
echo
echo "快速使用:"
echo "  sra start              # 启动守护进程"
echo "  sra recommend 画架构图  # 查询推荐"
echo "  sra status             # 查看状态"
echo "  sra coverage           # 查看覆盖率"
echo "  sra stats              # 查看统计"
echo "  sra stop               # 停止守护进程"
echo
echo "日志: $SRA_HOME/srad.log"
echo "Socket: $SRA_HOME/srad.sock"
echo "配置: $SRA_HOME/config.json"
echo
