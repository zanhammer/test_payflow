import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class HttpxWebhookSender:
    async def send(self, url: str, payload: dict[str, Any]) -> None:
        async with httpx.AsyncClient(timeout=10) as client:
            for attempt in range(3):
                try:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    return

                except (httpx.HTTPStatusError, httpx.HTTPError, httpx.TimeoutException) as exc:
                    if attempt == 2:
                        logger.error(
                            "Webhook delivery failed after 3 attempts",
                            extra={"url": url, "error": str(exc)},
                        )
                        return

                    delay = (attempt + 1) * 2
                    logger.warning(
                        "Webhook delivery attempt %d failed, retrying in %d sec",
                        attempt + 1,
                        delay,
                        extra={"url": url, "error": str(exc)},
                    )
                    await asyncio.sleep(delay)
