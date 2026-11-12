"""
Whether the main application finished starting up.

/healthz is served by the metrics app on a separate port, so it keeps answering
even when the main app's startup failed. It reads this flag so the health check
reports what callers of the main app actually see.
"""

_ready = False


def set_ready(ready: bool) -> None:
    global _ready
    _ready = ready


def is_ready() -> bool:
    return _ready
