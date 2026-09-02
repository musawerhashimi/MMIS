"""
JWT authentication for websocket connections.

Browsers cannot set headers on a websocket handshake, so the access token
arrives either in the query string (?token=...) or in the Sec-WebSocket-Protocol
header. Both are accepted here and resolved to a real user before the consumer
runs.
"""
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from channels.sessions import CookieMiddleware, SessionMiddleware
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def _user_from_token(raw_token: str):
    """Resolve a JWT string to a user, or AnonymousUser if it is not valid."""
    from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
    from rest_framework_simplejwt.tokens import AccessToken
    from django.contrib.auth import get_user_model

    try:
        token = AccessToken(raw_token)
        user_id = token["user_id"]
    except (InvalidToken, TokenError, KeyError):
        return AnonymousUser()

    User = get_user_model()
    try:
        user = User.objects.get(id=user_id, is_active=True)
    except User.DoesNotExist:
        return AnonymousUser()
    return user


def _extract_token(scope) -> str | None:
    query = parse_qs(scope.get("query_string", b"").decode())
    if "token" in query and query["token"]:
        return query["token"][0]

    # Fallback: token passed as the second websocket subprotocol.
    for header_name, header_value in scope.get("headers", []):
        if header_name == b"sec-websocket-protocol":
            parts = [p.strip() for p in header_value.decode().split(",")]
            if len(parts) >= 2 and parts[0] == "jwt":
                return parts[1]
    return None


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        scope = dict(scope)
        raw_token = _extract_token(scope)
        scope["user"] = await _user_from_token(raw_token) if raw_token else AnonymousUser()
        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    """Session middleware first so Django admin sessions also work in dev."""
    return CookieMiddleware(SessionMiddleware(JWTAuthMiddleware(inner)))
