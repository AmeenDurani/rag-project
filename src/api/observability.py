"""Structured logging, request-ID propagation, per-stage timing, and cost
estimation for the API. Scoped to src/api/ - the CLI keeps its existing
direct-to-stdout human-readable output, a deliberate choice (see
progress/add-logging-and-tracing.md) rather than an oversight.
"""

import contextvars
import json
import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager

request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)

# Attributes every LogRecord has by default - anything else found on a record
# is a caller-supplied `extra` field and gets included in the JSON output.
_BASE_RECORD_ATTRS = set(
    logging.LogRecord(name="", level=0, pathname="", lineno=0, msg="", args=(), exc_info=None).__dict__.keys()
) | {"message", "asctime"}


class RequestIdFilter(logging.Filter):
    """Injects the current request's ID (from contextvars) into every log
    record - no request_id parameter needs to be threaded through
    retrieve()/generate()/embed_chunks() to make this work.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
        }
        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _BASE_RECORD_ATTRS and key != "request_id"
        }
        payload.update(extras)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


@contextmanager
def stage_timer(stages: dict[str, float], name: str) -> Iterator[None]:
    """Records elapsed wall-clock time for one named stage into `stages`,
    e.g. `with stage_timer(stages, "generate"): ...` sets stages["generate"]
    to the elapsed milliseconds. Callers log `stages` themselves in one
    consolidated summary line per request rather than one log line per
    stage - a single structured event per request is enough visibility at
    this project's scale, without building out full span/trace concepts.
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        stages[name] = round((time.perf_counter() - start) * 1000, 2)


# Dollars per 1M tokens, Anthropic first-party API pricing. Only the two
# models this project actually configures (src/config.py::generation_model)
# are listed - estimate_cost_usd() returns None for anything else rather
# than guessing, since a stale/wrong number is worse than an absent one.
PRICING_PER_MILLION_TOKENS = {
    "claude-sonnet-5": {"input": 2.00, "output": 10.00},
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
}


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float | None:
    prices = PRICING_PER_MILLION_TOKENS.get(model)
    if prices is None:
        return None

    cost = (input_tokens / 1_000_000) * prices["input"] + (output_tokens / 1_000_000) * prices["output"]
    return round(cost, 6)
