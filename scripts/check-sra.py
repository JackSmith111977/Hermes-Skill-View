#!/usr/bin/env python3
"""
SRA — Skill Runtime Advisor 环境检查脚本 v1.1.0

AI 友好设计：运行此脚本即可获得完整的安装状态诊断。
每个检查项输出标准化格式，AI 能自动判断是否通过。

用法:
    python3 check-sra.py              # 检查全部
    python3 check-sra.py --port 9000  # 指定端口
"""

import json
import os
import sys
import urllib.request
import urllib.error


def check_python():
    """检查 Python 版本"""
    v = sys.version_info
    ok = v.major >= 3 and v.minor >= 8
    status = "ok" if ok else "fail"
    print(f"python: {status} ({v.major}.{v.minor}.{v.micro})")
    if not ok:
        print("  → 需要 Python >= 3.8")
    return ok


def check_sra_cli():
    """检查 sra CLI 是否可用"""
    try:
        result = os.popen("sra version 2>&1").read().strip()
        ok = bool(result) and ("sra" in result.lower() or "version" in result.lower() or "v" in result.lower())
        status = "ok" if ok else "fail"
        print(f"sra cli: {status} ({result})")
        if not ok:
            print("  → sra 命令不可用，请运行: pip install sra-agent")
        return ok
    except Exception as e:
        print(f"sra cli: fail ({e})")
        print("  → sra 命令不可用，请运行: pip install sra-agent")
        return False


def check_daemon(port=8536):
    """检查 SRA Daemon 是否运行"""
    try:
        url = f"http://127.0.0.1:{port}/health"
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=3)
        data = json.loads(resp.read())
        version = data.get("version", data.get("sra_version", "?"))
        skills = data.get("skills_count", "?")
        print(f"sra daemon: ok (port {port}, v{version}, {skills} skills indexed)")
        return True
    except urllib.error.URLError:
        print(f"sra daemon: fail (端口 {port} 不可达)")
        print("  → 请运行: sra start")
        return False
    except Exception as e:
        print(f"sra daemon: fail ({e})")
        print("  → 请运行: sra start")
        return False


def check_skills_dir(path=None):
    """检查技能目录是否存在且有内容"""
    if path:
        skills_dir = path
    else:
        skills_dir = os.environ.get("SRA_SKILLS_DIR", os.path.expanduser("~/.hermes/skills"))

    exists = os.path.isdir(skills_dir)
    if exists:
        try:
            count = len(os.listdir(skills_dir))
        except PermissionError:
            count = 0
    else:
        count = 0

    if exists and count > 0:
        print(f"skills dir: ok ({skills_dir}, {count} skills)")
        return True
    elif exists:
        print(f"skills dir: warn ({skills_dir} 为空)")
        print("  → 请确保技能目录中有 SKILL.md 文件")
        return False
    else:
        print(f"skills dir: fail ({skills_dir} 不存在)")
        print(f"  → 请创建目录并设置 SRA_SKILLS_DIR 环境变量")
        return False


def check_config():
    """检查 SRA 配置文件"""
    config_path = os.path.expanduser("~/.sra/config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                cfg = json.load(f)
            print(f"sra config: ok ({config_path})")
            print(f"  → skills_dir: {cfg.get('skills_dir', 'not set')}")
            print(f"  → http_port: {cfg.get('http_port', 'not set')}")
            return True
        except json.JSONDecodeError:
            print(f"sra config: fail ({config_path} 格式错误)")
            return False
    else:
        print(f"sra config: warn (配置文件不存在，将使用默认配置)")
        return True  # 不是致命错误


def check_autostart():
    """检查开机自启配置是否就绪"""
    # Linux systemd
    user_svc = os.path.expanduser("~/.config/systemd/user/srad.service")
    sys_svc = "/etc/systemd/system/srad.service"
    # macOS launchd
    launchd_plist = os.path.expanduser("~/Library/LaunchAgents/com.sra.daemon.plist")
    # WSL/Docker 入口脚本
    entry_script = os.path.expanduser("~/.sra/sra-entry.sh")

    found = False
    details = []

    if os.path.exists(user_svc):
        details.append(f"user-level service ({user_svc})")
        # 检查是否启用
        if os.path.exists(os.path.expanduser("~/.config/systemd/user/default.target.wants/srad.service")):
            details[-1] += " [enabled ✅]"
        found = True

    if os.path.exists(sys_svc):
        details.append(f"system-level service ({sys_svc})")
        found = True

    if os.path.exists(launchd_plist):
        details.append(f"macOS launchd ({launchd_plist})")
        found = True

    if os.path.exists(entry_script):
        details.append(f"entry script ({entry_script})")
        found = True

    if found:
        for d in details:
            print(f"autostart: ok ({d})")
        return True
    else:
        print("autostart: warn (未找到自启配置)")
        print("  → 运行 sra install --systemd 或 bash install.sh --systemd 配置")
        return True  # 非致命


def main():
    # 解析参数
    port = 8536
    skills_dir = None
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--port" and i < len(sys.argv) - 1:
            port = int(sys.argv[i + 1])
        elif arg.startswith("--port="):
            port = int(arg.split("=", 1)[1])
        elif arg == "--skills-dir" and i < len(sys.argv) - 1:
            skills_dir = sys.argv[i + 1]
        elif arg.startswith("--skills-dir="):
            skills_dir = arg.split("=", 1)[1]

    print("=" * 50)
    print("  SRA — 环境检查 v1.1.0")
    print("=" * 50)
    print()

    results = {
        "python": check_python(),
        "sra_cli": check_sra_cli(),
        "sra_daemon": check_daemon(port),
        "skills_dir": check_skills_dir(skills_dir),
        "sra_config": check_config(),
        "autostart": check_autostart(),
    }

    print()
    print("=" * 50)

    all_ok = all(results.values())
    critical_fail = not results["python"] or not results["sra_cli"]

    if all_ok:
        print("  ✅ SRA 环境检查全部通过")
        print("=" * 50)
        sys.exit(0)
    elif critical_fail:
        print("  ❌ 关键检查未通过，请修复后重试")
        print("=" * 50)
        sys.exit(1)
    else:
        warn_items = [k for k, v in results.items() if not v]
        print(f"  ⚠️  {len(warn_items)} 项未通过: {', '.join(warn_items)}")
        print("  → 非关键性警告，SRA 仍可运行")
        print("=" * 50)
        sys.exit(0)


if __name__ == "__main__":
    main()
