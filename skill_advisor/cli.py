"""
SRA CLI — 完整的命令行工具

子命令:
  sra start        启动守护进程
  sra stop         停止守护进程  
  sra status       查看状态
  sra restart      重启
  sra attach       前台运行（调试）
  sra recommend    推荐匹配（一次查询）
  sra query        同 recommend
  sra stats        查看统计
  sra coverage     分析技能覆盖率
  sra refresh      刷新索引
  sra record       记录使用
  sra config       配置管理
  sra install      安装到 Agent
  sra adapters     列出 Agent 适配器
  sra upgrade      升级到最新版本（从 GitHub）
  sra uninstall    完全卸载
  sra version      版本信息
  sra help         帮助
"""

import sys
import os
import json
import socket
import time
import subprocess
import shutil
from typing import List, Optional

from .runtime.daemon import (
    cmd_start, cmd_stop, cmd_status, cmd_restart, cmd_attach,
    cmd_install_service, load_config, save_config, PID_FILE,
)
from .runtime.dropin import cleanup_dropin, check_dropin_health, print_health_report

SOCKET_FILE = os.path.expanduser("~/.sra/srad.sock")


def _socket_request(request: dict) -> dict:
    """向守护进程发送请求"""
    if not os.path.exists(SOCKET_FILE):
        return {"error": "SRA Daemon 未运行", "suggestion": "请先运行 'sra start'"}
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.settimeout(5.0)
        client.connect(SOCKET_FILE)
        client.sendall(json.dumps(request).encode("utf-8"))
        response = client.recv(65536).decode("utf-8")
        client.close()
        return json.loads(response)
    except Exception as e:
        return {"error": str(e)}


def cmd_recommend(args: List[str]):
    """推荐匹配"""
    if not args:
        print("🚨 用法: sra recommend <查询内容>")
        return
    
    query = " ".join(args)
    
    # 优先通过 Socket 查询运行中的守护进程
    result = _socket_request({
        "action": "recommend",
        "params": {"query": query, "top_k": 3},
    })
    
    if "error" in result and "未运行" in result.get("error", ""):
        # 降级：直接本地查询
        print("⚠️  SRA Daemon 未运行，使用本地模式")
        from .advisor import SkillAdvisor
        advisor = SkillAdvisor()
        result = {"result": advisor.recommend(query)}
    
    recs = result.get("result", result).get("recommendations", [])
    
    print(f"🔍 查询: '{query}'")
    
    if result.get("result"):
        r = result["result"]
        print(f"⚡ {r.get('processing_ms', 0)}ms | 📊 {r.get('skills_scanned', 0)} skills")
    
    print()
    
    if recs:
        print("🎯 推荐技能:")
        for r in recs:
            icon = "✅" if r.get("confidence") == "high" else "💡"
            print(f"  {icon} {r['skill']} (得分: {r['score']})")
            print(f"     📄 {r.get('description', '')[:100]}")
            print(f"     📂 类别: {r.get('category', '')}")
            if r.get("reasons"):
                print(f"     💬 {'; '.join(r['reasons'][:3])}")
            if r.get("confidence") == "high":
                print(f"     ⚡ 建议自动加载")
            print()
    else:
        print("📭 未找到匹配技能")


def cmd_stats(args: List[str]):
    """查看统计"""
    # 通过守护进程查询
    result = _socket_request({"action": "stats"})
    
    if "error" in result and "未运行" in result.get("error", ""):
        # 本地模式
        print("⚠️  SRA Daemon 未运行，使用本地模式")
        from .advisor import SkillAdvisor
        advisor = SkillAdvisor()
        stats = advisor.show_stats()
        print("=" * 50)
        print("📊 SRA 统计 (本地模式)")
        print("=" * 50)
        print(f"  技能总数: {stats['total_skills']}")
        print(f"  总推荐次数: {stats['total_recommendations']}")
    else:
        stats = result.get("stats", result)
        print("=" * 50)
        print(f"📊 SRA Daemon 统计 v{stats.get('version', '1.1.0')}")
        print("=" * 50)
        print(f"  状态: {stats.get('status', 'unknown')}")
        print(f"  技能数: {stats.get('skills_count', 0)}")
        print(f"  请求次数: {stats.get('total_requests', 0)}")
        print(f"  推荐次数: {stats.get('total_recommendations', 0)}")
        uptime = stats.get("uptime_seconds", 0)
        if uptime:
            h, r = divmod(uptime, 3600)
            m, s = divmod(r, 60)
            print(f"  运行时长: {h}时{m}分{s}秒")


