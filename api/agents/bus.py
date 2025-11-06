import threading
import queue
from typing import Any, Dict, Callable, Optional


class MessageBus:
    """
    一个简单的进程内消息总线，支持 topic 级别的发布/订阅。
    - 每个 topic 都对应一个 Queue
    - Agent 可以阻塞式地从自己的订阅中取消息
    - 线程安全，适合在单机多线程环境中运行
    """

    def __init__(self):
        self._topics: Dict[str, queue.Queue] = {}
        self._lock = threading.Lock()

    def get_topic(self, name: str) -> queue.Queue:
        with self._lock:
            if name not in self._topics:
                self._topics[name] = queue.Queue()
            return self._topics[name]

    def publish(self, topic: str, message: Dict[str, Any]) -> None:
        q = self.get_topic(topic)
        q.put(message)

    def subscribe(self, topic: str) -> "Subscription":
        q = self.get_topic(topic)
        return Subscription(q)


class Subscription:
    """
    订阅句柄，封装对 Queue 的阻塞式读取。
    """

    def __init__(self, q: queue.Queue):
        self._q = q

    def recv(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        try:
            return self._q.get(timeout=timeout)
        except queue.Empty:
            return None

