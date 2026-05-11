"""
SRA — Gateway Drop-in 管理工具函数

提供 systemd drop-in 配置文件的创建、清理、健康检查功能。
SRA 与 Hermes Gateway 之间的依赖关系通过 drop-in 文件声明，
此模块确保 drop-in 生命周期的完整性。
"""

import os
import subprocess
import logging

logger = logging.getLogger("sra.dropin")

# ── 路径常量 ──────────────────────────────

GATEWAY_SERVICE_NAME = "hermes-gateway.service"
DROPIN_FILENAME = "sra-dep.conf"
DROPIN_RELPATH = f"{GATEWAY_SERVICE_NAME}.d/{DROPIN_FILENAME}"

# systemd 用户级配置目录
SYSTEMD_USER_DIR = os.path.expanduser("~/.config/systemd/user")

# ── 路径获取函数 ──────────────────────────


def get_dropin_path():
    """获取 sra-dep.conf 的完整路径"""
    return os.path.join(SYSTEMD_USER_DIR, DROPIN_RELPATH)


def get_dropin_dir():
    """获取 drop-in 目录路径"""
    return os.path.join(SYSTEMD_USER_DIR, f"{GATEWAY_SERVICE_NAME}.d")


def get_service_path():
    """获取 srad.service 的完整路径"""
    return os.path.join(SYSTEMD_USER_DIR, "srad.service")


# ── 核心操作函数 ──────────────────────────


def cleanup_dropin(dry_run: bool = False) -> bool:
    """
    清理 sra-dep.conf drop-in 文件。

    如果文件存在，删除它并执行 systemctl daemon-reload。
    如果文件不存在，什么也不做。

    Args:
        dry_run: True 时只打印将要执行的操作，不实际执行

    Returns:
        True 如果有文件被清理，False 如果文件不存在或清理失败
    """
    dropin_path = get_dropin_path()
    if not os.path.exists(dropin_path):
        logger.info("Gateway 依赖配置不存在，无需清理")
        return False

    if dry_run:
        print(f"  即将删除: {dropin_path}")
        return True

    try:
        os.unlink(dropin_path)
        print(f"  ✅ 已删除: {dropin_path}")

        # 清理后执行 daemon-reload 使 systemd 感知变更
        result = subprocess.run(
            ["systemctl", "--user", "daemon-reload"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            print("  ✅ systemd daemon-reload 完成")
        else:
            print(f"  ⚠️  daemon-reload 返回非零: {result.stderr.strip()[:100]}")

        logger.info("Gateway 依赖配置已清理")
        return True

    except OSError as e:
        logger.error(f"清理 drop-in 失败: {e}")
        print(f"  ❌ 删除失败: {e}")
        return False


def create_dropin(use_wants: bool = True, dry_run: bool = False) -> bool:
    """
    创建 sra-dep.conf drop-in 文件（用于安装流程）。

    Args:
        use_wants: True 用 Wants= (软依赖)，False 用 Requires= (硬依赖，不推荐)
        dry_run: True 时只打印

    Returns:
        True 如果创建成功
    """
    dropin_dir = get_dropin_dir()
    dropin_path = get_dropin_path()

    if dry_run:
        print(f"  即将创建: {dropin_path}")
        print(f"  依赖类型: {'Wants=' if use_wants else 'Requires='} (推荐 Wants=)")
        return True

    os.makedirs(dropin_dir, exist_ok=True)

    dep_keyword = "Wants" if use_wants else "Requires"
    content = f"""[Unit]
# Auto-configured by SRA
# {dep_keyword}= 是{'软' if use_wants else '硬'}依赖：
#   SRA 存在时自动按序启动，不存在时 Gateway{'不受影响' if use_wants else '启动失败（exit 5）'}
{dep_keyword}=srad.service
After=srad.service
"""

    try:
        with open(dropin_path, "w") as f:
            f.write(content)
        print(f"  ✅ 已创建: {dropin_path}")
        return True
    except OSError as e:
        logger.error(f"创建 drop-in 失败: {e}")
        print(f"  ❌ 创建失败: {e}")
        return False


# ── 检查函数 ──────────────────────────────


def check_dropin_health() -> dict:
    """
    检查 drop-in 配置的健康状态。

    Returns:
        dict: {
            "exists": bool,          # drop-in 文件是否存在
            "service_exists": bool,   # srad.service 是否存在
            "uses_wants": bool,       # 是否使用 Wants= (而非 Requires=)
            "healthy": bool,          # 总体是否健康
            "issues": [str],          # 问题列表
        }
    """
    result = {
        "exists": False,
        "service_exists": False,
        "uses_wants": False,
        "healthy": True,
        "issues": [],
    }

    dropin_path = get_dropin_path()
    service_path = get_service_path()

    # 检查 drop-in 文件是否存在
    if os.path.exists(dropin_path):
        result["exists"] = True
        try:
            with open(dropin_path) as f:
                content = f.read()
            result["uses_wants"] = "Wants=srad.service" in content
            if "Requires=srad.service" in content:
                result["healthy"] = False
                result["issues"].append(
                    "sra-dep.conf 使用了 Requires= (硬依赖)，建议改为 Wants= (软依赖)"
                )
        except OSError as e:
            result["healthy"] = False
            result["issues"].append(f"无法读取 sra-dep.conf: {e}")
    else:
        # drop-in 不存在不算不健康（可能 SRA 未安装或者在 macOS 上）
        pass

    # 检查 srad.service 是否存在
    if os.path.exists(service_path):
        result["service_exists"] = True

    # 跨检查：drop-in 存在但 srad.service 不存在
    if result["exists"] and not result["service_exists"]:
        result["healthy"] = False
        result["issues"].append(
            "sra-dep.conf 存在但 srad.service 不存在（孤儿配置），请运行 sra uninstall 清理"
        )

    return result


def print_health_report(health: dict):
    """打印健康检查报告"""
    if not health["exists"]:
        print("  ℹ️  Gateway 依赖配置: 不存在（这是正常的，如果 SRA 未安装）")
        return

    print(f"  📄 sra-dep.conf: {'存在' if health['exists'] else '不存在'}")
    print(f"  🔗 依赖类型: {'Wants= (软依赖 ✅)' if health['uses_wants'] else 'Requires= (硬依赖 ❌)'}")
    print(f"  🏠 srad.service: {'存在' if health['service_exists'] else '不存在'}")

    if health["healthy"]:
        print(f"  ✅ 依赖链健康")
    else:
        print(f"  ❌ 依赖链存在 {len(health['issues'])} 个问题:")
        for issue in health["issues"]:
            print(f"     - {issue}")
