from contextlib import asynccontextmanager
from typing import Any, AsyncIterator
from unittest.mock import AsyncMock

from app.domain.entities import OutboxEvent
from app.infrastructure.outbox.processor import OutboxProcessor
from tests.factories import make_event


def _make_outbox_repo_with_events(events: list[OutboxEvent]) -> tuple[Any, AsyncMock]:
    repo = AsyncMock()
    repo.get_unpublished.return_value = events
    repo.mark_published = AsyncMock()

    @asynccontextmanager
    async def get_repo() -> AsyncIterator[Any]:
        yield repo

    return get_repo, repo


class TestOutboxProcessor:
    async def test_publishes_events_with_correct_routing_key(self) -> None:
        event = make_event("payment.created")
        get_repo, repo = _make_outbox_repo_with_events([event])

        publisher = AsyncMock()
        processor = OutboxProcessor(get_repo, publisher)

        await processor._process_batch()

        publisher.publish.assert_called_once_with("payments.new", event.payload)

    async def test_mark_published_called_after_publish(self) -> None:
        event = make_event("payment.created")
        get_repo, repo = _make_outbox_repo_with_events([event])

        publisher = AsyncMock()
        processor = OutboxProcessor(get_repo, publisher)

        await processor._process_batch()

        repo.mark_published.assert_called_once_with(event.id)

    async def test_skips_unknown_event_type(self) -> None:
        events = [
            make_event("unknown.event"),
            make_event("payment.created"),
        ]
        get_repo, repo = _make_outbox_repo_with_events(events)
        publisher = AsyncMock()
        processor = OutboxProcessor(get_repo, publisher)

        await processor._process_batch()

        publisher.publish.assert_called_once_with("payments.new", events[1].payload)
        repo.mark_published.assert_called_once_with(events[1].id)

    async def test_does_nothing_when_no_events(self) -> None:
        get_repo, repo = _make_outbox_repo_with_events([])
        publisher = AsyncMock()
        processor = OutboxProcessor(get_repo, publisher)

        await processor._process_batch()

        publisher.publish.assert_not_called()
        repo.mark_published.assert_not_called()
