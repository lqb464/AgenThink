import logging
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("agenthink")


@dataclass
class TraceEvent:
    name: str
    detail: str
    duration_ms: float


@dataclass
class RequestTrace:
    request_id: str
    events: list[TraceEvent] = field(default_factory=list)
    estimated_cost_usd: float = 0.0

    def add(self, name: str, detail: str, duration_ms: float = 0.0) -> None:
        self.events.append(TraceEvent(name=name, detail=detail, duration_ms=duration_ms))
        logger.info(
            "trace=%s event=%s duration_ms=%.2f detail=%s",
            self.request_id,
            name,
            duration_ms,
            detail,
        )

    def add_cost(self, amount: float) -> None:
        self.estimated_cost_usd += amount

    def summary(self) -> dict:
        return {
            "request_id": self.request_id,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "events": [
                {
                    "name": event.name,
                    "detail": event.detail,
                    "duration_ms": round(event.duration_ms, 2),
                }
                for event in self.events
            ],
        }


def new_trace() -> RequestTrace:
    return RequestTrace(request_id=str(uuid.uuid4())[:8])


@contextmanager
def timed_event(trace: RequestTrace, name: str, detail: str = ""):
    started = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000
        trace.add(name, detail, elapsed_ms)
