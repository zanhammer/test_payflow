from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.infrastructure.http.webhook_sender import HttpxWebhookSender

URL = "https://example.com/hook"
PAYLOAD = {"payment_id": "123", "status": "completed"}


def make_mock_client(side_effect: Exception | None = None) -> MagicMock:
    response = MagicMock()
    response.raise_for_status = MagicMock()
    if side_effect:
        response.raise_for_status.side_effect = side_effect

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


class TestHttpxWebhookSender:
    async def test_successful_delivery_on_first_attempt(self) -> None:
        sender = HttpxWebhookSender()
        mock_client = make_mock_client()

        with patch("httpx.AsyncClient", return_value=mock_client):
            await sender.send(URL, PAYLOAD)

        mock_client.post.assert_called_once_with(URL, json=PAYLOAD)

    async def test_retries_on_failure_and_succeeds(self) -> None:
        sender = HttpxWebhookSender()

        success_response = MagicMock()
        success_response.raise_for_status = MagicMock()

        fail_response = MagicMock()
        fail_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=MagicMock()
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=[fail_response, fail_response, success_response]
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        sleep_mock = AsyncMock()
        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            patch("app.infrastructure.http.webhook_sender.asyncio.sleep", sleep_mock),
        ):
            await sender.send(URL, PAYLOAD)

        assert mock_client.post.call_count == 3
        assert sleep_mock.call_count == 2
        assert [call.args[0] for call in sleep_mock.call_args_list] == [2, 4]

    async def test_gives_up_after_3_failures_without_raising(self) -> None:
        sender = HttpxWebhookSender()
        mock_client = make_mock_client(side_effect=httpx.TimeoutException("timeout"))

        sleep_mock = AsyncMock()
        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            patch("app.infrastructure.http.webhook_sender.asyncio.sleep", sleep_mock),
        ):
            await sender.send(URL, PAYLOAD)

        assert mock_client.post.call_count == 3
