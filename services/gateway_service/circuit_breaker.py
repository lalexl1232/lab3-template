import time
import asyncio
from typing import Callable, Any, Optional
from dataclasses import dataclass
import inspect


@dataclass
class CircuitBreakerStats:
    failures: int = 0
    success: int = 0
    last_failure_time: Optional[float] = None
    state: str = "CLOSED"  # CLOSED, OPEN, HALF_OPEN


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        name: str = "default"
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.name = name
        self.stats = CircuitBreakerStats()

    async def call(self, func: Callable, *args, fallback: Optional[Callable] = None, **kwargs) -> Any:
        if self.stats.state == "OPEN":
            if self._should_attempt_reset():
                self.stats.state = "HALF_OPEN"
            else:
                if fallback:
                    if asyncio.iscoroutinefunction(fallback):
                        return await fallback()
                    return fallback()
                raise Exception(f"Circuit breaker {self.name} is OPEN")

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            if fallback:
                if asyncio.iscoroutinefunction(fallback):
                    return await fallback()
                return fallback()
            raise e

    def _on_success(self):
        self.stats.failures = 0
        if self.stats.state == "HALF_OPEN":
            self.stats.state = "CLOSED"

    def _on_failure(self):
        self.stats.failures += 1
        self.stats.last_failure_time = time.time()

        if self.stats.failures >= self.failure_threshold:
            self.stats.state = "OPEN"

    def _should_attempt_reset(self) -> bool:
        if self.stats.last_failure_time is None:
            return False

        return (time.time() - self.stats.last_failure_time) >= self.timeout

    def get_state(self) -> dict:
        return {
            "name": self.name,
            "state": self.stats.state,
            "failures": self.stats.failures,
            "last_failure_time": self.stats.last_failure_time
        }


class CircuitBreakerManager:
    def __init__(self):
        self.breakers: dict[str, CircuitBreaker] = {}

    def get_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout: float = 60.0
    ) -> CircuitBreaker:
        if name not in self.breakers:
            self.breakers[name] = CircuitBreaker(
                failure_threshold=failure_threshold,
                timeout=timeout,
                name=name
            )
        return self.breakers[name]

    def get_all_states(self) -> dict:
        return {
            name: breaker.get_state()
            for name, breaker in self.breakers.items()
        }
