"""Authenticated FastAPI gateway; this process never imports a GPIO library."""

import argparse
import hmac
from hashlib import sha256
from pathlib import Path
from typing import Any, Optional

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from piblindhub import __version__
from piblindhub.config import AppConfig, ConfigurationError
from piblindhub.domain import CommandType
from piblindhub.ipc import ControlClient, ControlUnavailable


class CommandRequest(BaseModel):
    command: CommandType
    position: Optional[float] = Field(default=None, ge=0.0, le=100.0)


def create_app(config: AppConfig) -> FastAPI:
    config.api.validate(require_token=True)
    expected_hash = config.api.resolved_token_hash()
    assert expected_hash is not None
    client = ControlClient(config.paths.control_socket)
    web_root = Path(__file__).parent / "web"

    app = FastAPI(
        title="PiBlindHub API",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.mount("/static", StaticFiles(directory=str(web_root / "static")), name="static")

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    def require_token(authorization: Optional[str] = Header(default=None)) -> None:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Bearer token required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        supplied = authorization[7:].strip()
        supplied_hash = sha256(supplied.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(supplied_hash, expected_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def request_control(payload: dict[str, Any]) -> dict[str, Any]:
        response = client.request(payload)
        if not response.get("ok"):
            error = response.get("error", "control_request_failed")
            code = (
                status.HTTP_404_NOT_FOUND
                if error == "command_not_found"
                else status.HTTP_409_CONFLICT
            )
            raise HTTPException(status_code=code, detail=error)
        return response["data"]

    @app.exception_handler(ControlUnavailable)
    async def control_unavailable_handler(_request, _exc):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Control daemon unavailable"},
        )

    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(str(web_root / "index.html"))

    @app.get("/health")
    async def health():
        try:
            data = request_control({"operation": "health"})
        except (ControlUnavailable, HTTPException):
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "unhealthy", "control_daemon": False},
            )
        http_status = (
            status.HTTP_200_OK if data.get("healthy") else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return JSONResponse(
            status_code=http_status,
            content={
                "status": "healthy" if data.get("healthy") else "unhealthy",
                "control_daemon": True,
            },
        )

    @app.get("/api/v1/status", dependencies=[Depends(require_token)])
    async def controller_status():
        return request_control({"operation": "status"})

    @app.post(
        "/api/v1/commands",
        status_code=status.HTTP_202_ACCEPTED,
        dependencies=[Depends(require_token)],
    )
    async def submit_command(command: CommandRequest):
        payload: dict[str, Any] = {
            "operation": "command",
            "command": command.command.value,
            "source": "api",
        }
        if command.position is not None:
            payload["position"] = command.position
        return request_control(payload)

    @app.get("/api/v1/commands/{command_id}", dependencies=[Depends(require_token)])
    async def command_status(command_id: str):
        return request_control({"operation": "command_status", "command_id": command_id})

    @app.get("/api/v1/events", dependencies=[Depends(require_token)])
    async def events(limit: int = Query(default=100, ge=1, le=500)):
        return request_control({"operation": "events", "limit": limit})

    return app


def run(config_path: Optional[str] = None) -> None:
    config = AppConfig.load(config_path)
    config.api.validate(require_token=True)
    loopback_hosts = {"127.0.0.1", "::1", "localhost"}
    if config.api.host not in loopback_hosts and not config.api.tls_certificate:
        raise ConfigurationError(
            "Refusing to expose bearer authentication over cleartext non-loopback HTTP"
        )
    uvicorn.run(
        create_app(config),
        host=config.api.host,
        port=config.api.port,
        ssl_certfile=config.api.tls_certificate,
        ssl_keyfile=config.api.tls_private_key,
        access_log=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="PiBlindHub authenticated API gateway")
    parser.add_argument("--config", help="Path to private runtime config.json")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
