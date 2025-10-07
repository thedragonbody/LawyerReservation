import urllib.parse
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import AccessToken
from users.models import User
from django.contrib.auth.models import AnonymousUser

@database_sync_to_async
def get_user_from_token(token_key):
    try:
        access = AccessToken(token_key)
        user_id = access["user_id"]
        return User.objects.get(id=user_id)
    except Exception:
        return AnonymousUser()

class JWTAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    def __call__(self, scope):
        return JWTAuthMiddlewareInstance(scope, self.inner)

class JWTAuthMiddlewareInstance:
    def __init__(self, scope, inner):
        self.scope = dict(scope)
        self.inner = inner

    async def __call__(self, receive, send):
        query = self.scope.get("query_string", b"").decode()
        params = urllib.parse.parse_qs(query)
        token = params.get("token", [None])[0]
        if token:
            self.scope["user"] = await get_user_from_token(token)
        return await self.inner(self.scope, receive, send)