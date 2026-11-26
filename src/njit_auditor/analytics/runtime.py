"""App-scoped, disabled-by-default configuration. No import-time I/O."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .collector import BoundedCollector, Clock, NoOpSink, Sink, SystemClock


@dataclass(frozen=True)
class AnalyticsSettings:
    enabled: bool = False
    database: Path | None = None

    @classmethod
    def from_environment(
        cls, *, public_web: bool, environment: str, test_mode: bool = False
    ) -> AnalyticsSettings:
        try:
            if test_mode or not public_web or environment != "production":
                return cls()
            if os.environ.get("NJIT_AUDITOR_ANALYTICS_ENABLED") != "1":
                return cls()
            value = os.environ.get("NJIT_AUDITOR_ANALYTICS_DB", "")
            path = Path(value)
            if not value or not path.is_absolute():
                return cls()
            return cls(True, path)
        except Exception:
            return cls()


class AnalyticsRuntime:
    def __init__(self, sink: Sink | None = None, clock: Clock | None = None) -> None:
        self.sink = sink if sink is not None else NoOpSink()
        self.clock = clock or SystemClock()

    def start(self) -> None:
        try:
            if isinstance(self.sink, BoundedCollector):
                self.sink.start()
        except Exception:
            self.sink = NoOpSink()

    def stop(self) -> None:
        try:
            if isinstance(self.sink, BoundedCollector):
                self.sink.stop()
        except Exception:
            pass


def build_runtime(
    settings: AnalyticsSettings, *, app_mode: str, clock: Clock | None = None
) -> AnalyticsRuntime:
    try:
        if (
            app_mode != "web"
            or settings.enabled is not True
            or settings.database is None
            or not settings.database.is_absolute()
        ):
            return AnalyticsRuntime()
        return AnalyticsRuntime(BoundedCollector(settings.database, clock), clock)
    except Exception:
        return AnalyticsRuntime()