def cmd_coverage(args: List[str]):
    """分析技能覆盖率"""
    result = _socket_request({"action": "coverage"})
    
    if "error" in result and "未运行" in result.get("error", ""):
        print("⚠️  SRA Daemon 未运行，使用本地模式")
        from .advisor import SkillAdvisor
        advisor = SkillAdvisor()
        cr = advisor.analyze_coverage()
    else:
        cr = result.get("result", {})
    
    print("=" * 60)
    print("📊 SRA 技能识别覆盖率")
    print("=" * 60)
    print(f"  总技能数: {cr.get('total', 0)}")
    print(f"  能识别的: {cr.get('covered', 0)}")
    print(f"  覆盖率: {cr.get('coverage_rate', 0)}%")
    
    not_covered = cr.get("not_covered", [])
    if not_covered:
        print(f"\n❌ 未能识别的技能 ({len(not_covered)} 个):")
        for s in not_covered[:10]:
            print(f"  - {s['name']} ({s['category']})")


def cmd_compliance(args: List[str]):
    """查看技能遵循率统计"""
    result = _socket_request({"action": "stats/compliance"})

    if "error" in result and "未运行" in result.get("error", ""):
        print("⚠️  SRA Daemon 未运行，使用本地模式")
        from .advisor import SkillAdvisor
        advisor = SkillAdvisor()
        stats = advisor.get_compliance_stats()
    else:
        stats = result.get("compliance", result.get("stats", {}))

    summary = stats.get("summary", {})
    per_skill = stats.get("per_skill", {})

    print("=" * 60)
    print("📊 SRA 技能遵循率统计")
    print("=" * 60)
    print(f"  总查看次数: {summary.get('total_views', 0)}")
    print(f"  总使用次数: {summary.get('total_uses', 0)}")
    print(f"  总跳过次数: {summary.get('total_skips', 0)}")
    cr = summary.get("overall_compliance_rate", 1.0)
    if cr is not None:
        pct = cr * 100
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"  整体遵循率: {bar} {pct:.0f}%")

    if per_skill:
        print(f"\n📈 按技能维度 ({len(per_skill)} 个):")
        # 按使用次数排序
        sorted_skills = sorted(per_skill.items(), key=lambda x: x[1].get("use_count", 0), reverse=True)
        for name, s in sorted_skills[:15]:
            uc = s.get("use_count", 0)
            sc = s.get("skip_count", 0)
            vc = s.get("view_count", 0)
            sr = s.get("compliance_rate")
            rate_str = f"{sr * 100:.0f}%" if sr is not None else "N/A"
            print(f"  {name:<30} 👁️{vc} ✅{uc} ⏭️{sc} 遵循率: {rate_str}")


def cmd_refresh(args: List[str]):
    """刷新技能索引"""
    result = _socket_request({"action": "refresh"})
    
    if "error" in result:
        if "未运行" in result.get("error", ""):
            print("⚠️  SRA Daemon 未运行，使用本地模式")
            from .advisor import SkillAdvisor
            advisor = SkillAdvisor()
            count = advisor.refresh_index()
            print(f"✅ 索引已刷新: {count} 个 skill")
        else:
            print(f"❌ 刷新失败: {result.get('error')}")
    else:
        print(f"✅ 索引已刷新: {result.get('count', 0)} 个 skill")


def cmd_record(args: List[str]):
    """记录使用"""
    if len(args) < 2:
        print("🚨 用法: sra record <skill_name> <用户输入> [--accepted true/false]")
        return
    
    skill_name = args[0]
    user_input = args[1]
    accepted = True
    
    if "--accepted" in args:
        idx = args.index("--accepted")
        if idx + 1 < len(args):
            accepted = args[idx + 1].lower() == "true"
    
    result = _socket_request({
        "action": "record",
        "params": {
            "skill": skill_name,
            "input": user_input,
            "accepted": accepted,
        },
    })
    
    if "error" in result:
        if "未运行" in result.get("error", ""):
            print("⚠️  SRA Daemon 未运行，使用本地模式")
            from .advisor import SkillAdvisor
            advisor = SkillAdvisor()
            advisor.record_usage(skill_name, user_input, accepted)
        else:
            print(f"❌ 记录失败: {result.get('error')}")
    
    print(f"✅ 已记录: {skill_name} ← '{user_input[:50]}'")


