"""TTL-cached probes for external tool availability (Python 3.12+).

``pip --version`` and ``uv --version`` each spawn a subprocess (up to five
seconds when the tool is missing).  Refreshing the environment table used to
run one probe *per environment on the Tk main thread*, which is exactly the
kind of repeated blocking work that freezes a Tkinter window.

Probes therefore memoise their answer for a short window.  Use
``refresh=True`` where a fresh answer is mandatory (for example validating a
configuration change the user just made).
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any, cast

#: How long a probe result stays valid.  Tool availability/versions do not
#: change while the app runs, but a short window keeps external installs
#: (e.g. ``pip install uv``) visible without a restart.
DEFAULT_TTL_SECONDS = 60.0

_lock = threading.Lock()
_cache: dict[str, tuple[float, Any]] = {}


def probe[ValueT](
    key: str,
    factory: Callable[[], ValueT],
    *,
    refresh: bool = False,
    ttl: float = DEFAULT_TTL_SECONDS,
) -> ValueT:
    """Return a memoised probe result, running ``factory`` only when stale.

    Thread safe: cache reads/writes are serialised by a lock, so the probe
    itself (a subprocess) never runs while the cache is being mutated.
    """
    if not refresh:
        now = time.monotonic()
        with _lock:
            entry = _cache.get(key)
            if entry is not None and now - entry[0] < ttl:
                return cast(ValueT, entry[1])
    value = factory()
    with _lock:
        _cache[key] = (time.monotonic(), value)
    return value


def invalidate(*key_prefixes: str) -> None:
    """Drop cached probes — all of them, or only keys with a given prefix."""
    with _lock:
        if not key_prefixes:
            _cache.clear()
            return
        for key in [k for k in _cache if k.startswith(key_prefixes)]:
            del _cache[key]
