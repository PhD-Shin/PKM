"""
단순 TTL 캐시 (인메모리) with LRU eviction
"""
import time
from typing import Any, Dict, Optional
from collections import OrderedDict


class TTLCache:
    def __init__(self, ttl_seconds: int = 30, maxsize: int = 1000):
        """
        TTL 기반 캐시 with LRU eviction

        Args:
            ttl_seconds: TTL in seconds
            maxsize: 최대 캐시 항목 수 (메모리 누수 방지)
        """
        self.ttl = ttl_seconds
        self.maxsize = maxsize
        self.store: OrderedDict[str, tuple] = OrderedDict()

    def get(self, key: str) -> Any:
        now = time.time()
        item = self.store.get(key)
        if not item:
            return None
        value, expires_at = item
        if expires_at < now:
            self.store.pop(key, None)
            return None
        # LRU: 접근 시 최신으로 이동
        self.store.move_to_end(key)
        return value

    def set(self, key: str, value: Any):
        expires_at = time.time() + self.ttl

        # 기존 키면 업데이트
        if key in self.store:
            self.store.pop(key)

        # maxsize 초과 시 가장 오래된 항목 제거 (LRU)
        if len(self.store) >= self.maxsize:
            self.store.popitem(last=False)

        self.store[key] = (value, expires_at)

    def clear(self, key: str):
        self.store.pop(key, None)

    def clear_prefix(self, prefix: str):
        for k in list(self.store.keys()):
            if k.startswith(prefix):
                self.store.pop(k, None)

    def clear_all(self):
        self.store.clear()
