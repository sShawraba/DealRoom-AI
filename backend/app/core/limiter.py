from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from fastapi import Request


def _get_user_key(request: Request) -> str:
    """Use JWT sub as rate-limit key for authenticated routes; fall back to IP."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            from app.core.security import decode_token
            payload = decode_token(auth[7:])
            return f"user:{payload['sub']}"
        except Exception:
            pass
    return get_remote_address(request)


ip_limiter = Limiter(key_func=get_remote_address)
user_limiter = Limiter(key_func=_get_user_key)

__all__ = [
    "ip_limiter",
    "user_limiter",
    "RateLimitExceeded",
    "_rate_limit_exceeded_handler",
]
