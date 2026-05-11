"""SRA 运行时 CLI 命令 — 守护进程生命周期管理"""

import os
import sys
import json
import time
import socket
import signal
import logging

from .lock import FileLock, check_port_in_use
from .daemon import SRaDDaemon
from .config import (
    ensure_sra_home, load_config,
    PID_FILE, LOCK_FILE, SOCKET_FILE, LOG_FILE, STATUS_FILE,
)

logger = logging.getLogger("sra.commands")


# ── 命令行接口 ─────────────────────────────

def cmd_start(args=None) -> None:
    """启动守护进程"""
    ensure_sra_home()
    
    # ── OS 级文件锁：原子性单例检测 ──
    lock = FileLock(LOCK_FILE, timeout=0)  # 非阻塞尝试
    if not lock.acquire():
        # 锁已被其他进程持有
        existing_pid = lock.get_lock_pid()
        if existing_pid:
            print(f"⚠️  SRA Daemon 已在运行 (PID: {existing_pid})")
        else:
            print("⚠️  SRA Daemon 已在运行 (无法获取锁)")
        print("   使用 'sra stop' 停止，或 'sra restart' 重启")
        return
    
    # 检查是否已有 PID 文件（兼容旧版本残留）
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            lock.release()
            print(f"⚠️  SRA Daemon 已在运行 (PID: {pid})")
            print("   使用 'sra stop' 停止，或 'sra restart' 重启")
            return
        except (ProcessLookupError, ValueError):
            os.unlink(PID_FILE)

    # 启动守护进程
    pid = os.fork()
    # ⚠️ os.fork() + 线程不兼容风险: fork 后只有调用线程存活，
    # 其他线程中的锁状态未定义。已在子进程起始处调用
    # logging.basicConfig(force=True) 重新初始化日志系统。
    # 长期建议: 改用 multiprocessing.set_start_method('spawn')
    if pid > 0:
        # 父进程 — 写入 PID 到锁文件和 PID 文件
        config = load_config()
        http_port = config.get("http_port", 8536)
        
        # 将 PID 写入锁文件（供 get_lock_pid 查询）
        try:
            with open(LOCK_FILE, 'w') as f:
                f.write(str(pid))
        except OSError:
            pass
        
        with open(PID_FILE, 'w') as f:
            f.write(str(pid))
        
        print(f"✅ SRA Daemon 已启动 (PID: {pid})")
        print(f"   Unix Socket: {SOCKET_FILE}")
        print(f"   HTTP API: http://localhost:{http_port}")
        print(f"   日志: {LOG_FILE}")
        # 父进程退出，锁由子进程继承
    else:
        # 子进程
        os.setsid()
        # 重定向标准 I/O
        sys.stdin.close()
        sys.stdout = open(LOG_FILE, 'a')
        sys.stderr = open(LOG_FILE, 'a')

        # 初始化日志
        logging.basicConfig(
            level=getattr(logging, load_config().get("log_level", "INFO")),
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=[
                logging.StreamHandler(sys.stdout),
            ],
        )

        daemon = SRaDDaemon()
        daemon.start()

        # 保持运行
        while daemon.running:
            time.sleep(1)


def cmd_stop(args=None) -> None:
    """停止守护进程"""
    if not os.path.exists(PID_FILE):
        # 检查锁文件
        if os.path.exists(LOCK_FILE):
            try:
                lock = FileLock(LOCK_FILE, timeout=0)
                if lock.acquire():
                    # 能获取到锁 → 进程已经不在了
                    lock.release()
                    os.unlink(LOCK_FILE)
                    print("⚠️  SRA Daemon 未在运行（已清理残留锁文件）")
                    return
                else:
                    # 锁被持有但 PID 文件不存在 → 可能异常
                    print("⚠️  SRA Daemon 状态异常（有锁但无 PID 文件）")
                    print("   可以手动删除锁文件: rm -f ~/.sra/srad.lock")
                    return
            except Exception as e:
                logger.warning("锁文件检查失败: %s", e)
        print("⚠️  SRA Daemon 未在运行")
        return

    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        os.kill(pid, signal.SIGTERM)
        os.unlink(PID_FILE)
        # 清理锁文件
        if os.path.exists(LOCK_FILE):
            try:
                os.unlink(LOCK_FILE)
            except OSError:
                pass
        print(f"✅ SRA Daemon 已停止 (PID: {pid})")
    except ProcessLookupError:
        os.unlink(PID_FILE)
        if os.path.exists(LOCK_FILE):
            try:
                os.unlink(LOCK_FILE)
            except OSError:
                pass
        print("⚠️  SRA Daemon 进程不存在，已清理 PID 和锁文件")
    except Exception as e:
        print(f"❌ 停止失败: {e}")


