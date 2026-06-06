"""线程安全 SSE 事件管理器 — 进程内广播"""
import queue
import json
import threading


class SSEManager:
    def __init__(self):
        self._clients: list[queue.Queue] = []
        self._lock = threading.Lock()

    def register(self) -> queue.Queue:
        """SSE 端点调用，返回该客户端的专属队列"""
        q = queue.Queue(maxsize=64)
        with self._lock:
            self._clients.append(q)
        return q

    def unregister(self, q: queue.Queue):
        """客户端断开时调用"""
        with self._lock:
            if q in self._clients:
                self._clients.remove(q)

    def broadcast(self, event_type: str, data: dict | None = None):
        """向所有已连接客户端推送事件（非阻塞）"""
        payload = json.dumps(
            {"type": event_type, "data": data or {}},
            ensure_ascii=False,
            default=str,
        )
        with self._lock:
            dead = []
            for q in self._clients:
                try:
                    q.put_nowait(payload)
                except queue.Full:
                    dead.append(q)  # 慢客户端，丢弃
            for q in dead:
                self._clients.remove(q)


# 模块级单例
sse_manager = SSEManager()
