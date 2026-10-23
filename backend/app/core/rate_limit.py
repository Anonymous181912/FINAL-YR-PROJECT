"""SlowAPI rate limiter shared instance (Phase 0g).

Endpoints opt in via ``@limiter.limit(settings.rate_limit_*)``.
The limiter is attached to the FastAPI app in ``app.main`` together with
the ``RateLimitExceeded`` handler, so all modules import this one instance.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=[])
