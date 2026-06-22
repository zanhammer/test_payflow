import pytest
from fastapi import HTTPException
from unittest.mock import patch

from app.presentation.api.v1.dependencies import verify_api_key


class TestVerifyApiKey:
    async def test_valid_key_passes(self) -> None:
        with patch("app.presentation.api.v1.dependencies.settings") as mock_settings:
            mock_settings.api_key = "test-secret-key-123"
            await verify_api_key(x_api_key="test-secret-key-123")

    async def test_invalid_key_raises_401(self) -> None:
        with patch("app.presentation.api.v1.dependencies.settings") as mock_settings:
            mock_settings.api_key = "correct-key"
            with pytest.raises(HTTPException) as exc_info:
                await verify_api_key(x_api_key="wrong-key")
            assert exc_info.value.status_code == 401
