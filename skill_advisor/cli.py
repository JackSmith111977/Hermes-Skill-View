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
  sra version      版本信息
  sra help         帮助
"""

import sys
import os
import json
import socket
import time
from typing import List, Optional

from .runtime.daemon import (
    cmd_start, cmd_stop, cmd_status, cmd_restart, cmd_attach,
    cmd_install_service, load_config, save_config, PID_FILE,
)

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
        print(f"📊 SRA Daemon 统计 v{stats.get('version', '1.0.0')}")
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
    print("作者: Emma (SRA Team)")
    print("许可: MIT")
    print()
    # 检查 Daemon 状态
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            print(f"Daemon: 运行中 (PID: {pid})")
        except:
            print("Daemon: 未运行")
    else:
        print("Daemon: 未运行")


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
    "refresh": cmd_refresh,
    "record": cmd_record,
    "config": cmd_config,
    "adapters": cmd_adapters,
    "install": cmd_install,
    "version": cmd_version,
    "help": lambda a: print_help(),
}


def print_help():
    print("SRA — Skill Runtime Advisor v1.0")
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
    print("  record <skill> <输入>  记录技能使用")
    print("  config [show|set|reset]  配置管理")
    print()
    print("Agent 集成:")
    print("  adapters              列出支持的 Agent 类型")
    print("  install <agent>      安装到指定 Agent")
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
