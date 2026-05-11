#!/usr/bin/env bash
# ===============================================================
# SRA — Skill Runtime Advisor 一键安装脚本 v1.1.0
# ===============================================================
# 用法:
#   curl -fsSL https://raw.githubusercontent.com/JackSmith111977/Hermes-Skill-View/main/scripts/install.sh | bash
#   或
#   bash install.sh [--help] [--prefix=/path] [--agent=hermes] [--proxy]
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

# ── 系统检测函数 ──────────────────────────
SRA_OS="unknown"
SRA_INIT="unknown"
SRA_HAS_SUDO=false
SRA_IS_WSL=false
SRA_IS_DOCKER=false
SRA_HAS_HERMES=false

detect_os() {
    case "$(uname -s)" in
        Linux*)  SRA_OS="linux" ;;
        Darwin*) SRA_OS="darwin" ;;
        *)       SRA_OS="other" ;;
    esac
}

detect_init() {
    if [[ -d /run/systemd/system ]]; then
        SRA_INIT="systemd"
    elif command -v launchctl &>/dev/null; then
        SRA_INIT="launchd"
    else
        SRA_INIT="other"
    fi
}

check_sudo() {
    if command -v sudo &>/dev/null && sudo -n true 2>/dev/null; then
        SRA_HAS_SUDO=true
    fi
}

check_wsl() {
    if [[ -f /proc/version ]] && grep -qi microsoft /proc/version 2>/dev/null; then
        SRA_IS_WSL=true
    fi
}

check_docker() {
    if [[ -f /.dockerenv ]]; then
        SRA_IS_DOCKER=true
    fi
}

check_hermes() {
    if command -v hermes &>/dev/null; then
        SRA_HAS_HERMES=true
        return 0
    fi
    if systemctl --user show hermes-gateway.service &>/dev/null 2>&1; then
        SRA_HAS_HERMES=true
        return 0
    fi
    return 1
}

run_system_detect() {
    detect_os
    detect_init
    check_sudo
    check_wsl
    check_docker
    check_hermes
}

# ── 默认配置 ──────────────────────────────
PREFIX="${SRA_PREFIX:-$HOME/.local}"
AGENT_TYPE="${SRA_AGENT:-hermes}"
SKILLS_DIR="${SRA_SKILLS_DIR:-$HOME/.hermes/skills}"
INSTALL_SYSTEMD=false
SKIP_PIP=false
PROXY_MODE=false     # v1.1.0: Proxy 模式（消息前置推理中间件）
PROXY_PORT=8536      # Proxy 默认端口

# ── 参数解析 ──────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --prefix=*) PREFIX="${1#*=}"; shift ;;
        --agent=*)  AGENT_TYPE="${1#*=}"; shift ;;
        --skills=*) SKILLS_DIR="${1#*=}"; shift ;;
        --systemd)  INSTALL_SYSTEMD=true; shift ;;
        --skip-pip) SKIP_PIP=true; shift ;;
        --proxy)    PROXY_MODE=true; shift ;;
        --proxy-port=*) PROXY_PORT="${1#*=}"; shift ;;
        --help)
            echo "SRA — Skill Runtime Advisor 一键安装脚本 v1.1.0"
            echo
            echo "选项:"
            echo "  --prefix=PATH      安装前缀 (默认: ~/.local)"
            echo "  --agent=TYPE       Agent 类型 (默认: hermes)"
            echo "                    可选: hermes, claude, codex, opencode, generic"
            echo "  --skills=PATH      技能目录路径 (默认: ~/.hermes/skills)"
            echo "  --systemd          配置开机自启（自动检测系统，无需手动指定类型）"
            echo "                    支持: Linux(systemd用户级/系统级), macOS(launchd),"
            echo "                          WSL(入口脚本), Docker(入口脚本)"
            echo "  --proxy            安装 Proxy 模式（消息前置推理中间件）"
            echo "  --proxy-port=PORT  Proxy 端口 (默认: 8536)"
            echo "  --skip-pip         跳过 pip 安装（用于已安装的情况）"
            exit 0
            ;;
        *) error "未知参数: $1"; exit 1 ;;
    esac
done

# ── 步骤 1: 检查环境 ──────────────────────
echo "=============================================="
echo "  SRA — Skill Runtime Advisor v1.1.0"
echo "=============================================="
echo

