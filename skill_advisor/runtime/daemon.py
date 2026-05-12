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

import json
import logging
import os
import socket
import threading
import time
from datetime import datetime

from .. import __version__
from ..advisor import SkillAdvisor
from .config import STATUS_FILE, ensure_sra_home, load_config
from .force import FORCE_LEVELS, ForceLevelManager

logger = logging.getLogger("srad")


class SRaDDaemon:
    """SRA 守护进程"""

    def __init__(self, config: dict = None) -> None:
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
        self.force_manager = ForceLevelManager()  # 🆕 力度管理器

    # ── 生命周期 ──────────────────────────────

    def start(self) -> None:
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

    def stop(self) -> None:
        """停止守护进程"""
        self.running = False
        if self._server_socket:
            try:
                self._server_socket.close()
            except OSError:
                logger.debug("Socket close in stop: expected")
        self._update_status("stopped")
        logger.info("SRA Daemon 已停止")

    def attach(self) -> None:
        """前台运行（调试用）"""
        try:
            self.start()
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("收到中断信号")
            self.stop()

    # ── 内部服务 ──────────────────────────────

    def _run_socket_server(self) -> None:
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

    def _handle_socket_client(self, conn: socket.socket) -> None:
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

    def _run_http_server(self) -> None:
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
                    force_summary = self.daemon.force_manager.get_summary()
                    self._send_json({
                        "status": "ok",
                        "sra_engine": True,
                        "version": __version__,
                        "force_level": force_summary,  # 🆕
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
                    contract = result.get("contract", {})
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
                            rag_lines.append("\n  💡 建议: 可参考上述 skill")

                        rag_lines.append("── ──────────────────────────────────────────────")

                    # 🆕 契约信息
                    if contract and contract.get("confidence") != "low":
                        rag_lines.append("")
                        rag_lines.append("── [SRA 技能契约] ──────────────────────────────")
                        rag_lines.append(f"  📋 {contract.get('summary', '')}")
                        if contract.get("required_skills"):
                            rag_lines.append(f"  🔴 必须加载: {', '.join(contract['required_skills'])}")
                        if contract.get("optional_skills"):
                            rag_lines.append(f"  🟡 建议参考: {', '.join(contract['optional_skills'])}")
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
                        "contract": contract if contract.get("confidence") != "low" else {},
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
                    result = self.daemon._handle_validate(data)
                    self._send_json(result)
                elif self.path == "/force":
                    result = self.daemon._handle_force(data)
                    self._send_json(result)
                elif self.path == "/recheck":
                    result = self.daemon._handle_recheck(data)
                    self._send_json(result)
                elif self.path == "/stats":
                    result = self.daemon._handle_stats({})
                    self._send_json(result)
                elif self.path == "/stats/compliance" or self.path == "/compliance":
                    result = self.daemon._handle_stats_compliance({})
                    self._send_json(result)
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

    def _auto_refresh_loop(self) -> None:
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
                    with self._lock:
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
                        with self._lock:
                            self._last_refresh = time.time()
                        last_checksum = current_checksum
                    except Exception as e:
                        logger.error(f"变更刷新失败: {e}")

            time.sleep(5)  # 每 5 秒检查一次循环条件

    def _compute_skills_checksum(self) -> str:
        """计算技能目录的校验和（文件数量 + 所有 SKILL.md 的 mtime + 大小）

        用于快速检测技能目录是否有新增/删除/修改。
        零额外依赖，纯 Python 实现。
        """
        import glob
        import hashlib

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

    # ── 统一路由表 ──────────────────────────────
    # 所有 action → handler 映射在此注册
    # Socket 和 HTTP 共用此路由
    ROUTER = {
        "recommend": "_handle_recommend",
        "record": "_handle_record",
        "refresh": "_handle_refresh",
        "stats": "_handle_stats",
        "ping": "_handle_ping",
        "coverage": "_handle_coverage",
        "stats/compliance": "_handle_stats_compliance",
        "stop": "_handle_stop",
        "validate": "_handle_validate",
        "force": "_handle_force",
        "recheck": "_handle_recheck",
    }

    # ── 请求处理 ──────────────────────────────

    def _handle_request(self, request: dict) -> dict:
        """处理 API 请求（通过 ROUTER 分发）"""
        with self._lock:
            self._stats["total_requests"] += 1

        action = request.get("action", "")
        params = request.get("params", {})

        handler_name = self.ROUTER.get(action)
        if handler_name:
            handler = getattr(self, handler_name, None)
            if handler:
                return handler(params)
            logger.warning("路由表中有 action '%s' 但方法 %s 不存在", action, handler_name)

        return {"error": f"unknown action: {action}"}

    def _handle_recommend(self, params: dict) -> dict:
        """推荐处理"""
        query = params.get("query", "")
        if not query:
            return {"error": "missing query"}
        result = self.advisor.recommend(query)
        with self._lock:
            self._stats["total_recommendations"] += 1
        return {"status": "ok", "result": result}

    def _handle_record(self, params: dict) -> dict:
        """记录处理"""
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

    def _handle_refresh(self, params: dict) -> dict:
        """刷新索引"""
        count = self.advisor.refresh_index()
        return {"status": "ok", "count": count}

    def _handle_stats(self, params: dict) -> dict:
        """统计信息"""
        return {"status": "ok", "stats": self.get_stats()}

    def _handle_ping(self, params: dict) -> dict:
        """心跳检测"""
        return {"status": "ok", "pong": True}

    def _handle_coverage(self, params: dict) -> dict:
        """覆盖率分析"""
        result = self.advisor.analyze_coverage()
        return {"status": "ok", "result": result}

    def _handle_stats_compliance(self, params: dict) -> dict:
        """遵循率统计"""
        stats = self.advisor.get_compliance_stats()
        return {"status": "ok", "compliance": stats}

    def _handle_stop(self, params: dict) -> dict:
        """远程停止"""
        t = threading.Thread(target=self.stop, daemon=True)
        t.start()
        return {"status": "ok", "message": "stopping"}

    def _handle_validate(self, params: dict) -> dict:
        """工具调用前技能校验"""
        from .endpoints.validate import handle_validate
        force = self.force_manager
        params["_force_level"] = force.get_level()
        params["_monitored_tools"] = force.get_monitored_tools()
        return {"status": "ok", "result": handle_validate(params)}

    def _handle_force(self, params: dict) -> dict:
        """力度管理"""
        level = params.get("level", "")
        if not level:
            return {
                "status": "ok",
                "current_level": self.force_manager.get_summary(),
                "available_levels": list(FORCE_LEVELS.keys()),
            }
        if level not in FORCE_LEVELS:
            return {
                "error": f"无效的力度等级: {level}",
                "available": list(FORCE_LEVELS.keys()),
            }
        success = self.force_manager.set_level(level)
        if success:
            return {
                "status": "ok",
                "message": f"力度等级已切换为 {level}",
                "current_level": self.force_manager.get_summary(),
            }
        return {"error": "设置力度等级失败"}

    def _handle_recheck(self, params: dict) -> dict:
        """长任务上下文漂移重检"""
        summary = params.get("conversation_summary", "")
        if not summary:
            return {"error": "missing conversation_summary"}
        loaded_skills = params.get("loaded_skills", [])
        result = self.advisor.recheck(summary, loaded_skills)
        return {"status": "ok", "recheck": result}

    # ── 状态管理 ──────────────────────────────

    def get_stats(self) -> dict:
        """获取运行统计"""
        with self._lock:
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
                "force_level": self.force_manager.get_summary(),  # 🆕
                "config": {
                    k: v for k, v in self.config.items()
                    if k in ("http_port", "auto_refresh_interval", "enable_http", "enable_unix_socket")
                },
            }

    def _update_status(self, status: str) -> None:
        """更新状态文件（线程安全）"""
        ensure_sra_home()
        try:
            with self._lock:
                with open(STATUS_FILE, 'w') as f:
                    json.dump({
                        "status": status,
                        "pid": os.getpid(),
                        "updated_at": datetime.now().isoformat(),
                    }, f)
        except OSError as e:
            logger.warning("状态文件写入失败: %s", e)
