from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "hhh-graphs-service"
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "hhh_graphs"
    host: str = "0.0.0.0"
    port: int = 8004
    jwt_secret: str = Field(default="change-me-in-production", validation_alias="HEXADIAN_AUTH_JWT_SECRET")
    jwt_algorithm: str = "HS256"
    maps_service_url: str = "http://localhost:8003"
    cors_allow_origins: list[str] = Field(default=["http://localhost:3000", "http://localhost:3001"])

    model_config = {"env_prefix": "HHH_GRAPHS_", "populate_by_name": True}
