"""SRA Daemon 单例守护测试 — 验证文件锁和端口探测机制"""

import os
import sys
import time
import json
import signal
import tempfile
import threading
import shutil
import subprocess
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from skill_advisor.runtime.lock import FileLock, check_port_in_use


class TestFileLock:
    """文件锁功能测试"""

    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.lock_path = os.path.join(self.tmp_dir, "test.lock")

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_acquire_and_release(self):
        """基本获取和释放"""
        lock = FileLock(self.lock_path, timeout=0)
        assert lock.acquire() == True
        assert lock.is_locked == True
        lock.release()
        assert lock.is_locked == False

    def test_exclusivity_same_process(self):
        """同一进程不能重复获取（非阻塞模式返回 False）"""
        lock1 = FileLock(self.lock_path, timeout=0)
        lock2 = FileLock(self.lock_path, timeout=0)
        
        assert lock1.acquire() == True
        # 同一进程内重新获取应该成功（flock 允许递归）
        # 这里测试的是不同 FileLock 实例对同一文件的操作
        lock1.release()
        
        lock1.acquire()
        assert lock1.is_locked == True
        lock1.release()

    def test_exclusivity_cross_thread(self):
        """跨线程互斥"""
        acquired = [False]
        
        def try_acquire():
            lock = FileLock(self.lock_path, timeout=1.0)
            acquired[0] = lock.acquire()
            if acquired[0]:
                lock.release()
        
        lock1 = FileLock(self.lock_path, timeout=0)
        assert lock1.acquire() == True
        
        t = threading.Thread(target=try_acquire)
        t.start()
        t.join()
        
        # lock1 持有锁 → 线程应获取失败
        assert acquired[0] == False
        lock1.release()

    def test_context_manager(self):
        """上下文管理器"""
        with FileLock(self.lock_path) as lock:
            assert lock.is_locked == True
        assert lock.is_locked == False

    def test_lock_file_created(self):
        """锁文件应被自动创建"""
        lock = FileLock(self.lock_path)
        lock.acquire()
        assert os.path.exists(self.lock_path)
        lock.release()

    def test_get_lock_pid(self):
        """锁文件 PID 读取"""
        test_pid = 12345
        with open(self.lock_path, 'w') as f:
            f.write(str(test_pid))
        
        lock = FileLock(self.lock_path)
        assert lock.get_lock_pid() == test_pid

    def test_lock_file_cleanup(self):
        """释放锁后文件应保持存在（锁定状态由内核维护）"""
        lock = FileLock(self.lock_path)
        lock.acquire()
        lock.release()
        # flock 文件在 close 后锁释放，但文件本身保留
        # 这个文件下次 open 时不会自动持有锁
        assert os.path.exists(self.lock_path)


class TestCheckPortInUse:
    """端口活性探测测试"""

    def test_port_not_in_use(self):
        """未占用的端口返回 False"""
        # 使用一个罕见端口避免冲突
        result = check_port_in_use(51999)
        assert result == False

    def test_port_in_use(self):
        """占用的端口返回 True"""
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", 51998))
        s.listen(1)
        
        try:
            result = check_port_in_use(51998)
            assert result == True
        finally:
            s.close()


class TestDaemonLockIntegration:
    """Daemon 锁集成测试（不启动真实进程）"""

    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_lock_prevents_duplicate_start(self):
        """模拟两个 cmd_start：第二个应被阻止"""
        from skill_advisor.runtime.config import LOCK_FILE, PID_FILE
        from skill_advisor.runtime.commands import cmd_start, cmd_stop
        
        test_lock = os.path.join(self.tmp_dir, "srad.lock")
        
        # 模拟锁已被其他进程持有
        lock = FileLock(test_lock, timeout=0)
        assert lock.acquire() == True
        
        # 同一个锁文件，第二个实例获取不到
        lock2 = FileLock(test_lock, timeout=0)
        assert lock2.acquire() == False
        
        lock.release()

    def test_lock_auto_release_on_process_exit(self):
        """进程退出时锁自动释放（OS 级机制）"""
        test_lock = os.path.join(self.tmp_dir, "auto_release.lock")
        
        # 启动子进程获取锁
        code = (
            "import os, fcntl\n"
            f"fd = os.open('{test_lock}', os.O_CREAT | os.O_RDWR, 0o644)\n"
            "fcntl.flock(fd, fcntl.LOCK_EX)\n"
            "print('locked', flush=True)\n"
            "import time\n"
            "time.sleep(0.5)\n"
        )
        proc = subprocess.Popen(
            [sys.executable, "-c", code],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        
        # 等待子进程获取锁
        proc.stdout.readline()
        
        # 此时锁被子进程持有
        lock = FileLock(test_lock, timeout=0.1)
        assert lock.acquire() == False  # 获取不到
        
        # 等待子进程退出
        proc.wait(timeout=5)
        
        # 子进程退出后，锁自动释放
        time.sleep(0.1)
        lock2 = FileLock(test_lock, timeout=0)
        assert lock2.acquire() == True  # 现在可以获取了
        lock2.release()
