from hexadian_auth_common.fastapi import JWTAuthDependency
from opyoid import Module, SingletonScope
from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection

from src.application.ports.inbound.graph_service import GraphService
from src.application.ports.outbound.graph_repository import GraphRepository
from src.application.ports.outbound.maps_client import MapsClient
from src.application.services.graph_service_impl import GraphServiceImpl
from src.infrastructure.adapters.outbound.http.maps_client_impl import HttpMapsClient
from src.infrastructure.adapters.outbound.persistence.mongo_graph_repository import MongoGraphRepository
from src.infrastructure.config.settings import Settings


class AppModule(Module):
    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self._settings = settings

    def configure(self) -> None:
        client = MongoClient(self._settings.mongo_uri)
        db = client[self._settings.mongo_db]
        collection = db["graphs"]

        collection.create_index([("name", ASCENDING)])
        collection.create_index([("nodes.location_id", ASCENDING)])

        jwt_auth = JWTAuthDependency(
            secret=self._settings.jwt_secret,
            algorithm=self._settings.jwt_algorithm,
        )
        maps_client = HttpMapsClient(base_url=self._settings.maps_service_url)

        self.bind(Collection, to_instance=collection, scope=SingletonScope)
        self.bind(GraphRepository, to_class=MongoGraphRepository, scope=SingletonScope)
        self.bind(GraphService, to_class=GraphServiceImpl, scope=SingletonScope)
        self.bind(JWTAuthDependency, to_instance=jwt_auth, scope=SingletonScope)
        self.bind(MapsClient, to_instance=maps_client, scope=SingletonScope)
