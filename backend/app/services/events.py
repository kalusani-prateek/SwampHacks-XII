"""In-process publish/subscribe for live updates (Server-Sent Events at /api/alerts/stream)."""
import queue
import threading


class EventBus:
    def __init__(self):
        self._subscribers = set()
        self._lock = threading.Lock()

    def subscribe(self):
        q = queue.Queue(maxsize=100)
        with self._lock:
            self._subscribers.add(q)
        return q

    def unsubscribe(self, q):
        with self._lock:
            self._subscribers.discard(q)

    def publish(self, event):
        """Send an event (a dict) to every connected client; slow clients just miss events."""
        with self._lock:
            subscribers = list(self._subscribers)
        for q in subscribers:
            try:
                q.put_nowait(event)
            except queue.Full:
                pass


bus = EventBus()
