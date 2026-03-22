import asyncio
import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient

from src.application.ports.inbound.graph_service import GraphService
from src.application.ports.inbound.import_event_subscriber import ImportEventSubscriber

logger = logging.getLogger(__name__)

_RESUME_TOKENS_COLLECTION = "resume_tokens"
_SUBSCRIBER_ID = "import_event_subscriber"
_IMPORT_EVENTS_COLLECTION = "import_events"
_RETRY_DELAY_SECONDS = 5


class MongoImportEventSubscriber(ImportEventSubscriber):
    """Watches the maps-service ``import_events`` collection via Change Streams
    and marks affected graphs as stale.

    Resume tokens are persisted in the graphs database so the subscriber can
    restart from its last position after a process restart.
    """

    def __init__(
        self,
        motor_client: AsyncIOMotorClient,
        graphs_db_name: str,
        maps_db_name: str,
        graph_service: GraphService,
    ) -> None:
        self._graphs_db = motor_client[graphs_db_name]
        self._maps_db = motor_client[maps_db_name]
        self._graph_service = graph_service
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(), name="import-event-subscriber")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            await self._task
            self._task = None

    # ------------------------------------------------------------------
    # Internal loop
    # ------------------------------------------------------------------

    async def _run(self) -> None:
        resume_token = await self._load_resume_token()
        while not self._stop_event.is_set():
            try:
                await self._watch(resume_token)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Import event subscriber error; retrying in %s s", _RETRY_DELAY_SECONDS)
                if not self._stop_event.is_set():
                    await asyncio.sleep(_RETRY_DELAY_SECONDS)
                    resume_token = await self._load_resume_token()

    async def _watch(self, resume_token: dict[str, Any] | None) -> None:
        pipeline = [{"$match": {"operationType": "insert"}}]
        watch_kwargs: dict[str, Any] = {}
        if resume_token is not None:
            watch_kwargs["resume_after"] = resume_token

        async with self._maps_db[_IMPORT_EVENTS_COLLECTION].watch(pipeline, **watch_kwargs) as stream:
            async for event in stream:
                if self._stop_event.is_set():
                    break
                await self._handle_event(event)
                token = event["_id"]
                await self._save_resume_token(token)

    async def _handle_event(self, event: dict[str, Any]) -> None:
        doc: dict[str, Any] = event.get("fullDocument") or {}
        location_ids: list[str] = doc.get("location_ids", [])
        if not location_ids:
            logger.debug("Import event has no location_ids; skipping")
            return
        count = await self._graph_service.mark_graphs_stale(
            location_ids=location_ids,
            reason="data_import",
        )
        logger.info("Marked %d graph(s) stale for %d imported location(s)", count, len(location_ids))

    # ------------------------------------------------------------------
    # Resume token persistence
    # ------------------------------------------------------------------

    async def _load_resume_token(self) -> dict[str, Any] | None:
        doc = await self._graphs_db[_RESUME_TOKENS_COLLECTION].find_one({"_id": _SUBSCRIBER_ID})
        if doc is None:
            return None
        return doc.get("token")

    async def _save_resume_token(self, token: dict[str, Any]) -> None:
        await self._graphs_db[_RESUME_TOKENS_COLLECTION].update_one(
            {"_id": _SUBSCRIBER_ID},
            {"$set": {"token": token}},
            upsert=True,
        )
