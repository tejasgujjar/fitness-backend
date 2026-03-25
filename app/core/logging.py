from __future__ import annotations

import logging
import sys
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Adds record.request_id from context for use in format strings."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get("-")
        return True


def setup_logging() -> None:
    fmt = "%(levelname)-5s [request_id=%(request_id)s] [%(name)s] %(message)s"
    formatter = logging.Formatter(fmt)

    request_id_filter = RequestIdFilter()

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    if not root.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(formatter)
        handler.addFilter(request_id_filter)
        root.addHandler(handler)
    else:
        for h in root.handlers:
            h.setFormatter(formatter)
            if not any(isinstance(f, RequestIdFilter) for f in h.filters):
                h.addFilter(request_id_filter)

    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        log = logging.getLogger(name)
        for h in log.handlers:
            h.setFormatter(formatter)
            if not any(isinstance(f, RequestIdFilter) for f in h.filters):
                h.addFilter(request_id_filter)
        if not log.handlers:
            log.propagate = True