def cmd_config(args: List[str]):
    """配置管理"""
    config = load_config()
    
    if not args or args[0] == "show":
        print("=" * 50)
        print("⚙️  SRA 配置")
        print("=" * 50)
        for k, v in config.items():
            print(f"  {k}: {v}")
    
    elif args[0] == "set":
        if len(args) < 3:
            print("🚨 用法: sra config set <key> <value>")
            return
        key = args[1]
        value = args[2]
        
        # 类型推断
        if value.lower() in ("true", "false"):
            config[key] = value.lower() == "true"
        elif value.isdigit():
            config[key] = int(value)
        elif value.replace(".", "").isdigit():
            config[key] = float(value)
        else:
            config[key] = value
        
        save_config(config)
        print(f"✅ 配置已更新: {key} = {config[key]}")
    
    elif args[0] == "reset":
        from .runtime.daemon import DEFAULT_CONFIG
        for k in list(config.keys()):
            if k in DEFAULT_CONFIG:
                config[k] = DEFAULT_CONFIG[k]
        save_config(config)
        print("✅ 配置已重置为默认值")
    
    else:
        print(f"🚨 未知配置命令: {args[0]}")
        print("  可用: show, set <key> <value>, reset")


def cmd_adapters(args: List[str]):
    """列出 Agent 适配器"""
    from .adapters import list_adapters
    
    print("=" * 50)
    print("🔌 SRA Agent 适配器")
    print("=" * 50)
    for name in list_adapters():
        print(f"  - {name}")
    print()
    print("用法: sra install <agent_type>")
    print("示例: sra install hermes")


def cmd_install(args: List[str]):
    """安装到 Agent"""
    agent_type = args[0] if args else "hermes"
    
    from .adapters import get_adapter
    
    if agent_type == "hermes":
        print("📝 安装 SRA 到 Hermes Agent")
        print()
        print("步骤 1: 确保 SRA Daemon 已启动")
        print("  sra start")
        print()
        print("步骤 2: 在 Hermes 的 learning-workflow 前置层添加:")
        print()
        adapter = get_adapter("hermes")
        print(adapter.to_system_prompt_block())
        print()
        print("步骤 3: 当需要查询推荐时加载 skill-advisor:")
        print("  sra recommend <查询内容>")
        print()
        print("或通过 Python 集成:")
        print("  from sra_agent.adapters import get_adapter")
        print("  adapter = get_adapter('hermes')")
        print("  recs = adapter.recommend('帮我画个架构图')")
        print("  print(adapter.format_suggestion(recs))")
    
    elif agent_type in ("claude", "codex", "opencode"):
        print(f"📝 安装 SRA 到 {agent_type}")
        print()
        print("步骤 1: 确保 SRA Daemon 已启动")
        print("  sra start")
        print()
        print("步骤 2: 在 Agent 的 system prompt 中添加:")
        adapter = get_adapter(agent_type)
        print(adapter.to_system_prompt_block())
        print()
        print("步骤 3: 运行时查询:")
        print(f"  sra --agent {agent_type} --query '<用户输入>'")
    
    else:
        print(f"❌ 未知 Agent 类型: {agent_type}")
        print("可用类型: hermes, claude, codex, opencode, generic")


def cmd_version(args: List[str]):
    """版本信息"""
    from . import __version__
    print(f"SRA — Skill Runtime Advisor v{__version__}")
    print("让 AI Agent 知道自己有什么能力，以及什么时候该用什么能力")
    print()
    print("作者: Emma (SRA Team) / Kei")
    print("许可: MIT")
    print()
    # 检查 Daemon 状态
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            print(f"Daemon: 运行中 (PID: {pid})")
        except (ProcessLookupError, ValueError):
            print("Daemon: 未运行（PID 文件残留）")
    else:
        print("Daemon: 未运行")


# ── 升级 ────────────────────────────────────

