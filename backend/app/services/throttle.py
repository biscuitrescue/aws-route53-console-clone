"""Throttling of failed sign-ins, counted in memory over a sliding window.

The counters live in this process. That fits the deployment, which runs one worker; with
several workers each would count separately, and a restart forgets every count.
"""

import threading
import time
from collections import deque
from collections.abc import Callable

from app.errors import TooManyRequestsError

# Counters for at most this many keys are kept; beyond it the stalest are dropped, so
# a flood of distinct keys cannot grow the table without bound.
_MAX_KEYS = 50_000


class SlidingWindowCounter:
    """Counts events per key over the last ``window`` seconds."""

    def __init__(
        self, limit: int, window: float, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.limit = limit
        self.window = window
        self.clock = clock
        self._events: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _live(self, key: str, now: float) -> deque[float] | None:
        events = self._events.get(key)
        if events is None:
            return None
        while events and events[0] <= now - self.window:
            events.popleft()
        if not events:
            del self._events[key]
            return None
        return events

    def retry_after(self, key: str) -> float:
        """Seconds until ``key`` is under the limit again; zero when it already is."""
        if self.limit <= 0:
            return 0.0
        now = self.clock()
        with self._lock:
            events = self._live(key, now)
            if events is None or len(events) < self.limit:
                return 0.0
            # The oldest of the last ``limit`` events has to leave the window first.
            return max(0.0, events[-self.limit] + self.window - now)

    def add(self, key: str) -> None:
        if self.limit <= 0:
            return
        now = self.clock()
        with self._lock:
            if key not in self._events and len(self._events) >= _MAX_KEYS:
                self._evict(now)
            self._events.setdefault(key, deque()).append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._events.pop(key, None)

    def _evict(self, now: float) -> None:
        for key in list(self._events):
            self._live(key, now)
        overflow = len(self._events) - _MAX_KEYS + 1
        if overflow > 0:
            stalest = sorted(self._events, key=lambda key: self._events[key][-1])[:overflow]
            for key in stalest:
                del self._events[key]


class LoginThrottle:
    """Refuses further sign-in attempts after repeated failures.

    Failures are counted per client address and account together, so guessing one
    account's password is slowed down without letting anyone lock other people out of
    it, and per client address alone, so trying many accounts is slowed down too. The
    check does not depend on whether the account exists.
    """

    def __init__(
        self,
        *,
        max_failures: int,
        max_failures_per_client: int,
        window: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._per_account = SlidingWindowCounter(max_failures, window, clock)
        self._per_client = SlidingWindowCounter(max_failures_per_client, window, clock)

    @staticmethod
    def _account_key(client: str, email: str) -> str:
        return f"{client}|{email.strip().lower()[:254]}"

    def set_clock(self, clock: Callable[[], float]) -> None:
        self._per_account.clock = clock
        self._per_client.clock = clock

    def check(self, client: str, email: str) -> None:
        """Raise ``TooManyRequestsError`` while ``client`` has to wait."""
        wait = max(
            self._per_account.retry_after(self._account_key(client, email)),
            self._per_client.retry_after(client),
        )
        if wait > 0:
            raise TooManyRequestsError(
                "Too many failed sign-in attempts. Wait a few minutes, then try again.",
                retry_after=wait,
            )

    def record_failure(self, client: str, email: str) -> None:
        self._per_account.add(self._account_key(client, email))
        self._per_client.add(client)

    def record_success(self, client: str, email: str) -> None:
        self._per_account.reset(self._account_key(client, email))
