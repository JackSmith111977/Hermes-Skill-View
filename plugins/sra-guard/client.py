"""
SRA Daemon 通信客户端 — HTTP + Unix Socket 双协议

提供 SraClient 类，封装与 SRA Daemon 的所有通信。
HTTP（httpx）优先，失败自动降级到 Unix Socket。

所有异常被捕获并记录，绝不向上传播。
"""

from __future__ import annotations

import json
import logging
import os
import socket
from typing import Any, Dict, List, Optional

logger = logging.getLogger("sra-guard.client")

# 默认地址
DEFAULT_HTTP_URL = "http://127.0.0.1:8536"
DEFAULT_SOCKET_PATH = os.path.expanduser("~/.sra/srad.sock")
DEFAULT_TIMEOUT = 2.0


class SraClient:
    """SRA Daemon 通信客户端

    双协议自适应：
      1. HTTP (httpx) — 主协议
      2. Unix Socket — 降级备选

    用法::

        client = SraClient()
        ctx = client.recommend("帮我画架构图")
        if ctx:
            print(f"推荐: {ctx}")
    """

    def __init__(
        self,
        http_url: str = DEFAULT_HTTP_URL,
        socket_path: str = DEFAULT_SOCKET_PATH,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.http_url = http_url.rstrip("/")
        self.socket_path = socket_path
        self.timeout = timeout

    # ── 公开 API ───────────────────────────────────────────

    def recommend(self, message: str) -> str:
        """获取技能推荐上下文

        Args:
            message: 用户消息

        Returns:
            rag_context 字符串，无推荐或失败时返回空字符串
        """
        if not message or not message.strip():
            return ""

        data = self._request("/recommend", {"message": message})
        if not data:
            return ""
        return data.get("rag_context", "")

    def validate(
        self,
        tool: str,
        args: Dict[str, Any],
        loaded_skills: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """校验工具调用

        Args:
            tool: 工具名称 (write_file, patch, terminal, execute_code)
            args: 工具参数
            loaded_skills: 已加载的技能列表

        Returns:
            {"compliant": bool, "missing": [], "severity": "info", "message": ""}
        """
        data = self._request("/validate", {
            "tool": tool,
            "args": args,
            "loaded_skills": loaded_skills or [],
        })
        if not data:
            return {"compliant": True, "missing": [], "severity": "info", "message": ""}
        return {
            "compliant": data.get("compliant", True),
            "missing": data.get("missing", []),
            "severity": data.get("severity", "info"),
            "message": data.get("message", ""),
        }

    def record(self, skill: str, action: str) -> bool:
        """记录技能使用轨迹

        Args:
            skill: 技能名称
            action: 操作类型 (viewed/used/skipped)

        Returns:
            是否记录成功
        """
        data = self._request("/record", {"skill": skill, "action": action})
        return data is not None and data.get("status") == "ok"

    def health(self) -> bool:
        """检查 SRA Daemon 是否可用

        Returns:
            True 表示 SRA Daemon 正常运行
        """
        data = self._request_http("GET", "/health")
        if data:
            return data.get("status") in ("ok", "running")
        return False

    # ── 内部请求 ───────────────────────────────────────────

    def _request(self, endpoint: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """发送请求 — HTTP 优先，Socket 降级"""
        # HTTP 优先
        result = self._request_http("POST", endpoint, payload)
        if result is not None:
            if "error" not in result:
                return result
            logger.debug("HTTP %s 返回错误: %s，降级到 Socket", endpoint, result.get("error"))

        # Socket 降级
        result = self._request_socket(endpoint, payload)
        if result is not None and "error" not in result:
            return result
        return None

    def _request_http(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """HTTP 请求（使用 httpx）"""
        try:
            import httpx

            url = f"{self.http_url}{endpoint}"
            with httpx.Client(timeout=self.timeout) as client:
                if method == "GET":
                    resp = client.get(url)
                else:
                    resp = client.post(url, json=payload or {})

                if resp.status_code == 200:
                    return resp.json()
                logger.debug("HTTP %s %s -> %d", method, url, resp.status_code)
                return None
        except ImportError:
            logger.warning("httpx 不可用，跳过 HTTP 请求")
            return None
        except Exception as exc:
            logger.debug("HTTP 请求失败: %s", exc)
            return None

    def _request_socket(
        self,
        endpoint: str,
        payload: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Unix Socket 请求"""
        if not os.path.exists(self.socket_path):
            logger.debug("Socket 文件不存在: %s", self.socket_path)
            return None

        # Socket 端需要 action/params 格式
        action = endpoint.lstrip("/")  # /recommend → recommend
        request = {"action": action, "params": payload}

        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect(self.socket_path)
            sock.sendall(json.dumps(request).encode("utf-8"))
            response = sock.recv(65536).decode("utf-8")
            sock.close()

            result = json.loads(response)
            if "error" in result:
                logger.debug("Socket %s 返回错误: %s", endpoint, result["error"])
                return None
            # Socket 响应包装在 {"status": "ok", "result": {...}}
            inner = result.get("result", result)
            if isinstance(inner, dict):
                return inner
            return result
        except Exception as exc:
            logger.debug("Socket 请求失败: %s", exc)
            return None
