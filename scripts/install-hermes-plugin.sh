#!/usr/bin/env bash
# ===============================================================
# install-hermes-plugin.sh — 部署 sra-guard 插件到 Hermes
# ===============================================================
# 用法:
#   bash scripts/install-hermes-plugin.sh [install|uninstall]
#
# 功能:
#   install   — 将 plugins/sra-guard/ 复制到 Hermes plugins 目录
#   uninstall — 从 Hermes plugins 目录删除 sra-guard
# ===============================================================

set -euo pipefail

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
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCE_DIR="$PROJECT_DIR/plugins/sra-guard"
HERMES_PLUGINS_DIR="${HERMES_HOME:-$HOME/.hermes}/hermes-agent/plugins"
TARGET_DIR="$HERMES_PLUGINS_DIR/sra-guard"

# ── 检查源目录完整性 ─────────────────────
check_source() {
    local missing=0
    for f in "plugin.yaml" "__init__.py" "client.py"; do
        if [[ ! -f "$SOURCE_DIR/$f" ]]; then
            error "源目录缺少: $f"
            missing=1
        fi
    done
    if [[ $missing -ne 0 ]]; then
        error "源目录不完整: $SOURCE_DIR"
        exit 1
    fi
}

# ── 安装 ──────────────────────────────────
install() {
    echo "=============================================="
    echo "  sra-guard 插件安装"
    echo "=============================================="
    echo ""

    # 检查源目录
    if [[ ! -d "$SOURCE_DIR" ]]; then
        error "源目录不存在: $SOURCE_DIR"
        info "请在 SRA 项目根目录运行此脚本"
        exit 1
    fi
    check_source
    ok "源目录完整: $SOURCE_DIR"

    # 检查目标目录是否已存在
    if [[ -d "$TARGET_DIR" ]]; then
        warn "sra-guard 插件已安装: $TARGET_DIR"
        info "如需重新安装，先运行: $0 uninstall"
        return 0
    fi

    # 创建目标目录
    mkdir -p "$HERMES_PLUGINS_DIR"

    # 复制文件
    cp -r "$SOURCE_DIR" "$TARGET_DIR"
    ok "文件已复制到: $TARGET_DIR"

    # 验证
    check_target
    ok "sra-guard 插件安装完成！"
    echo ""
    echo "📋 安装内容:"
    echo "  $(ls -1 "$TARGET_DIR" | wc -l) 个文件"
    echo ""
    echo "✅ Hermes 下次启动时自动加载 sra-guard"
    echo "📌 如需卸载: $0 uninstall"
}

# ── 卸载 ──────────────────────────────────
uninstall() {
    echo "=============================================="
    echo "  sra-guard 插件卸载"
    echo "=============================================="
    echo ""

    if [[ ! -d "$TARGET_DIR" ]]; then
        warn "sra-guard 插件未安装: $TARGET_DIR"
        return 0
    fi

    rm -rf "$TARGET_DIR"
    ok "sra-guard 插件已卸载"

    # 验证
    if [[ -d "$TARGET_DIR" ]]; then
        error "卸载失败: $TARGET_DIR 仍存在"
        exit 1
    fi
}

# ── 验证 ──────────────────────────────────
check_target() {
    local missing=0
    for f in "plugin.yaml" "__init__.py" "client.py"; do
        if [[ ! -f "$TARGET_DIR/$f" ]]; then
            error "目标目录缺少: $f"
            missing=1
        fi
    done
    if [[ $missing -ne 0 ]]; then
        exit 1
    fi
    ok "目标目录完整性验证通过"
}

# ── 主流程 ────────────────────────────────
case "${1:-install}" in
    install|--install)
        install
        ;;
    uninstall|--uninstall|remove|--remove)
        uninstall
        ;;
    help|--help|-h)
        echo "用法: bash scripts/install-hermes-plugin.sh [选项]"
        echo ""
        echo "选项:"
        echo "  install     安装 sra-guard 插件 (默认)"
        echo "  uninstall   卸载 sra-guard 插件"
        echo "  help        显示帮助"
        echo ""
        echo "环境变量:"
        echo "  HERMES_HOME  Hermes 家目录 (默认: ~/.hermes)"
        ;;
    *)
        echo "未知选项: $1"
        echo "用法: $0 [install|uninstall|help]"
        exit 1
        ;;
esac
