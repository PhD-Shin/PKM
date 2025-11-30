"""
단순 TTL 캐시 (인메모리)
"""
import time
from typing import Any, Dict


class TTLCache:
    def __init__(self, ttl_seconds: int = 30):
        self.ttl = ttl_seconds
        self.store: Dict[str, tuple] = {}

    def get(self, key: str) -> Any:
        now = time.time()
        item = self.store.get(key)
        if not item:
            return None
        value, expires_at = item
        if expires_at < now:
            self.store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any):
        expires_at = time.time() + self.ttl
        self.store[key] = (value, expires_at)

    def clear(self, key: str):
        self.store.pop(key, None)

    def clear_prefix(self, prefix: str):
        for k in list(self.store.keys()):
            if k.startswith(prefix):
                self.store.pop(k, None)

    def clear_all(self):
        self.store.clear()