info "系统信息: $(uname -a)"
info "Python: $(python3 --version 2>&1)"
info "安装前缀: $PREFIX"
info "Agent 类型: $AGENT_TYPE"
info "技能目录: $SKILLS_DIR"
# 运行系统检测
run_system_detect
info "系统: $SRA_OS, Init: $SRA_INIT, sudo: $SRA_HAS_SUDO"
if [[ "$SRA_IS_WSL" == "true" ]]; then info "环境: WSL"; fi
if [[ "$SRA_IS_DOCKER" == "true" ]]; then info "环境: Docker"; fi
if [[ "$SRA_HAS_HERMES" == "true" ]]; then info "检测到: Hermes Agent"; fi
if [[ "$INSTALL_SYSTEMD" == "true" ]]; then
    info "自启: 启用（自动适配 $SRA_OS/$SRA_INIT）"
fi
if [[ "$PROXY_MODE" == "true" ]]; then
    info "安装模式: Proxy（消息前置推理中间件）"
    info "Proxy 端口: $PROXY_PORT"
fi
echo

# 检查 Python 版本
PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if [[ $(echo "$PY_VERSION < 3.8" | bc) -eq 1 ]]; then
    error "需要 Python >= 3.8，当前: $PY_VERSION"
    exit 1
fi

# ── 步骤 2: 安装 Python 包（多路径降级策略）──
if [[ "$SKIP_PIP" != "true" ]]; then
    info "安装 SRA Python 包..."
    info "尝试方式 1/3: 源码安装（最稳定）..."
    
    # 检查是否在源码目录
    if [[ -f "setup.py" ]]; then
        info "检测到源码目录，使用 editable install..."
        pip install --user -e . || pip install -e . || {
            warn "editable install 失败，尝试普通安装"
            pip install --user . || pip install . || {
                error "Python 包安装失败，请检查 pip 和 Python 版本"
                exit 1
            }
        }
    else
        info "尝试方式 2/3: PyPI 安装..."
        pip install --user sra-agent || pip install sra-agent || {
            warn "PyPI 安装失败，尝试方式 3/3: GitHub 源码安装..."
            pip install --user git+https://github.com/JackSmith111977/Hermes-Skill-View.git || {
                error "所有安装方式均失败。请手动运行: pip install sra-agent"
                exit 1
            }
        }
    fi
    
    # 安装后验证
    if command -v sra &>/dev/null; then
        ok "sra CLI 安装成功: $(sra version 2>/dev/null || echo 'v1.1.0')"
    else
        warn "sra 命令未在 PATH 中找到，可能是 ~/.local/bin 未加入 PATH"
        info "运行: export PATH=\$PATH:\$HOME/.local/bin"
    fi
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
    "http_port": ${PROXY_PORT},
    "auto_refresh_interval": 3600,
    "enable_http": true,
    "enable_unix_socket": true,
    "log_level": "INFO",
    "watch_skills_dir": true
}
EOF
ok "配置文件已生成: $SRA_HOME/config.json"

# ── 步骤 3b: 创建 Proxy 服务文件（Proxy 模式）──
if [[ "$PROXY_MODE" == "true" ]]; then
    info "创建 Proxy 服务..."
    
    # 创建 Proxy 入口脚本
    SRA_BIN=$(which sra 2>/dev/null || echo "$PREFIX/bin/sra")
    cat > "$SRA_HOME/sra-proxy.sh" << PROXYEOF
#!/usr/bin/env bash
# SRA Proxy — 消息前置推理中间件 (v1.1.0)
# 用 sra daemon 的 HTTP API 直接提供 Proxy 服务
export SRA_PROXY_ENABLED=true
export SRA_PROXY_URL=http://127.0.0.1:${PROXY_PORT}
exec python3 -m skill_advisor.runtime.daemon
PROXYEOF
    chmod +x "$SRA_HOME/sra-proxy.sh"
    ok "Proxy 入口脚本已生成: $SRA_HOME/sra-proxy.sh"
fi

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
    # 测试 HTTP API
    if command -v curl &>/dev/null; then
        HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:${PROXY_PORT}/health 2>/dev/null || echo "000")
        if [[ "$HTTP_STATUS" == "200" ]]; then
            ok "HTTP API: http://127.0.0.1:${PROXY_PORT} ✅"
            # 测试 recommend
            REC_RESULT=$(curl -s -X POST http://127.0.0.1:${PROXY_PORT}/recommend \
                -H "Content-Type: application/json" \
                -d '{"message": "test"}' 2>/dev/null)
            if echo "$REC_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('sra_version',''))" 2>/dev/null; then
                ok "POST /recommend API 正常 ✅"
            fi
        fi
    fi
