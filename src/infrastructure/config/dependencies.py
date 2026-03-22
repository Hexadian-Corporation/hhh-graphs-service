import httpx
from hexadian_auth_common.fastapi import JWTAuthDependency
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from opyoid import Module, SingletonScope
from pymongo import ASCENDING, MongoClient

from src.application.ports.inbound.graph_service import GraphService
from src.application.ports.inbound.import_event_subscriber import ImportEventSubscriber
from src.application.ports.outbound.graph_repository import GraphRepository
from src.application.ports.outbound.maps_client import MapsClient
from src.application.services.graph_service_impl import GraphServiceImpl
from src.infrastructure.adapters.inbound.events.mongo_import_event_subscriber import MongoImportEventSubscriber
from src.infrastructure.adapters.outbound.http.maps_client_impl import HttpMapsClient
from src.infrastructure.adapters.outbound.persistence.mongo_graph_repository import MongoGraphRepository
from src.infrastructure.config.settings import Settings


class AppModule(Module):
    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self._settings = settings

    def configure(self) -> None:
        # Create indexes synchronously at startup (motor client is async-only)
        sync_client = MongoClient(self._settings.mongo_uri)
        sync_db = sync_client[self._settings.mongo_db]
        sync_collection = sync_db["graphs"]
        sync_collection.create_index([("name", ASCENDING)])
        sync_collection.create_index([("nodes.location_id", ASCENDING)])
        sync_collection.create_index("hash", unique=True, sparse=True)
        sync_client.close()

        # Async motor client for runtime
        motor_client = AsyncIOMotorClient(self._settings.mongo_uri)
        motor_db = motor_client[self._settings.mongo_db]
        motor_collection = motor_db["graphs"]

        http_client = httpx.AsyncClient(timeout=10.0)
        jwt_auth = JWTAuthDependency(
            secret=self._settings.jwt_secret,
            algorithm=self._settings.jwt_algorithm,
        )
        maps_client = HttpMapsClient(client=http_client, base_url=self._settings.maps_service_url)
        graph_repository = MongoGraphRepository(motor_collection)
        graph_service = GraphServiceImpl(repository=graph_repository, maps_client=maps_client)
        subscriber = MongoImportEventSubscriber(
            motor_client=motor_client,
            graphs_db_name=self._settings.mongo_db,
            maps_db_name=self._settings.maps_mongo_db,
            graph_service=graph_service,
        )

        self.bind(AsyncIOMotorClient, to_instance=motor_client, scope=SingletonScope)
        self.bind(AsyncIOMotorCollection, to_instance=motor_collection, scope=SingletonScope)
        self.bind(httpx.AsyncClient, to_instance=http_client, scope=SingletonScope)
        self.bind(GraphRepository, to_instance=graph_repository, scope=SingletonScope)
        self.bind(GraphService, to_instance=graph_service, scope=SingletonScope)
        self.bind(JWTAuthDependency, to_instance=jwt_auth, scope=SingletonScope)
        self.bind(MapsClient, to_instance=maps_client, scope=SingletonScope)
        self.bind(ImportEventSubscriber, to_instance=subscriber, scope=SingletonScope)
