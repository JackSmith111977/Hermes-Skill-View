"""
SRA Runtime Daemon — 稳定的后台技能推荐守护进程

功能:
  - Unix Socket / HTTP 双协议 API
  - 自动索引刷新（定时 + 文件变更监听）
  - 场景记忆自动持久化
  - 多 Agent 连接管理
  - 健康检查 / 统计上报

用法:
  srad start         启动守护进程
  srad stop          停止守护进程
  srad status        查看状态
  srad restart       重启
  srad attach        前台运行（调试用）
"""

import os
import sys
import json
import time
import socket
import threading
import logging
import signal
import atexit
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from ..advisor import SkillAdvisor
from ..indexer import SkillIndexer
from .. import __version__

from .lock import FileLock, check_port_in_use

logger = logging.getLogger("srad")


# ── 路径常量 ─────────────────────────────────
SRA_HOME = os.path.expanduser("~/.sra")
PID_FILE = os.path.join(SRA_HOME, "srad.pid")
LOCK_FILE = os.path.join(SRA_HOME, "srad.lock")
SOCKET_FILE = os.path.join(SRA_HOME, "srad.sock")
LOG_FILE = os.path.join(SRA_HOME, "srad.log")
STATUS_FILE = os.path.join(SRA_HOME, "srad.status.json")
CONFIG_FILE = os.path.join(SRA_HOME, "config.json")

# 默认配置
DEFAULT_CONFIG = {
    "skills_dir": os.path.expanduser("~/.hermes/skills"),
    "data_dir": os.path.join(SRA_HOME, "data"),
    "socket_path": SOCKET_FILE,
    "http_port": 8536,    # v1.1.0: Proxy 兼容端口
    "auto_refresh_interval": 3600,    # 自动刷新索引间隔（秒）
    "enable_http": True,
    "enable_unix_socket": True,
    "log_level": "INFO",
    "max_connections": 10,
    "watch_skills_dir": True,          # 监听技能目录变更
}


def ensure_sra_home():
    """确保 SRA 家目录存在"""
    os.makedirs(SRA_HOME, exist_ok=True)
    os.makedirs(os.path.join(SRA_HOME, "data"), exist_ok=True)
    os.makedirs(os.path.join(SRA_HOME, "logs"), exist_ok=True)


def load_config() -> dict:
    """加载配置"""
    ensure_sra_home()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                user_config = json.load(f)
            merged = {**DEFAULT_CONFIG, **user_config}
            return merged
        except Exception as e:
            logger.warning("配置文件加载失败: %s", e)
    return dict(DEFAULT_CONFIG)


def save_config(config: dict):
    """保存配置"""
    ensure_sra_home()
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


