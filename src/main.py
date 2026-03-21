from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from hexadian_auth_common.fastapi import (
    JWTAuthDependency,
    _stub_jwt_auth,
    register_exception_handlers,
)
from motor.motor_asyncio import AsyncIOMotorClient
from opyoid import Injector

from src.application.ports.inbound.graph_service import GraphService
from src.infrastructure.adapters.inbound.api.graph_router import init_router, router
from src.infrastructure.config.dependencies import AppModule
from src.infrastructure.config.settings import Settings


def create_app() -> FastAPI:
    settings = Settings()
    injector = Injector([AppModule(settings)])

    graph_service = injector.inject(GraphService)
    jwt_auth = injector.inject(JWTAuthDependency)
    motor_client = injector.inject(AsyncIOMotorClient)
    http_client = injector.inject(httpx.AsyncClient)
    init_router(graph_service)

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # noqa: ARG001
        yield
        await http_client.aclose()
        motor_client.close()

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.dependency_overrides[_stub_jwt_auth] = jwt_auth
    register_exception_handlers(app)
    app.include_router(router)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "service": settings.app_name}

    return app


app = create_app()

if __name__ == "__main__":
    _settings = Settings()
    uvicorn.run("src.main:app", host=_settings.host, port=_settings.port, reload=True)
