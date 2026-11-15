from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.analysis import BaselineAnalyzer
from app.biometrics import DisabledBiometrics, SimulatedBiometrics
from app.chat import (
    ChatBusyError,
    ChatGenerationError,
    ChatTimeoutError,
    ChatUnavailableError,
    LocalGemmaChat,
)
from app.config import Settings
from app.models import (
    CrewMember,
    ChatRequest,
    ChatResponse,
    ChatHealthResponse,
    CrewMessage,
    CrewMessageAck,
    CrewMessageCreate,
    HealthResponse,
    StatusResponse,
)
from app.processing import SensorProcessor
from app.sensors import SenseHatSensor, SimulatedSensor
from app.service import AstraService
from app.storage import StatusStore
from app.suit import DisabledSuitTelemetry, SimulatedSuitTelemetry
from app.tasks import SimulatedTaskSource

DASHBOARD_DIRECTORY = Path(__file__).resolve().parents[2] / "central-station"
CREW_ROSTER = (
    CrewMember(id="astronaut-1", name="Astronaut 1"),
    CrewMember(id="astronaut-2", name="Astronaut 2"),
    CrewMember(id="astronaut-3", name="Astronaut 3"),
    CrewMember(id="astronaut-4", name="Astronaut 4"),
)
CREW_IDS = {member.id for member in CREW_ROSTER}


def build_service(settings: Settings) -> AstraService:
    if settings.sensor_mode == "sense-hat":
        sensor = SenseHatSensor()
    else:
        sensor = SimulatedSensor(
            settings.simulation_profile,
            imu_sample_hz=settings.imu_sample_hz,
        )

    biometrics = (
        SimulatedBiometrics()
        if settings.biometrics_mode == "simulated"
        else DisabledBiometrics()
    )
    suit = (
        SimulatedSuitTelemetry()
        if settings.suit_telemetry_mode == "simulated"
        else DisabledSuitTelemetry()
    )

    return AstraService(
        sensor=sensor,
        analyzer=BaselineAnalyzer(
            minimum_samples=settings.baseline_samples,
            confirmation_samples=settings.state_confirmation_samples,
        ),
        store=StatusStore(settings.database_path),
        sample_interval_seconds=settings.sample_interval_seconds,
        restore_baseline=settings.restore_baseline,
        processor=SensorProcessor(expected_imu_samples=settings.imu_sample_hz),
        biometrics=biometrics,
        suit=suit,
        tasks=SimulatedTaskSource(
            interval_seconds=settings.task_interval_seconds,
        ),
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or Settings.from_environment()
    service = build_service(active_settings)
    chat = LocalGemmaChat(
        binary_path=active_settings.llm_binary_path,
        model_path=active_settings.llm_model_path,
        timeout_seconds=active_settings.llm_timeout_seconds,
        max_tokens_limit=active_settings.llm_max_tokens,
        max_temperature=active_settings.llm_max_temperature,
        threads=active_settings.llm_threads,
        enabled=active_settings.llm_enabled,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await service.start()
        yield
        await service.stop()

    application = FastAPI(
        title="ASTRA Backpack Service",
        version=__version__,
        lifespan=lifespan,
    )
    application.state.astra_service = service
    application.state.astra_chat = chat
    application.mount(
        "/static",
        StaticFiles(directory=DASHBOARD_DIRECTORY),
        name="static",
    )

    @application.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse(url="/dashboard")

    @application.get("/dashboard", include_in_schema=False)
    async def dashboard() -> FileResponse:
        return FileResponse(DASHBOARD_DIRECTORY / "index.html")

    @application.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        snapshot = service.health_snapshot()
        return HealthResponse(
            version=__version__,
            sensor_mode=active_settings.sensor_mode,
            **snapshot,
        )

    @application.get("/api/v1/status", response_model=StatusResponse)
    async def status() -> StatusResponse:
        if service.latest is None:
            raise HTTPException(status_code=503, detail="No sensor sample is ready")
        return service.latest

    @application.get("/api/v1/history", response_model=list[StatusResponse])
    async def history(
        limit: int = Query(default=120, ge=1, le=300),
    ) -> list[StatusResponse]:
        return await service.recent_history(limit)

    @application.get("/api/v1/crew", response_model=list[CrewMember])
    async def crew() -> list[CrewMember]:
        return list(CREW_ROSTER)

    @application.post(
        "/api/v1/messages",
        response_model=CrewMessage,
        status_code=201,
    )
    async def send_message(request: CrewMessageCreate) -> CrewMessage:
        if request.recipient_id not in CREW_IDS:
            raise HTTPException(status_code=422, detail="Unknown astronaut ID")
        return await service.send_message(request)

    @application.get("/api/v1/messages", response_model=list[CrewMessage])
    async def messages(
        recipient_id: str | None = Query(default=None),
        after_id: int = Query(default=0, ge=0),
        pending_only: bool = Query(default=False),
        limit: int = Query(default=50, ge=1, le=100),
    ) -> list[CrewMessage]:
        if recipient_id is not None and recipient_id not in CREW_IDS:
            raise HTTPException(status_code=422, detail="Unknown astronaut ID")
        return await service.messages(
            recipient_id=recipient_id,
            after_id=after_id,
            pending_only=pending_only,
            limit=limit,
        )

    @application.post(
        "/api/v1/messages/{message_id}/ack",
        response_model=CrewMessage,
    )
    async def acknowledge_message(
        message_id: int,
        request: CrewMessageAck,
    ) -> CrewMessage:
        message = await service.acknowledge_message(
            message_id,
            request.recipient_id,
        )
        if message is None:
            raise HTTPException(status_code=404, detail="Message not found")
        return message

    @application.post("/api/v1/chat", response_model=ChatResponse)
    async def local_chat(request: ChatRequest) -> ChatResponse:
        try:
            return await chat.complete(request)
        except ChatBusyError as error:
            raise HTTPException(status_code=429, detail=str(error)) from error
        except ChatUnavailableError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except ChatTimeoutError as error:
            raise HTTPException(status_code=504, detail=str(error)) from error
        except ChatGenerationError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

    @application.get("/api/v1/chat/health", response_model=ChatHealthResponse)
    async def local_chat_health() -> ChatHealthResponse:
        return ChatHealthResponse(**chat.health_snapshot())

    return application


app = create_app()
