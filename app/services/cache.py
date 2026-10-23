import time
import threading
from functools import wraps
from typing import Any, Callable, Optional, Dict, Tuple

class SimpleTTLCache:
    """スレッドセーフで軽量なインメモリTTLキャッシュ。"""
    def __init__(self, default_ttl: int = 1800, maxsize: int = 128):
        self.default_ttl = default_ttl
        self.maxsize = maxsize
        self._cache: Dict[Any, Tuple[Any, float]] = {}
        self._lock = threading.Lock()

    def get(self, key: Any) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                return None
            val, expiry = self._cache[key]
            if time.time() > expiry:
                del self._cache[key]
                return None
            return val

    def set(self, key: Any, value: Any, ttl: Optional[int] = None) -> None:
        with self._lock:
            now = time.time()
            if len(self._cache) >= self.maxsize:
                # 期限切れのエントリを削除
                expired = [k for k, (_, exp) in self._cache.items() if now > exp]
                for k in expired:
                    del self._cache[k]
                # それでも上限を超えている場合は最古のエントリを削除
                if len(self._cache) >= self.maxsize:
                    oldest_k = next(iter(self._cache))
                    del self._cache[oldest_k]

            expiry = now + (ttl if ttl is not None else self.default_ttl)
            self._cache[key] = (value, expiry)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

def ttl_cache(ttl: int = 1800, maxsize: int = 128):
    """関数の戻り値を指定秒数キャッシュするデコレータ。"""
    cache = SimpleTTLCache(default_ttl=ttl, maxsize=maxsize)
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            cached = cache.get(key)
            if cached is not None:
                return cached
            result = func(*args, **kwargs)
            cache.set(key, result)
            return result
        wrapper.cache = cache
        return wrapper
    return decorator