else
    warn "SRA Daemon 未启动，请稍后运行: sra start"
fi

# ── 步骤 6: 自启配置（跨平台自动适配）───
if [[ "$INSTALL_SYSTEMD" == "true" ]]; then
    echo ""
    info "配置开机自启..."
    echo "  检测: OS=$SRA_OS  Init=$SRA_INIT  sudo=$SRA_HAS_SUDO  WSL=$SRA_IS_WSL  Docker=$SRA_IS_DOCKER"
    echo ""

    SRA_BIN=$(which sra 2>/dev/null || echo "$PREFIX/bin/sra")

    case "$SRA_OS-$SRA_INIT" in
        linux-systemd)
            if [[ "$SRA_HAS_SUDO" == "true" ]]; then
                # ── 系统级 systemd service（有 sudo）──
                info "安装系统级 systemd 服务..."
                cat > /tmp/srad.service << SERVICEEOF
[Unit]
Description=SRA — Skill Runtime Advisor Daemon
Documentation=https://github.com/JackSmith111977/Hermes-Skill-View
After=network.target

[Service]
Type=simple
User=$(whoami)
ExecStart=$SRA_BIN attach
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=srad

[Install]
WantedBy=multi-user.target
SERVICEEOF
                sudo cp /tmp/srad.service /etc/systemd/system/srad.service
                sudo systemctl daemon-reload
                sudo systemctl enable --now srad.service
                ok "✅ 系统级 srad.service 已安装并启动 (sudo)"
                # Proxy 模式共存
                if [[ "$PROXY_MODE" == "true" ]]; then
                    info "Proxy 模式: 直接通过 srad.service 提供 HTTP API"
                fi
            else
                # ── 用户级 systemd service（无 sudo）──
                info "安装用户级 systemd 服务..."
                SYSTEMD_USER_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
                mkdir -p "$SYSTEMD_USER_DIR"

                cat > "$SYSTEMD_USER_DIR/srad.service" << SERVICEEOF
[Unit]
Description=SRA — Skill Runtime Advisor Daemon
Documentation=https://github.com/JackSmith111977/Hermes-Skill-View
After=network.target

[Service]
Type=simple
ExecStart=$SRA_BIN attach
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=srad

[Install]
WantedBy=default.target
SERVICEEOF
                ok "srad.service 已创建: $SYSTEMD_USER_DIR/srad.service"

                # ── Hermes Gateway 依赖（自动检测）──
                if [[ "$SRA_HAS_HERMES" == "true" ]]; then
                    info "检测到 Hermes Agent，配置 Gateway 依赖..."
                    mkdir -p "$SYSTEMD_USER_DIR/hermes-gateway.service.d"
                    cat > "$SYSTEMD_USER_DIR/hermes-gateway.service.d/sra-dep.conf" << CONFIGEOF
[Unit]
# Auto-configured by SRA install.sh
# Wants= 是软依赖：SRA 存在时按序启动，不存在时 Gateway 不受影响
# 不要改为 Requires= 否则 Gateway 在 srad.service 不存在时启动失败
Wants=srad.service
After=srad.service
CONFIGEOF
                    ok "🔗 Hermes Gateway 依赖已配置"
                fi

                systemctl --user daemon-reload
                systemctl --user enable --now srad.service
                ok "✅ 用户级 srad.service 已安装并启动"

                if [[ "$SRA_HAS_HERMES" == "true" ]]; then
                    echo ""
                    info "下次重启 Hermes Gateway 时 SRA 自动随其启动:"
                    echo "  systemctl --user restart hermes-gateway"
                fi
            fi
            ;;

        darwin-launchd)
            # ── macOS launchd ──
            info "安装 macOS launchd 服务..."
            LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
            mkdir -p "$LAUNCH_AGENTS_DIR"
            PLIST_FILE="$LAUNCH_AGENTS_DIR/com.sra.daemon.plist"

            cat > "$PLIST_FILE" << PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.sra.daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>$SRA_BIN</string>
        <string>attach</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HOME/.sra/srad.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/.sra/srad.log</string>
</dict>
</plist>
PLISTEOF

            launchctl load -w "$PLIST_FILE" 2>/dev/null || {
                warn "launchctl load 失败，请手动加载:"
                echo "  launchctl load -w $PLIST_FILE"
            }
            ok "✅ macOS launchd 服务已安装: $PLIST_FILE"
            ;;

        darwin-*)
            # ── macOS 无 launchd（罕见）──
            warn "macOS 未检测到 launchctl，请手动配置自启"
            ;;

        *)
            # ── 其他系统：生成入口脚本 + 引导提示 ──
            ENTRY_SCRIPT="$SRA_HOME/sra-entry.sh"
            cat > "$ENTRY_SCRIPT" << EOF
