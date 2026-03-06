from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app


class TestCORS(TestCase):
    async def test_cors_preflight_allows_frontend_origin(self):
        """프론트엔드 origin의 preflight 요청이 허용되어야 한다."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.options(
                "/api/v1/auth/kakao",
                headers={
                    "Origin": "http://localhost:5173",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type",
                },
            )
        assert response.status_code == status.HTTP_200_OK
        assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
        assert response.headers.get("access-control-allow-credentials") == "true"
