import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class InternalAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        node_env = os.getenv("NODE_ENV", "development")

        if node_env != "production":
            return await call_next(request)

        if request.url.path == "/health":
            return await call_next(request)

        expected_secret = os.getenv("INTERNAL_SHARED_SECRET")
        received_secret = request.headers.get("x-internal-auth")

        if not expected_secret or received_secret != expected_secret:
            return JSONResponse(
                status_code=403,
                content={"error": "Internal shared secret requerido"}
            )

        return await call_next(request)