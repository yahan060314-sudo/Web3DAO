import threading
import queue
from typing import Any, Dict, Callable, Optional


class MessageBus:
    """
    一个简单的进程内消息总线，支持 topic 级别的发布/订阅。
    - 每个 topic 对应多个 Queue（广播模式，每个订阅者都有自己的队列）
    - Agent 可以阻塞式地从自己的订阅中取消息
    - 线程安全，适合在单机多线程环境中运行
    - 支持广播：一条消息会被发送到所有订阅者的队列
    """

    def __init__(self):
        # topic -> List[queue.Queue] (每个订阅者都有自己的队列)
        self._topics: Dict[str, list] = {}
        self._lock = threading.Lock()

    def publish(self, topic: str, message: Dict[str, Any]) -> None:
        """
        发布消息到指定 topic，所有订阅者都会收到
        """
        with self._lock:
            if topic in self._topics:
                # 广播到所有订阅者的队列
                for q in self._topics[topic]:
                    try:
                        q.put(message)
                    except Exception as e:
                        print(f"[MessageBus] ⚠️ 发布消息到队列失败: {e}")

    def subscribe(self, topic: str) -> "Subscription":
        """
        订阅 topic，返回一个订阅句柄
        每个订阅者都有自己的队列，确保都能收到消息
        """
        with self._lock:
            if topic not in self._topics:
                self._topics[topic] = []
            # 为每个订阅者创建独立的队列
            q = queue.Queue()
            self._topics[topic].append(q)
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