#!/usr/bin/env bash
# SRA Daemon 入口脚本 — 用于手动或开机自启配置
# 由 install.sh --systemd 自动生成
# 将此脚本添加到你的系统开机启动项中
exec $SRA_BIN attach
EOF
            chmod +x "$ENTRY_SCRIPT"
            ok "入口脚本已生成: $ENTRY_SCRIPT"

            echo ""
            warn "⚠️  未检测到已知的 init 系统，请手动配置自启:"
            if [[ "$SRA_IS_WSL" == "true" ]]; then
                echo "  📌 WSL 环境: 在 Windows 任务计划程序中添加:"
                echo "     操作: 启动 wsl -d <发行版> -- $ENTRY_SCRIPT"
                echo "     触发器: 系统启动时"
            elif [[ "$SRA_IS_DOCKER" == "true" ]]; then
                echo "  📌 Docker 环境: 在 docker run 命令中添加:"
                echo "     docker run --restart=always ..."
                echo "     或在 docker-compose.yml 中添加: restart: always"
            else
                echo "  📌 将以下命令添加到系统的开机启动项:"
                echo "     $ENTRY_SCRIPT"
                echo ""
                echo "  或使用 screen/tmux 保持后台运行:"
                echo "     screen -dmS sra $ENTRY_SCRIPT"
            fi
            echo ""
            info "完整文档: https://github.com/JackSmith111977/Hermes-Skill-View"
            ;;
    esac
fi

# ── 步骤 7b: 运行环境检查 ─────────────────
echo
info "运行环境检查..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/check-sra.py" ]]; then
    python3 "$SCRIPT_DIR/check-sra.py" --port "${PROXY_PORT}" || {
        warn "环境检查未全部通过，请查看上方输出并修复"
    }
else
    warn "check-sra.py 未找到，跳过环境检查"
fi

# ── 步骤 8: 集成到 Agent ─────────────────
echo
info "将 SRA 集成到 $AGENT_TYPE Agent..."

case "$AGENT_TYPE" in
    hermes)
        echo
        echo "📝 将以下配置添加到 Agent 的启动脚本或配置中:"
        echo
        echo "  # Hermes Python SDK 方式:"
        echo "  from sra_agent.adapters import get_adapter"
        echo "  adapter = get_adapter('hermes')"
        echo "  recs = adapter.recommend(user_input)"
        echo "  if recs:"
        echo "      print(adapter.format_suggestion(recs))"
        echo
        echo "  # 或直接使用 HTTP API（消息前置推理）:"
        echo "  curl -s -X POST http://127.0.0.1:${PROXY_PORT}/recommend \\"
        echo "    -H 'Content-Type: application/json' \\"
        echo "    -d '{\"message\": \"<用户消息>\"}'"
        echo
        echo "  # 设置环境变量（让 Agent 知道 SRA 可用）:"
        echo "  export SRA_PROXY_ENABLED=true"
        echo "  export SRA_PROXY_URL=http://127.0.0.1:${PROXY_PORT}"
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
echo -e "${GREEN}  ✅ SRA v1.1.0 安装完成！${NC}"
echo "=============================================="
echo
echo "📋 安装后自检："
echo "  python3 scripts/check-sra.py     # 一键环境检查"
echo
echo "📋 快速使用："
echo "  sra start              # 启动守护进程"
echo "  sra status             # 查看运行状态"
echo "  sra recommend 画架构图  # 查询技能推荐"
echo "  sra stop               # 停止守护进程"
echo
echo "📋 更多命令："
echo "  sra coverage           # 查看技能覆盖率"
echo "  sra stats              # 查看统计"
echo "  sra version            # 版本信息"
echo
if [[ "$PROXY_MODE" == "true" ]]; then
echo "📋 Proxy 模式测试："
echo "  curl -s http://127.0.0.1:${PROXY_PORT}/health"
echo "  curl -s -X POST http://127.0.0.1:${PROXY_PORT}/recommend \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"message\": \"画个架构图\"}'"
echo
fi
echo "📋 资源路径："
echo "  日志:     $SRA_HOME/srad.log"
echo "  Socket:   $SRA_HOME/srad.sock"
echo "  配置:     $SRA_HOME/config.json"
echo "  GitHub:   https://github.com/JackSmith111977/Hermes-Skill-View"
echo