def cmd_upgrade(args: List[str]):
    """升级 SRA 到最新版本"""
    repo_url = "https://github.com/JackSmith111977/Hermes-Skill-View.git"
    sra_src = "/tmp/sra-latest"  # 默认值

    # 解析参数
    version = None
    for i, a in enumerate(args):
        if a in ("--version", "-V") and i + 1 < len(args):
            version = args[i + 1].lstrip("v")

    # 1. 停止守护进程
    if os.path.exists(PID_FILE):
        print("⏹️  正在停止 SRA Daemon...")
        cmd_stop(None)
        time.sleep(1)

    print("=" * 50)
    print("📦 SRA 升级工具")
    print("=" * 50)

    # 2. 检查当前安装状态 + 自动检测源码路径
    pip_cmd = [sys.executable, "-m", "pip"]
    result = subprocess.run(
        pip_cmd + ["show", "sra-agent"],
        capture_output=True, text=True
    )

    if result.returncode == 0:
        info = {}
        for line in result.stdout.split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                info[k.strip()] = v.strip()
        print(f"📦 当前版本: {info.get('Version', '未知')}")
        print(f"📂 安装位置: {info.get('Location', '未知')}")
        # pip show 输出的 key 是 "Editable project location"——大小写不敏感匹配
        editable_key = next((k for k in info if "editable" in k.lower() and "location" in k.lower()), None)
        is_editable = editable_key is not None
        print(f"🔗 安装模式: {'editable (-e)' if is_editable else '标准安装'}")
        if is_editable:
            sra_src = info[editable_key]
            print(f"📁 源码目录: {sra_src}")
        if version:
            print(f"🎯 目标版本: v{version}")
    else:
        print("⚠️  未检测到已安装的 SRA 包，将执行全新安装")

    print()

    # 3. 设置代理环境（国内服务器需要）
    env = os.environ.copy()
    if "https_proxy" not in env and "HTTPS_PROXY" not in env:
        for port in [7890, 7891, 1080, 1087]:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.3)
                s.connect(("127.0.0.1", port))
                s.close()
                env["https_proxy"] = f"http://127.0.0.1:{port}"
                env["http_proxy"] = f"http://127.0.0.1:{port}"
                print(f"🌐 检测到代理: 127.0.0.1:{port}，已自动设置")
                break
            except (ConnectionRefusedError, OSError, socket.timeout):
                continue

    # 4. 获取最新代码
    if os.path.exists(os.path.join(sra_src, ".git")):
        print("🔄 从 Git 仓库拉取最新代码...")
        result = subprocess.run(
            ["git", "pull"],
            cwd=sra_src, capture_output=True, text=True, env=env
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            print(f"   {output}" if output else "   ✅ 已是最新")
        else:
            print(f"   ⚠️  Git pull 失败: {result.stderr.strip()[:100]}")
            bak_dir = f"{sra_src}.bak.{int(time.time())}"
            shutil.move(sra_src, bak_dir)
            print(f"   → 已备份旧代码到 {bak_dir}")
            print("   → 将重新克隆...")
            result = subprocess.run(
                ["git", "clone", repo_url, sra_src],
                capture_output=True, text=True, env=env
            )
            if result.returncode != 0:
                print(f"❌ 克隆失败: {result.stderr.strip()[:100]}")
                print()
                print("💡 提示：国内服务器请确保代理已启动")
                print("   systemctl --user status mihomo")
                return
            print("✅ 代码克隆完成")
    else:
        if os.path.exists(sra_src):
            bak_dir = f"{sra_src}.bak.{int(time.time())}"
            shutil.move(sra_src, bak_dir)
            print(f"📦 已备份旧目录到 {bak_dir}")

        print("📥 从 GitHub 克隆最新代码...")
        result = subprocess.run(
            ["git", "clone", repo_url, sra_src],
            capture_output=True, text=True, env=env
        )
        if result.returncode != 0:
            print(f"❌ 克隆失败: {result.stderr.strip()[:100]}")
            print()
            print("💡 提示：国内服务器请确保代理已启动")
            print("   systemctl --user status mihomo")
            return
        print("✅ 代码克隆完成")

    # 如果指定了版本，切换到该 Tag
    if version:
        tag = f"v{version}" if not version.startswith("v") else version
        print(f"🏷️  切换到版本 {tag}...")
        r = subprocess.run(
            ["git", "checkout", tag],
            cwd=sra_src, capture_output=True, text=True, env=env
        )
        if r.returncode == 0:
            print(f"   ✅ 已切换至 {tag}")
        else:
            print(f"   ⚠️  切换失败: {r.stderr.strip()[:80]}")
            print("   💡 将使用最新代码")

    print()

    # 5. 重新安装
    print("🔧 正在安装到当前 Python 环境...")
    result = subprocess.run(
        pip_cmd + ["install", "--no-build-isolation", "-e", sra_src],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        print(f"   ⚠️  --no-build-isolation 失败，尝试标准安装...")
        result = subprocess.run(
            pip_cmd + ["install", "-e", sra_src],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"   ❌ 安装失败: {result.stderr.strip()[:200]}")
            print()
            print("💡 建议手动执行:")
            print(f"   {sys.executable} -m pip install -e {sra_src}")
            return

    # 提取新版号
    new_version = "未知"
    for line in result.stdout.split("\n"):
        if "sra-agent" in line:
            for part in line.strip().split():
                if part[0:1].isdigit() and "." in part:
                    new_version = part.rstrip(",")
                    break

    print()
    print("✅ " + "=" * 40)
    print(f"✅ SRA 升级完成！")
    print(f"   版本: {new_version}")
    print(f"   源码: {sra_src}")
    print("✅ " + "=" * 40)
    print()
    print("💡 接下来:")
    print("   sra start          # 启动新版 Daemon")
    print("   sra version        # 查看版本信息")
    if version:
        print("   sra --help         # 查看完整帮助")


# ── 卸载 ────────────────────────────────────

def cmd_uninstall(args: List[str]):
    """卸载 SRA"""
    remove_all = "--all" in args or "-a" in args
    force = "-y" in args or "--yes" in args

    print("=" * 50)
    print("🗑️  SRA 卸载工具")
    print("=" * 50)

    pip_cmd = [sys.executable, "-m", "pip"]

    # 检查是否已安装
    check = subprocess.run(
        pip_cmd + ["show", "sra-agent"],
        capture_output=True, text=True
    )
    if check.returncode != 0:
        print("ℹ️  SRA 未安装（pip 中未找到 sra-agent 包）")
    else:
        for line in check.stdout.split("\n"):
            if line.startswith("Version:"):
                print(f"📦 已安装版本: {line.split(':', 1)[1].strip()}")
                break

    print()

    # 1. 停止守护进程
    if os.path.exists(PID_FILE):
        print("⏹️  正在停止 SRA Daemon...")
        cmd_stop(None)
        time.sleep(0.5)
    else:
        print("ℹ️  SRA Daemon 未运行")

    print()

    # 2. 移除 systemd 服务
    user_service = os.path.expanduser("~/.config/systemd/user/srad.service")
    sys_service = "/etc/systemd/system/srad.service"

    if os.path.exists(user_service):
        print("🗑️  移除用户级 systemd 服务...")
        subprocess.run(
            ["systemctl", "--user", "disable", "srad"],
            capture_output=True
        )
        os.unlink(user_service)
        subprocess.run(
            ["systemctl", "--user", "daemon-reload"],
            capture_output=True
        )
        print("   ✅ 用户级服务已移除")

    if os.path.exists(sys_service):
        print("🗑️  检测到系统级 systemd 服务")
        print(f"   路径: {sys_service}")
        print(f"   需要手动执行: sudo rm {sys_service}")
        print("   然后: sudo systemctl daemon-reload")

    print()

    # 3. 卸载 Python 包
    if check.returncode == 0:
        print("📦 卸载 Python 包 sra-agent...")
        result = subprocess.run(
            pip_cmd + ["uninstall", "sra-agent", "-y"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print("   ✅ Python 包已卸载")
        else:
            print(f"   ⚠️  卸载可能未完全: {result.stderr.strip()[:100]}")
    else:
        print("📦 Python 包: 未安装，跳过")

    print()

    # 4. 清理 ~/.sra/
    sra_home = os.path.expanduser("~/.sra")
    if os.path.exists(sra_home):
        if remove_all or force:
            print(f"  🗑️  删除 {sra_home}/ ...")
            shutil.rmtree(sra_home, ignore_errors=True)
            print("   ✅ 配置和数据已清除")
        else:
            print(f"  📁 配置目录 {sra_home}/ 已保留")
            print("   如需删除请添加 --all 参数，或手动:")
            print(f"   rm -rf {sra_home}")
    else:
        print("  📁 配置目录不存在，跳过")

    print()

    # 5. 清理 Gateway 依赖配置（sra-dep.conf）
    print("🔄 清理 Gateway 依赖配置...")
    cleanup_dropin()

    print()
    print("✅ " + "=" * 40)
    print("✅ SRA 卸载完成！")
    print("✅ " + "=" * 40)
    print()
    print("💡 如果将来需要重新安装:")
    print("   pip install sra-agent")
    print("   或参考: https://github.com/JackSmith111977/Hermes-Skill-View#readme")


def cmd_dep_check(args: List[str]):
    """检查 SRA 与 Hermes Gateway 的依赖链健康度"""
    print("=" * 50)
    print("🔗 SRA 依赖链检查")
    print("=" * 50)
    print()

    print(f"📁 systemd 用户目录: {os.path.expanduser('~/.config/systemd/user/')}")
    print()

    health = check_dropin_health()
    print_health_report(health)

    print()
    if health["healthy"]:
        print("✅ 依赖链检查通过")
    else:
        print("⚠️  依赖链存在风险，请根据上方提示修复")


# ── 主入口 ──────────────────────────────────

COMMANDS = {
    "start": cmd_start,
    "stop": cmd_stop,
    "status": cmd_status,
    "restart": cmd_restart,
    "attach": cmd_attach,
    "recommend": cmd_recommend,
    "query": cmd_recommend,
    "stats": cmd_stats,
    "coverage": cmd_coverage,
    "compliance": cmd_compliance,
    "refresh": cmd_refresh,
    "record": cmd_record,
    "config": cmd_config,
    "adapters": cmd_adapters,
    "install": cmd_install,
    "upgrade": cmd_upgrade,
    "uninstall": cmd_uninstall,
    "dep-check": cmd_dep_check,
    "version": cmd_version,
    "help": lambda a: print_help(),
}


def print_help():
    print("SRA — Skill Runtime Advisor v1.1")
    print()
    print("用法: sra <command> [options]")
    print()
    print("守护进程管理:")
    print("  start                 启动 SRA Daemon（后台守护进程）")
    print("  stop                  停止 SRA Daemon")
    print("  status                查看 Daemon 状态")
    print("  restart               重启 Daemon")
    print("  attach                前台运行（调试用）")
    print()
    print("技能推荐:")
    print("  recommend <查询>      推荐匹配技能")
    print("  query <查询>          同 recommend")
    print()
    print("系统管理:")
    print("  stats                 查看运行统计")
    print("  coverage              分析技能识别覆盖率")
    print("  refresh               刷新技能索引")
    print("  record <name> <input>  记录技能使用场景")
    print("  compliance             查看技能遵循率统计")
    print("  config [show|set|reset] 配置管理")
    print()
    print("Agent 集成:")
    print("  adapters              列出支持的 Agent 类型")
    print("  install <agent>      安装到指定 Agent")
    print()
    print("管理维护:")
    print("  upgrade [--version <tag>]  升级 SRA 到最新版本")
    print("  uninstall [-a|--all]        卸载 SRA（--all 清除配置）")
    print("  dep-check                   检查 Gateway 依赖链健康度")
    print()
    print("其他:")
    print("  version               版本信息")
    print("  help                  显示本帮助")
    print()
    print("示例:")
    print("  sra start              # 启动守护进程")
    print("  sra recommend 画架构图  # 查询推荐")
    print("  sra coverage           # 查看覆盖率")
    print("  sra install hermes     # 安装到 Hermes")
    print("  sra upgrade            # 从 GitHub 升级到最新版")
    print("  sra upgrade -V 1.2.0   # 升级到指定版本")
    print("  sra uninstall          # 卸载 SRA（保留配置）")
    print("  sra uninstall --all    # 完全卸载（含配置和索引数据）")


def main():
    if len(sys.argv) < 2:
        print_help()
        return
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    if command in COMMANDS:
        COMMANDS[command](args)
    else:
        # 尝试作为查询（快速模式）
        cmd_recommend([command] + args)


if __name__ == "__main__":
    main()
