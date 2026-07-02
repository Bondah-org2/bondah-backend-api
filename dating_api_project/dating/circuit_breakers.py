"""
Circuit breakers for external service calls.

A circuit breaker prevents cascading failures by stopping calls to a
service that is repeatedly failing. After fail_max failures, the breaker
opens and immediately raises CircuitBreakerError for reset_timeout seconds
before allowing a retry.

Usage:
    from dating.circuit_breakers import cloudinary_breaker, email_breaker

    @cloudinary_breaker
    def my_cloudinary_call():
        ...

    try:
        my_cloudinary_call()
    except CircuitBreakerError:
        return Response({"error": "Service unavailable"}, status=503)
"""

import logging
import pybreaker

logger = logging.getLogger(__name__)


def _on_open(cb):
    logger.warning(
        f"Circuit breaker OPENED for '{cb.name}' after {cb.fail_counter} failures. "
        f"Will retry after {cb.reset_timeout}s."
    )


def _on_close(cb):
    logger.info(f"Circuit breaker CLOSED for '{cb.name}'. Service recovered.")


def _on_half_open(cb):
    logger.info(f"Circuit breaker HALF-OPEN for '{cb.name}'. Testing service...")


# ── Cloudinary circuit breaker ────────────────────────────────────────────────
# Opens after 5 consecutive failures, resets after 60 seconds
cloudinary_breaker = pybreaker.CircuitBreaker(
    fail_max=5,
    reset_timeout=60,
    name="cloudinary",
    listeners=[
        pybreaker.CircuitBreakerListener(),
    ],
)

# ── Email (Brevo) circuit breaker ─────────────────────────────────────────────
email_breaker = pybreaker.CircuitBreaker(
    fail_max=5,
    reset_timeout=60,
    name="email",
    listeners=[
        pybreaker.CircuitBreakerListener(),
    ],
)

# ── Firebase push notification circuit breaker ───────────────────────────────
firebase_breaker = pybreaker.CircuitBreaker(
    fail_max=5,
    reset_timeout=60,
    name="firebase",
    listeners=[
        pybreaker.CircuitBreakerListener(),
    ],
)