class SRaDDaemon:
    """SRA 守护进程"""

    def __init__(self, config: dict = None):
        self.config = config or load_config()
        self.advisor = SkillAdvisor(
            skills_dir=self.config["skills_dir"],
            data_dir=self.config["data_dir"],
        )
        self.running = False
        self._threads = []
        self._server_socket = None
        self._http_server = None
        self._last_refresh = 0
        self._stats = {
            "started_at": None,
            "total_requests": 0,
            "total_recommendations": 0,
            "errors": 0,
            "uptime_seconds": 0,
        }
        self._lock = threading.Lock()

    # ── 生命周期 ──────────────────────────────

    def start(self):
        """启动守护进程"""
        ensure_sra_home()
        self.running = True
        self._stats["started_at"] = datetime.now().isoformat()

        # 初始化索引
        logger.info("正在构建技能索引...")
        count = self.advisor.refresh_index()
        logger.info(f"技能索引就绪: {count} 个 skill")

        # 启动 Unix Socket 监听
        if self.config.get("enable_unix_socket"):
            t = threading.Thread(target=self._run_socket_server, daemon=True)
            t.start()
            self._threads.append(t)
            logger.info(f"Unix Socket 监听: {self.config['socket_path']}")

        # 启动 HTTP 服务器
        if self.config.get("enable_http"):
            t = threading.Thread(target=self._run_http_server, daemon=True)
            t.start()
            self._threads.append(t)
            logger.info(f"HTTP 监听: 0.0.0.0:{self.config['http_port']}")

        # 启动自动刷新
        t = threading.Thread(target=self._auto_refresh_loop, daemon=True)
        t.start()
        self._threads.append(t)
        logger.info(f"自动刷新间隔: {self.config.get('auto_refresh_interval', 3600)}s")

        # 写入状态
        self._update_status("running")

        logger.info("🚀 SRA Daemon 启动完成")

    def stop(self):
        """停止守护进程"""
        self.running = False
        if self._server_socket:
            try:
                self._server_socket.close()
            except OSError:
                logger.debug("Socket close in stop: expected")
        self._update_status("stopped")
        logger.info("SRA Daemon 已停止")

    def attach(self):
        """前台运行（调试用）"""
        try:
            self.start()
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("收到中断信号")
            self.stop()

    # ── 内部服务 ──────────────────────────────

    def _run_socket_server(self):
        """Unix Socket 服务器"""
        socket_path = self.config["socket_path"]
        # 清理旧 socket
        if os.path.exists(socket_path):
            os.unlink(socket_path)

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(socket_path)
        server.listen(self.config.get("max_connections", 10))
        server.settimeout(1.0)
        self._server_socket = server

        # 设置权限
        os.chmod(socket_path, 0o666)

        while self.running:
            try:
                conn, _ = server.accept()
                t = threading.Thread(
                    target=self._handle_socket_client,
                    args=(conn,),
                    daemon=True,
                )
                t.start()
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Socket 接受连接错误: {e}")

    def _handle_socket_client(self, conn: socket.socket):
        """处理 Unix Socket 客户端请求"""
        try:
            data = conn.recv(65536).decode("utf-8")
            if not data:
                return

            request = json.loads(data)
            response = self._handle_request(request)
            conn.sendall(json.dumps(response).encode("utf-8"))
        except json.JSONDecodeError:
            conn.sendall(json.dumps({"error": "invalid_json"}).encode("utf-8"))
        except Exception as e:
            logger.error(f"Socket 客户端处理错误: {e}")
            try:
                conn.sendall(json.dumps({"error": str(e)}).encode("utf-8"))
            except OSError:
                logger.debug("Socket send in error handler failed")
        finally:
            try:
                conn.close()
            except OSError:
                logger.debug("Socket close in finally: expected")

    def _run_http_server(self):
        """简易 HTTP 服务器（使用标准库）"""
        import http.server
        import socketserver

        port = self.config["http_port"]

        class SRAHTTPHandler(http.server.BaseHTTPRequestHandler):
            daemon = self

            def log_message(self, format, *args):
                logger.debug(f"HTTP: {format % args}")

            def _send_json(self, data, status=200):
                body = json.dumps(data, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path == "/health":
                    stats = self.daemon.get_stats()
                    self._send_json({"status": "ok", **stats})
                elif self.path == "/status":
                    stats = self.daemon.get_stats()
                    self._send_json({
                        "status": "ok",
                        "sra_engine": True,
                        "version": __version__,
                        "stats": {
                            "skills_scanned": stats.get("skills_count", 0),
                        },
                        "config": {
                            "host": "0.0.0.0",
                            "port": port,
                            "high_threshold": 80,
                            "medium_threshold": 40,
                        },
                    })
                elif self.path == "/stats":
                    stats = self.daemon.get_stats()
                    self._send_json(stats)
                elif self.path == "/stats/compliance":
                    stats = self.daemon.advisor.get_compliance_stats()
                    self._send_json({"status": "ok", "compliance": stats})
                elif self.path.startswith("/recommend"):
                    import urllib.parse
                    parsed = urllib.parse.urlparse(self.path)
                    params = urllib.parse.parse_qs(parsed.query)
                    query = params.get("q", [""])[0]
                    if query:
                        result = self.daemon.advisor.recommend(query)
                        self._send_json(result)
                    else:
                        self._send_json({"error": "missing q parameter"}, 400)
                else:
                    self._send_json({"error": "not_found"}, 404)

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                if length > 0:
                    body = self.rfile.read(length).decode("utf-8")
                    try:
                        data = json.loads(body)
                    except json.JSONDecodeError:
                        logger.debug("Invalid JSON in POST body, using empty dict")
                        data = {}
                else:
                    data = {}

                if self.path == "/recommend":
                    # 支持 query 和 message 两种字段（兼容 v1.0.0 和 v1.1.0）
                    query = data.get("message", data.get("query", "")).strip()
                    if not query:
                        self._send_json({"error": "missing query or message"}, 400)
                        return

                    result = self.daemon.advisor.recommend(query)
                    recs = result.get("recommendations", [])
                    timing_ms = result.get("processing_ms", 0)

                    # ── 构建 RAG 上下文（Proxy 兼容格式）────────────────
                    top_skill = None
                    should_auto_load = False
                    rag_lines = []

                    if recs:
                        top = recs[0]
                        top_skill = top["skill"]
                        score = top["score"]
                        should_auto_load = score >= 80

                        rag_lines.append("── [SRA Skill 推荐] ──────────────────────────────")
                        for i, r in enumerate(recs[:5]):
                            flag = "⭐" if i == 0 else "  "
                            conf = r["confidence"]
                            s_name = r["skill"]
                            s_score = r["score"]
                            s_reasons = " | ".join(r.get("reasons", [])[:2])
                            rag_lines.append(f"  {flag} [{conf:>6}] {s_name} ({s_score:.1f}分) — {s_reasons}")

                        if should_auto_load:
                            rag_lines.append(f"\n  ⚡ 强推荐自动加载: {top_skill}")
                        else:
                            rag_lines.append(f"\n  💡 建议: 可参考上述 skill")

                        rag_lines.append("── ──────────────────────────────────────────────")

                    rag_context = "\n".join(rag_lines)

                    self._send_json({
                        "rag_context": rag_context,
                        "recommendations": [
                            {
                                "skill": r["skill"],
                                "score": r["score"],
                                "confidence": r["confidence"],
                                "reasons": r.get("reasons", []),
                                "description": r.get("description", ""),
                            }
                            for r in recs[:5]
                        ],
                        "top_skill": top_skill,
                        "should_auto_load": should_auto_load,
                        "timing_ms": timing_ms,
                        "provider_latency_ms": timing_ms,
                        "sra_available": True,
                        "sra_version": __version__,
                    })
                elif self.path == "/record":
                    skill = data.get("skill", "")
                    action = data.get("action", "")  # viewed/used/skipped
                    if action:
                        # 新式：轨迹追踪
                        if action == "viewed":
                            self.daemon.advisor.record_view(skill)
                        elif action == "used":
                            self.daemon.advisor.record_use(skill)
                        elif action == "skipped":
                            reason = data.get("reason", "")
                            self.daemon.advisor.record_skip(skill, reason)
                        else:
                            self._send_json({"error": f"unknown action: {action}"}, 400)
                            return
                        self._send_json({"status": "ok"})
                    elif skill and data.get("input", ""):
                        # 旧式：记录推荐采纳
                        accepted = data.get("accepted", True)
                        self.daemon.advisor.record_usage(skill, data["input"], accepted)
                        self._send_json({"status": "ok"})
                    else:
                        self._send_json({"error": "missing skill or input"}, 400)
                elif self.path == "/refresh":
                    count = self.daemon.advisor.refresh_index()
                    self._send_json({"status": "ok", "count": count})
                elif self.path == "/validate":
                    from ..endpoints.validate import handle_validate
                    result = handle_validate(data)
                    self._send_json(result)
                elif self.path == "/recheck":
                    summary = data.get("conversation_summary", "")
                    if not summary:
                        self._send_json({"error": "missing conversation_summary"}, 400)
                        return
                    loaded_skills = data.get("loaded_skills", [])
                    result = self.daemon.advisor.recheck(summary, loaded_skills)
                    self._send_json({"status": "ok", "recheck": result})
                else:
                    self._send_json({"error": "not_found"}, 404)

        # 使用 ThreadingHTTPServer 支持并发
        class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
            allow_reuse_address = True
            daemon_threads = True

        server = ThreadedHTTPServer(("0.0.0.0", port), SRAHTTPHandler)
        server.timeout = 0.5  # 允许线程可中断
        self._http_server = server
        logger.info(f"HTTP API: http://0.0.0.0:{port}")

        # 使用 serve_forever() 让 ThreadingMixIn 真正生效
        # 在独立线程中运行，不阻塞主循环
        import threading as _threading
        http_thread = _threading.Thread(
            target=server.serve_forever,
            daemon=True,
        )
        http_thread.start()

        # 监听 running 状态，用于优雅关闭
        while self.running:
            try:
                http_thread.join(timeout=1.0)
            except KeyboardInterrupt:
                break
        
        server.shutdown()
        logger.info("HTTP 服务器已关闭")

    def _auto_refresh_loop(self):
        """自动刷新循环 — 双模式：定时刷新 + 文件变更检测"""
        interval = self.config.get("auto_refresh_interval", 3600)
        
        # 文件变更检测：每 30 秒检查技能目录的校验和
        watch_enabled = self.config.get("watch_skills_dir", True)
        watch_interval = 30  # 每 30 秒检测一次
        
        # 初始化文件校验和
        last_checksum = self._compute_skills_checksum()
        
        last_timer_refresh = time.time()
        
        while self.running:
            # 模式1: 定时刷新（优先级高）
            if time.time() - last_timer_refresh >= interval:
                try:
                    logger.info("定时刷新技能索引...")
                    count = self.advisor.refresh_index()
                    logger.info(f"索引刷新完成: {count} 个 skill")
                    self._last_refresh = time.time()
                    last_timer_refresh = time.time()
                    # 刷新后更新校验和
                    last_checksum = self._compute_skills_checksum()
                except Exception as e:
                    logger.error(f"索引刷新失败: {e}")
            
            # 模式2: 文件变更检测（仅当 watch_skills_dir 启用时）
            if watch_enabled and time.time() - self._last_refresh >= watch_interval:
                current_checksum = self._compute_skills_checksum()
                if current_checksum != last_checksum:
                    logger.info("检测到技能目录变更，自动刷新索引...")
                    try:
                        count = self.advisor.refresh_index()
                        logger.info(f"变更刷新完成: {count} 个 skill")
                        self._last_refresh = time.time()
                        last_checksum = current_checksum
                    except Exception as e:
                        logger.error(f"变更刷新失败: {e}")
            
            time.sleep(5)  # 每 5 秒检查一次循环条件

    def _compute_skills_checksum(self):
        """计算技能目录的校验和（文件数量 + 所有 SKILL.md 的 mtime + 大小）
        
        用于快速检测技能目录是否有新增/删除/修改。
        零额外依赖，纯 Python 实现。
        """
        import hashlib
        import glob
        
        skills_dir = self.config.get("skills_dir", "")
        if not skills_dir or not os.path.exists(skills_dir):
            return ""
        
        try:
            files = sorted(glob.glob(os.path.join(skills_dir, '**/SKILL.md'), recursive=True))
            # 计算稳健的校验和：文件名 + mtime + 文件大小
            checksum_parts = []
            for f in files:
                try:
                    stat = os.stat(f)
                    checksum_parts.append(f"{f}:{stat.st_mtime}:{stat.st_size}")
                except OSError:
                    checksum_parts.append(f)
            return hashlib.md5("|".join(checksum_parts).encode()).hexdigest()
        except Exception as e:
            logger.warning(f"计算技能目录校验和失败: {e}")
            return ""

    # ── 请求处理 ──────────────────────────────

    def _handle_request(self, request: dict) -> dict:
        """处理 API 请求"""
        with self._lock:
            self._stats["total_requests"] += 1

        action = request.get("action", "")
        params = request.get("params", {})

        if action == "recommend":
            query = params.get("query", "")
            if not query:
                return {"error": "missing query"}
            result = self.advisor.recommend(query)
            with self._lock:
                self._stats["total_recommendations"] += 1
            return {"status": "ok", "result": result}

        elif action == "record":
            skill = params.get("skill", "")
            action_type = params.get("action", "")  # viewed/used/skipped
            if action_type:
                if action_type == "viewed":
                    self.advisor.record_view(skill)
                elif action_type == "used":
                    self.advisor.record_use(skill)
                elif action_type == "skipped":
                    reason = params.get("reason", "")
                    self.advisor.record_skip(skill, reason)
                else:
                    return {"error": f"unknown action: {action_type}"}
                return {"status": "ok"}
            # 旧式：记录推荐采纳
            user_input = params.get("input", "")
            accepted = params.get("accepted", True)
            self.advisor.record_usage(skill, user_input, accepted)
            return {"status": "ok"}

        elif action == "refresh":
            count = self.advisor.refresh_index()
            return {"status": "ok", "count": count}

        elif action == "stats":
            return {"status": "ok", "stats": self.get_stats()}

        elif action == "ping":
            return {"status": "ok", "pong": True}

        elif action == "coverage":
            result = self.advisor.analyze_coverage()
            return {"status": "ok", "result": result}

        elif action == "stats/compliance":
            stats = self.advisor.get_compliance_stats()
            return {"status": "ok", "compliance": stats}

        elif action == "stop":
            # 远程停止
            t = threading.Thread(target=self.stop, daemon=True)
            t.start()
            return {"status": "ok", "message": "stopping"}

        elif action == "validate":
            from ..endpoints.validate import handle_validate
            return {"status": "ok", "result": handle_validate(params)}

        elif action == "recheck":
            summary = params.get("conversation_summary", "")
            if not summary:
                return {"error": "missing conversation_summary"}
            loaded_skills = params.get("loaded_skills", [])
            result = self.advisor.recheck(summary, loaded_skills)
            return {"status": "ok", "recheck": result}

        else:
            return {"error": f"unknown action: {action}"}

    # ── 状态管理 ──────────────────────────────

    def get_stats(self) -> dict:
        """获取运行统计"""
        uptime = 0
        if self._stats["started_at"]:
            try:
                start = datetime.fromisoformat(self._stats["started_at"])
                uptime = int((datetime.now() - start).total_seconds())
            except Exception:
                logger.debug("Could not parse start time, uptime=0")

        return {
            "version": __version__,
            "status": "running" if self.running else "stopped",
            "uptime_seconds": uptime,
            "skills_count": len(self.advisor.indexer.get_skills()),
            "total_requests": self._stats["total_requests"],
            "total_recommendations": self._stats["total_recommendations"],
            "errors": self._stats["errors"],
            "last_refresh": self._last_refresh,
            "config": {
                k: v for k, v in self.config.items()
                if k in ("http_port", "auto_refresh_interval", "enable_http", "enable_unix_socket")
            },
        }

    def _update_status(self, status: str):
        """更新状态文件"""
        ensure_sra_home()
        try:
            with open(STATUS_FILE, 'w') as f:
                json.dump({
                    "status": status,
                    "pid": os.getpid(),
                    "updated_at": datetime.now().isoformat(),
                }, f)
        except OSError as e:
            logger.warning("状态文件写入失败: %s", e)


# ── 命令行接口 ─────────────────────────────

def cmd_start(args=None):
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


def cmd_stop(args=None):
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


def cmd_status(args=None):
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


def cmd_restart(args=None):
    """重启守护进程"""
    cmd_stop(args)
    time.sleep(1)
    cmd_start(args)


def cmd_attach(args=None):
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


def cmd_install_service(args=None):
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
