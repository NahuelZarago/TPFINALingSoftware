"""Metaclase Singleton thread-safe."""

from __future__ import annotations

import threading
from typing import Any, ClassVar


class SingletonMeta(type):
    """Metaclase que garantiza una única instancia por clase."""

    _instances: ClassVar[dict[type, Any]] = {}
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        """Devuelve la instancia única, creándola si no existe."""
        with SingletonMeta._lock:
            if cls not in SingletonMeta._instances:
                SingletonMeta._instances[cls] = super().__call__(*args, **kwargs)
            return SingletonMeta._instances[cls]

    @classmethod
    def reset(mcs, cls: type | None = None) -> None:
        """Descarta instancias (útil en tests)."""
        with mcs._lock:
            if cls is None:
                mcs._instances.clear()
            else:
                mcs._instances.pop(cls, None)
