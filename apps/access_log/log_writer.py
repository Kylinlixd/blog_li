"""AccessLog 异步批量落库。

请求/响应路径只做一次内存入队（满了直接丢），由单个后台线程攒批写库，
避免每个 /api/ 请求在响应路径上同步阻塞一次 INSERT（2GB 小机器上
这是高并发时的主要吞吐瓶颈之一）。flush_access_log_queue 供测试与
进程退出前排空队列。
"""

import atexit
import logging
import queue
import threading
import time

logger = logging.getLogger(__name__)

_MAX_PENDING = 10_000
_FLUSH_INTERVAL = 1.0  # 秒
_FLUSH_BATCH = 200

_queue = queue.Queue(maxsize=_MAX_PENDING)
_lock = threading.Lock()
_worker_started = False


class _FlushSentinel:
    __slots__ = ("done",)

    def __init__(self):
        self.done = threading.Event()


def enqueue_access_log(entry):
    try:
        _queue.put_nowait(entry)
    except queue.Full:
        # 队列满说明写库能力已经跟不上流量，丢弃优于阻塞请求线程
        pass
    _ensure_worker()


def flush_access_log_queue(timeout=5):
    """同步排空队列（测试与优雅停机用）。返回是否在超时前排空。"""
    _ensure_worker()
    sentinel = _FlushSentinel()
    try:
        _queue.put(sentinel, timeout=timeout)
    except queue.Full:
        return False
    return sentinel.done.wait(timeout)


def _ensure_worker():
    global _worker_started
    if _worker_started:
        return
    with _lock:
        if _worker_started:
            return
        threading.Thread(target=_run_worker, name="access-log-writer", daemon=True).start()
        _worker_started = True


def _run_worker():
    while True:
        item = _queue.get()
        # 哨兵可能恰好排在队首：直接消化掉，绝不能混进批量数据里写库
        if isinstance(item, _FlushSentinel):
            item.done.set()
            continue
        batch = [item]
        deadline = time.monotonic() + _FLUSH_INTERVAL
        flush_now = False
        while len(batch) < _FLUSH_BATCH:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                item = _queue.get(timeout=remaining)
            except queue.Empty:
                break
            if isinstance(item, _FlushSentinel):
                flush_now = True
                item.done.set()
                break
            batch.append(item)

        if batch:
            _write_batch(batch)
        if flush_now:
            continue  # 立即进入下一轮等待，保证后续哨兵同样即时处理


def _write_batch(batch):
    # close_old_connections 必须在这里导入：批量落库跑在独立线程，
    # 连接老化检查随每次写库执行，避免测试环境与长驻线程里的连接堆积
    from django.db import close_old_connections
    from .models import AccessLog

    try:
        close_old_connections()
        AccessLog.objects.bulk_create([AccessLog(**entry) for entry in batch])
    except Exception:
        logger.warning("AccessLog 批量落库失败，丢弃 %d 条", len(batch), exc_info=True)
    finally:
        close_old_connections()


atexit.register(flush_access_log_queue, 2)