def cmd_status(args=None) -> None:
    """查看守护进程状态"""
    if not os.path.exists(PID_FILE):
        # 检查状态文件
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE) as f:
                    status = json.load(f)
                print(f"📊 SRA Daemon 状态: {status.get('status', 'unknown')}")
                print(f"   最后更新: {status.get('updated_at', 'unknown')}")
                return
            except Exception as e:
                logger.warning("状态文件读取失败: %s", e)
        print("📭 SRA Daemon 未运行")
        return

    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)

        # 通过 Socket 查询实时状态
        try:
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.connect(SOCKET_FILE)
            client.sendall(json.dumps({"action": "stats"}).encode("utf-8"))
            response = client.recv(65536).decode("utf-8")
            client.close()
            data = json.loads(response)
            stats = data.get("stats", data)

            print(f"✅ SRA Daemon 运行中 (PID: {pid})")
            print(f"📊 运行统计:")
            skills = stats.get("skills_count", 0)
            print(f"   技能数: {skills}")
            print(f"   请求次数: {stats.get('total_requests', 0)}")
            print(f"   推荐次数: {stats.get('total_recommendations', 0)}")
            uptime = stats.get("uptime_seconds", 0)
            hours, remainder = divmod(uptime, 3600)
            minutes, seconds = divmod(remainder, 60)
            print(f"   运行时长: {hours}时{minutes}分{seconds}秒")
            print(f"   HTTP 端口: {stats.get('config', {}).get('http_port', 8536)}")
            return stats
        except Exception as e:
            print(f"✅ SRA Daemon 运行中 (PID: {pid})")
            print(f"⚠️  无法连接 Socket: {e}")
            return None

    except ProcessLookupError:
        os.unlink(PID_FILE)
        print("📭 SRA Daemon 进程已不存在，PID 文件已清理")
    except Exception as e:
        print(f"❌ 状态查询失败: {e}")


def cmd_restart(args=None) -> None:
    """重启守护进程"""
    cmd_stop(args)
    time.sleep(1)
    cmd_start(args)


def cmd_attach(args=None) -> None:
    """前台运行（调试）"""
    ensure_sra_home()
    
    # 同样检查文件锁
    lock = FileLock(LOCK_FILE, timeout=0)
    if not lock.acquire():
        existing_pid = lock.get_lock_pid()
        if existing_pid:
            print(f"⚠️  SRA Daemon 已在运行 (PID: {existing_pid})")
        else:
            print("⚠️  SRA Daemon 已在运行 (无法获取锁)")
        print("   使用 'sra stop' 停止")
        return
    
    config = load_config()
    daemon = SRaDDaemon(config)
    
    # 端口活性探测
    http_port = config.get("http_port", 8536)
    if check_port_in_use(http_port):
        print(f"⚠️  端口 {http_port} 已被占用，请检查是否有其他 SRA 实例")
        lock.release()
        return
    
    try:
        daemon.attach()
    finally:
        lock.release()


# ── systemd service 单元模板 ──────────────

SYSTEMD_SERVICE_SYS = """[Unit]
Description=SRA — Skill Runtime Advisor Daemon
Documentation=https://github.com/JackSmith111977/Hermes-Skill-View
After=network.target

[Service]
Type=simple
User=%s
ExecStart=%s attach
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=srad

[Install]
WantedBy=multi-user.target
"""

SYSTEMD_SERVICE_USER = """[Unit]
Description=SRA — Skill Runtime Advisor Daemon
Documentation=https://github.com/JackSmith111977/Hermes-Skill-View
After=network.target

[Service]
Type=simple
ExecStart=%s attach
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=srad

[Install]
WantedBy=default.target
"""


def cmd_install_service(args=None) -> None:
    """安装 systemd 服务

    支持 --user 标志生成用户级服务（无 sudo）。
    默认生成系统级服务（需 sudo）。
    """
    import getpass
    user = getpass.getuser()
    python_path = sys.executable
    sra_bin = os.path.join(os.path.dirname(python_path), "sra")

    # 解析 --user 标志
    is_user = args and any(a in ("--user", "-u") for a in args)

    if is_user:
        xdg_config = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        user_dir = os.path.join(xdg_config, "systemd", "user")
        service_path = os.path.join(user_dir, "srad.service")

        service_content = SYSTEMD_SERVICE_USER % (sra_bin,)

        os.makedirs(user_dir, exist_ok=True)
        with open(service_path, 'w') as f:
            f.write(service_content)

        print(f"📝 用户级 systemd 服务已创建: {service_path}")
        print(f"   SRA 路径: {sra_bin}")
        print()
        print("启动命令:")
        print(f"  systemctl --user daemon-reload")
        print(f"  systemctl --user enable --now srad")
        print()
        print("管理命令:")
        print(f"  systemctl --user status srad")
        print(f"  journalctl --user -u srad -f")
    else:
        service_content = SYSTEMD_SERVICE_SYS % (user, sra_bin)
        service_path = "/etc/systemd/system/srad.service"

        print(f"📝 将安装系统级 systemd 服务: {service_path}")
        print(f"   用户: {user}")
        print(f"   SRA 路径: {sra_bin}")
        print()
        print("需要 sudo 权限:")

        tmp_path = "/tmp/srad.service"
        with open(tmp_path, 'w') as f:
            f.write(service_content)
        print(f"   service 文件已生成: {tmp_path}")
        print()
        print("安装命令:")
        print(f"  sudo cp {tmp_path} {service_path}")
        print(f"  sudo systemctl daemon-reload")
        print(f"  sudo systemctl enable --now srad")
        print()
        print("管理命令:")
        print(f"  sudo systemctl status srad")
        print(f"  sudo journalctl -u srad -f")
