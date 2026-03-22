"""Unit tests for MongoImportEventSubscriber."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.infrastructure.adapters.inbound.events.mongo_import_event_subscriber import (
    _RESUME_TOKENS_COLLECTION,
    _SUBSCRIBER_ID,
    MongoImportEventSubscriber,
)


def _make_subscriber(graph_service: AsyncMock | None = None) -> MongoImportEventSubscriber:
    """Build a subscriber with fully mocked motor client and service."""
    motor_client = MagicMock()
    # motor_client[db] returns a mock database; mock[coll] returns a mock collection
    motor_client.__getitem__ = MagicMock(return_value=MagicMock())
    svc = graph_service or AsyncMock()
    return MongoImportEventSubscriber(
        motor_client=motor_client,
        graphs_db_name="hhh_graphs",
        maps_db_name="hhh_maps",
        graph_service=svc,
    )


class TestHandleEvent:
    async def test_calls_mark_graphs_stale_with_location_ids(self) -> None:
        graph_service = AsyncMock()
        graph_service.mark_graphs_stale.return_value = 3
        subscriber = _make_subscriber(graph_service)

        event = {"_id": {"token": "t1"}, "fullDocument": {"location_ids": ["loc1", "loc2"]}}
        await subscriber._handle_event(event)

        graph_service.mark_graphs_stale.assert_called_once_with(location_ids=["loc1", "loc2"], reason="data_import")

    async def test_skips_event_with_no_location_ids(self) -> None:
        graph_service = AsyncMock()
        subscriber = _make_subscriber(graph_service)

        event = {"_id": {"token": "t1"}, "fullDocument": {"location_ids": []}}
        await subscriber._handle_event(event)

        graph_service.mark_graphs_stale.assert_not_called()

    async def test_skips_event_with_missing_location_ids_key(self) -> None:
        graph_service = AsyncMock()
        subscriber = _make_subscriber(graph_service)

        event = {"_id": {"token": "t1"}, "fullDocument": {"other_field": "value"}}
        await subscriber._handle_event(event)

        graph_service.mark_graphs_stale.assert_not_called()

    async def test_skips_event_with_missing_full_document(self) -> None:
        graph_service = AsyncMock()
        subscriber = _make_subscriber(graph_service)

        event = {"_id": {"token": "t1"}}
        await subscriber._handle_event(event)

        graph_service.mark_graphs_stale.assert_not_called()


class TestResumeToken:
    async def test_load_resume_token_returns_none_when_no_document(self) -> None:
        subscriber = _make_subscriber()
        subscriber._graphs_db[_RESUME_TOKENS_COLLECTION].find_one = AsyncMock(return_value=None)

        result = await subscriber._load_resume_token()

        assert result is None
        subscriber._graphs_db[_RESUME_TOKENS_COLLECTION].find_one.assert_called_once_with({"_id": _SUBSCRIBER_ID})

    async def test_load_resume_token_returns_stored_token(self) -> None:
        subscriber = _make_subscriber()
        stored_token = {"_data": "some-token-data"}
        subscriber._graphs_db[_RESUME_TOKENS_COLLECTION].find_one = AsyncMock(
            return_value={"_id": _SUBSCRIBER_ID, "token": stored_token}
        )

        result = await subscriber._load_resume_token()

        assert result == stored_token

    async def test_save_resume_token_upserts_document(self) -> None:
        subscriber = _make_subscriber()
        subscriber._graphs_db[_RESUME_TOKENS_COLLECTION].update_one = AsyncMock()
        token = {"_data": "new-token-data"}

        await subscriber._save_resume_token(token)

        subscriber._graphs_db[_RESUME_TOKENS_COLLECTION].update_one.assert_called_once_with(
            {"_id": _SUBSCRIBER_ID},
            {"$set": {"token": token}},
            upsert=True,
        )


class TestStartStop:
    async def test_start_creates_background_task(self) -> None:
        subscriber = _make_subscriber()

        with patch.object(subscriber, "_run", new_callable=AsyncMock):
            await subscriber.start()
            assert subscriber._task is not None
            # Clean up
            subscriber._stop_event.set()
            await subscriber._task

    async def test_stop_sets_stop_event_and_awaits_task(self) -> None:
        subscriber = _make_subscriber()
        completed = asyncio.Event()

        async def _fake_run() -> None:
            await subscriber._stop_event.wait()
            completed.set()

        subscriber._task = asyncio.create_task(_fake_run())
        await subscriber.stop()

        assert completed.is_set()
        assert subscriber._task is None

    async def test_stop_is_idempotent_when_task_is_none(self) -> None:
        subscriber = _make_subscriber()
        # Should not raise even with no task running
        await subscriber.stop()


class TestWatchRetry:
    async def test_run_retries_after_error(self) -> None:
        """Subscriber retries the watch loop when an error occurs."""
        graph_service = AsyncMock()
        subscriber = _make_subscriber(graph_service)

        call_count = 0

        async def _flaky_watch(resume_token):  # noqa: ANN001, ARG001
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("transient error")
            # Second call: set stop immediately so the loop exits
            subscriber._stop_event.set()

        with (
            patch.object(subscriber, "_watch", side_effect=_flaky_watch),
            patch.object(subscriber, "_load_resume_token", new_callable=AsyncMock, return_value=None),
            patch(
                "src.infrastructure.adapters.inbound.events.mongo_import_event_subscriber.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            await subscriber.start()
            await asyncio.wait_for(subscriber._task, timeout=2.0)

        assert call_count == 2


class TestWatch:
    async def test_processes_event_and_saves_token(self) -> None:
        graph_service = AsyncMock()
        graph_service.mark_graphs_stale.return_value = 1
        subscriber = _make_subscriber(graph_service)
        subscriber._graphs_db[_RESUME_TOKENS_COLLECTION].update_one = AsyncMock()

        event = {"_id": {"_data": "token1"}, "fullDocument": {"location_ids": ["loc1"]}}

        async def _fake_stream():  # noqa: ANN202
            yield event

        watch_cm = AsyncMock()
        watch_cm.__aenter__.return_value = _fake_stream()
        subscriber._maps_db["import_events"].watch.return_value = watch_cm

        await subscriber._watch(None)

        graph_service.mark_graphs_stale.assert_called_once_with(location_ids=["loc1"], reason="data_import")
        subscriber._graphs_db[_RESUME_TOKENS_COLLECTION].update_one.assert_called_once()

    async def test_passes_resume_token_when_provided(self) -> None:
        subscriber = _make_subscriber()

        async def _empty_stream():  # noqa: ANN202
            return
            yield  # make it an async generator

        watch_cm = AsyncMock()
        watch_cm.__aenter__.return_value = _empty_stream()
        subscriber._maps_db["import_events"].watch.return_value = watch_cm

        resume_token = {"_data": "stored-token"}
        await subscriber._watch(resume_token)

        call_kwargs = subscriber._maps_db["import_events"].watch.call_args
        assert call_kwargs.kwargs.get("resume_after") == resume_token

    async def test_stops_processing_when_stop_event_is_set(self) -> None:
        graph_service = AsyncMock()
        subscriber = _make_subscriber(graph_service)
        subscriber._stop_event.set()

        event = {"_id": {"_data": "token1"}, "fullDocument": {"location_ids": ["loc1"]}}

        async def _fake_stream():  # noqa: ANN202
            yield event

        watch_cm = AsyncMock()
        watch_cm.__aenter__.return_value = _fake_stream()
        subscriber._maps_db["import_events"].watch.return_value = watch_cm

        await subscriber._watch(None)

        graph_service.mark_graphs_stale.assert_not_called()


class TestRunCancelledError:
    async def test_run_exits_on_cancelled_error_from_watch(self) -> None:
        """CancelledError in _watch causes _run to exit cleanly (no retry)."""
        subscriber = _make_subscriber()

        async def _raise_cancelled(resume_token):  # noqa: ANN001, ARG001
            raise asyncio.CancelledError

        with (
            patch.object(subscriber, "_watch", side_effect=_raise_cancelled),
            patch.object(subscriber, "_load_resume_token", new_callable=AsyncMock, return_value=None),
        ):
            await subscriber.start()
            task = subscriber._task
            await asyncio.wait_for(task, timeout=1.0)

        assert task.done()
