"""
SES Send Rate Limiter — configurable token bucket.

Thread-safe singleton that enforces a per-second send-rate cap for
VOÏA-managed AWS SES delivery.  The rate is read from
PlatformEmailSettings.ses_rate_limit_per_second and reloaded
periodically so admin changes take effect without a server restart.
"""

import logging
import time
from threading import Lock, Thread

logger = logging.getLogger(__name__)

_DEFAULT_RATE = 14.0          # emails / second
_RELOAD_INTERVAL = 60         # seconds between DB re-reads


class SesRateLimiter:
    """
    Token-bucket rate limiter for SES sends.

    Workers call ``acquire()`` before sending an email.  If no token is
    available the call blocks (sleeps in a tight loop) until one
    becomes available.  This keeps the claimed task in 'processing'
    state while it waits — no task is dropped.
    """

    def __init__(self, rate: float = _DEFAULT_RATE):
        self._lock = Lock()
        self._rate: float = rate          # tokens per second
        self._tokens: float = 0.0         # start empty — no startup burst
        self._last_refill: float = time.monotonic()

        self._reload_thread = Thread(
            target=self._periodic_reload,
            daemon=True,
            name="ses-rate-limiter-reload",
        )
        self._reload_thread.start()
        logger.info(
            f"SesRateLimiter started: rate={rate:.1f} emails/sec"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def acquire(self) -> None:
        """Block until a send token is available, then consume it."""
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                # How long until the next token arrives
                wait = (1.0 - self._tokens) / self._rate if self._rate > 0 else 1.0

            # Sleep outside the lock so other threads can still acquire
            time.sleep(min(wait, 0.1))

    def set_rate(self, rate: float) -> None:
        """Update the allowed rate (emails/second).  Thread-safe."""
        if rate <= 0:
            logger.warning(
                f"Ignoring invalid SES rate {rate!r}; keeping {self._rate}"
            )
            return
        with self._lock:
            old = self._rate
            self._rate = float(rate)
            # Cap the bucket at the new rate so it doesn't overflow
            self._tokens = min(self._tokens, self._rate)
        if old != rate:
            logger.info(
                f"SesRateLimiter rate updated: {old:.1f} → {rate:.1f} emails/sec"
            )

    @property
    def current_rate(self) -> float:
        return self._rate

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refill(self) -> None:
        """Add tokens proportional to elapsed time (call while holding lock)."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._last_refill = now
        self._tokens = min(self._rate, self._tokens + elapsed * self._rate)

    def _reload_from_db(self) -> None:
        """Reload rate from PlatformEmailSettings (runs in background thread)."""
        try:
            from app import app
            with app.app_context():
                from models import PlatformEmailSettings
                settings = PlatformEmailSettings.query.first()
                if settings is not None:
                    self.set_rate(settings.ses_rate_limit_per_second)
        except Exception as exc:
            logger.warning(f"SesRateLimiter: DB reload failed — {exc}")

    def _periodic_reload(self) -> None:
        """Background thread that reloads the rate from DB every minute."""
        while True:
            time.sleep(_RELOAD_INTERVAL)
            self._reload_from_db()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_limiter: SesRateLimiter | None = None
_singleton_lock = Lock()


def get_ses_rate_limiter() -> SesRateLimiter:
    """Return the module-level singleton, creating it on first call."""
    global _limiter
    if _limiter is None:
        with _singleton_lock:
            if _limiter is None:
                # Try to initialise from DB; fall back to default
                initial_rate = _DEFAULT_RATE
                try:
                    from app import app
                    with app.app_context():
                        from models import PlatformEmailSettings
                        settings = PlatformEmailSettings.query.first()
                        if settings is not None:
                            initial_rate = settings.ses_rate_limit_per_second
                except Exception as exc:
                    logger.warning(
                        f"SesRateLimiter: could not read DB at startup, "
                        f"using default {_DEFAULT_RATE} emails/sec — {exc}"
                    )
                _limiter = SesRateLimiter(rate=initial_rate)
    return _limiter
