"""
SRA 文件锁工具模块 — 基于 fcntl.flock 的 OS 级原子锁

提供进程级别的互斥锁，用于确保 SRA Daemon 单例运行。
核心特性：
- OS 级原子性：通过 fcntl.flock 实现，不依赖 PID 文件检查的竞态条件
- 自动释放：进程退出时内核自动释放文件锁
- 超时机制：支持非阻塞获取（设置 timeout 参数）
- 兼容 POSIX 系统（Linux/macOS）
"""

import fcntl
import logging
import os
import time
from typing import Optional

logger = logging.getLogger("sra.lock")


class FileLock:
    """基于 fcntl.flock 的文件锁"""

    def __init__(self, lock_path: str, timeout: float = 0):
        """
        Args:
            lock_path: 锁文件路径
            timeout: 获取锁的超时时间（秒）。0 表示非阻塞尝试一次，-1 表示阻塞等待
        """
        self.lock_path = lock_path
        self.timeout = timeout
        self._fd: Optional[int] = None
        self._locked = False

    def acquire(self) -> bool:
        """尝试获取锁

        Returns:
            True 表示成功获取锁，False 表示获取失败（其他进程持有锁）

        Raises:
            OSError: 锁文件路径无效或权限错误
        """
        if self._locked:
            return True

        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.lock_path), exist_ok=True)
            # O_CREAT: 文件不存在则创建
            # O_RDWR: 读写模式（flock 需要可写 fd）
            self._fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR, 0o644)
        except OSError as e:
            logger.error("无法创建锁文件 %s: %s", self.lock_path, e)
            return False

        try:
            if self.timeout < 0:
                # 阻塞模式
                fcntl.flock(self._fd, fcntl.LOCK_EX)
                self._locked = True
                return True
            elif self.timeout == 0:
                # 非阻塞模式
                try:
                    fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    self._locked = True
                    return True
                except BlockingIOError:
                    return False
            else:
                # 超时模式：轮询获取
                deadline = time.time() + self.timeout
                while time.time() < deadline:
                    try:
                        fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        self._locked = True
                        return True
                    except BlockingIOError:
                        time.sleep(0.1)
                return False
        except OSError as e:
            logger.error("flock 操作失败 %s: %s", self.lock_path, e)
            self._cleanup()
            return False

    def release(self):
        """释放锁"""
        if not self._locked or self._fd is None:
            return
        try:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
        except OSError as e:
            logger.warning("释放锁失败 %s: %s", self.lock_path, e)
        finally:
            self._locked = False
            self._cleanup()

    def _cleanup(self):
        """清理文件描述符"""
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

    @property
    def is_locked(self) -> bool:
        """是否持有锁"""
        return self._locked

    def get_lock_pid(self) -> Optional[int]:
        """尝试读取锁文件中的 PID（不保证准确，仅供参考）"""
        try:
            if os.path.exists(self.lock_path):
                with open(self.lock_path) as f:
                    content = f.read().strip()
                    if content:
                        return int(content)
        except (ValueError, OSError):
            pass
        return None


def check_port_in_use(port: int, host: str = "0.0.0.0") -> bool:
    """检查端口是否已被占用

    通过尝试建立 TCP 连接到目标端口来判断。
    适用于 HTTP 端口绑定前的活性探测。

    Args:
        port: 端口号
        host: 主机地址

    Returns:
        True 表示端口已被占用
    """
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.0)
        result = s.connect_ex((host, port))
        s.close()
        return result == 0
    except OSError:
        return False
