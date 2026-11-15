from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
import unicodedata

from pydantic import BaseModel, Field, field_validator

StatusName = Literal["LEARNING", "NORMAL", "CAUTION", "ALERT", "OFFLINE"]
SourceName = Literal["live", "cached", "simulated"]
HealthName = Literal["ok", "degraded"]
BiometricSourceName = Literal["unavailable", "local-device", "cached", "simulated"]
SuitSourceName = Literal["unavailable", "local-device", "cached", "simulated"]
SuitPressureStatus = Literal[
    "CRITICAL_LOW", "WARN_LOW", "NOMINAL", "WARN_HIGH", "CRITICAL_HIGH"
]
SuitTemperatureStatus = Literal[
    "CRITICAL_LOW", "WARN_LOW", "COMFORT", "WARN_HIGH", "CRITICAL_HIGH"
]
HeartRateStatus = Literal["UNAVAILABLE", "NOMINAL", "WARN_HIGH", "CRITICAL_HIGH"]
TaskPriority = Literal["INFO", "ADVISORY", "CAUTION", "ALERT"]
MessageDeliveryStatus = Literal["queued", "delivered"]


class Vector3(BaseModel):
    x: float | None = Field(default=None, description="X-axis value")
    y: float | None = Field(default=None, description="Y-axis value")
    z: float | None = Field(default=None, description="Z-axis value")


class OrientationDegrees(BaseModel):
    pitch: float | None = Field(default=None, description="Pitch in degrees")
    roll: float | None = Field(default=None, description="Roll in degrees")
    yaw: float | None = Field(default=None, description="Yaw in degrees")


class SensorValues(BaseModel):
    temperature_c: float | None = Field(
        default=None,
        description="Sense HAT temperature in degrees Celsius",
    )
    humidity_pct: float | None = Field(
        default=None,
        description="Relative humidity in percent",
    )
    pressure_hpa: float | None = Field(
        default=None,
        description="Barometric pressure in hectopascals",
    )
    acceleration_g: Vector3 | None = Field(
        default=None,
        description="Filtered 3-axis acceleration in g",
    )
    gyroscope_rps: Vector3 | None = Field(
        default=None,
        description="Filtered 3-axis angular velocity in radians per second",
    )
    magnetic_uT: Vector3 | None = Field(
        default=None,
        description="Filtered 3-axis magnetic field in microteslas",
    )
    orientation_deg: OrientationDegrees | None = Field(
        default=None,
        description="Fused pitch, roll, and yaw orientation in degrees",
    )


class DerivedFeatures(BaseModel):
    acceleration_magnitude_g: float | None = Field(
        default=None,
        description="Magnitude of the filtered acceleration vector in g",
    )
    motion_rms_g: float | None = Field(
        default=None,
        description="RMS acceleration variation within the edge window in g",
    )
    peak_acceleration_g: float | None = Field(
        default=None,
        description="Peak acceleration magnitude within the edge window in g",
    )
    rotation_rms_rps: float | None = Field(
        default=None,
        description="RMS angular speed within the edge window in radians per second",
    )
    orientation_change_deg: float | None = Field(
        default=None,
        description="Combined pitch, roll, and yaw change across the edge window",
    )


class DataQuality(BaseModel):
    overall_score: float = Field(ge=0.0, le=1.0)
    sample_count: int = Field(ge=0)
    expected_sample_count: int = Field(ge=1)
    valid_ratio: float = Field(ge=0.0, le=1.0)
    filtered: bool = True
    flags: list[str] = Field(default_factory=list)


class BloodPressure(BaseModel):
    systolic_mm_hg: float | None = Field(
        default=None,
        ge=0.0,
        description="Systolic blood pressure in mmHg; inspect biometric source",
    )
    diastolic_mm_hg: float | None = Field(
        default=None,
        ge=0.0,
        description="Diastolic blood pressure in mmHg; inspect biometric source",
    )


class BiometricQuality(BaseModel):
    overall_score: float = Field(default=0.0, ge=0.0, le=1.0)
    valid_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    sample_age_seconds: float | None = Field(default=None, ge=0.0)
    flags: list[str] = Field(default_factory=list)


class HeartRateThresholds(BaseModel):
    warn_high_bpm: float = 120.0
    critical_high_bpm: float = 140.0


class Biometrics(BaseModel):
    timestamp: datetime | None = None
    heart_rate_bpm: float | None = Field(
        default=None,
        ge=0.0,
        description="Heart rate in beats per minute; inspect biometric source",
    )
    blood_pressure: BloodPressure | None = None
    oxygen_saturation_pct: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Oxygen saturation in percent; inspect biometric source",
    )
    body_temperature_c: float | None = Field(
        default=None,
        description="Body temperature in Celsius; inspect biometric source",
    )
    heart_rate_status: HeartRateStatus = "UNAVAILABLE"
    heart_rate_thresholds: HeartRateThresholds = Field(
        default_factory=HeartRateThresholds
    )
    source: BiometricSourceName = "unavailable"
    quality: BiometricQuality = Field(default_factory=BiometricQuality)


class SuitPressureThresholds(BaseModel):
    critical_low_hpa: float = 248.0
    warn_low_hpa: float = 276.0
    nominal_hpa: float = 296.0
    warn_high_hpa: float = 365.0
    critical_high_hpa: float = 455.0


class SuitPressure(BaseModel):
    timestamp: datetime | None = None
    pressure_hpa: float | None = Field(
        default=None,
        ge=0.0,
        description="Suit pressure in hectopascals; inspect source",
    )
    pressure_psi: float | None = Field(
        default=None,
        ge=0.0,
        description="Suit pressure in pounds per square inch; inspect source",
    )
    status: SuitPressureStatus | Literal["UNAVAILABLE"] = "UNAVAILABLE"
    source: SuitSourceName = "unavailable"
    thresholds: SuitPressureThresholds = Field(
        default_factory=SuitPressureThresholds
    )
    flags: list[str] = Field(default_factory=list)


class SuitTemperatureThresholds(BaseModel):
    critical_low_c: float = 10.0
    comfort_low_c: float = 20.0
    comfort_high_c: float = 30.0
    critical_high_c: float = 43.0


class SuitTemperature(BaseModel):
    timestamp: datetime | None = None
    temperature_c: float | None = Field(
        default=None,
        description="Suit air temperature in Celsius; inspect source",
    )
    status: SuitTemperatureStatus | Literal["UNAVAILABLE"] = "UNAVAILABLE"
    source: SuitSourceName = "unavailable"
    thresholds: SuitTemperatureThresholds = Field(
        default_factory=SuitTemperatureThresholds
    )
    flags: list[str] = Field(default_factory=list)


class TaskMessage(BaseModel):
    id: str
    priority: TaskPriority
    category: str
    text: str
    issued_at: datetime
    source: Literal["simulated"] = "simulated"


class CrewMember(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,31}$")
    name: str = Field(min_length=1, max_length=64)


class CrewMessageCreate(BaseModel):
    recipient_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,31}$")
    priority: TaskPriority = "INFO"
    text: str = Field(min_length=1, max_length=240)

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("message text cannot be blank")
        return normalized


class CrewMessageAck(BaseModel):
    recipient_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,31}$")


class CrewMessage(BaseModel):
    id: int = Field(ge=1)
    recipient_id: str
    sender: Literal["central-station"] = "central-station"
    priority: TaskPriority
    text: str
    created_at: datetime
    delivered_at: datetime | None = None
    status: MessageDeliveryStatus


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=400)
    max_tokens: int = Field(default=24, ge=1, le=32)
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        value = unicodedata.normalize("NFKC", value)
        if any(
            unicodedata.category(character) in {"Cc", "Cf"}
            and character not in {"\t", "\n", "\r"}
            for character in value
        ):
            raise ValueError("message cannot contain control characters")
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("chat message cannot be blank")
        return normalized


class ChatResponse(BaseModel):
    reply: str
    model: str
    generated_at: datetime
    latency_seconds: float = Field(ge=0.0)
    local: Literal[True] = True
    response_type: Literal["model", "guardrail", "fallback"] = "model"
    safety_notice: str = (
        "Prototype assistant; not medical, emergency, or flight-certified guidance."
    )


class ChatHealthResponse(BaseModel):
    status: Literal["ready", "busy", "unavailable"]
    model: str
    max_input_characters: int = Field(ge=1)
    max_output_tokens: int = Field(ge=1)
    max_temperature: float = Field(ge=0.0, le=1.0)
    timeout_seconds: float = Field(gt=0.0)
    guardrails_version: str
    local: Literal[True] = True


class SensorSample(BaseModel):
    timestamp: datetime
    sensors: SensorValues
    source: SourceName
    imu_window: list[SensorValues] = Field(default_factory=list, exclude=True)
    features: DerivedFeatures | None = None
    quality: DataQuality | None = None


class StatusResponse(BaseModel):
    timestamp: datetime
    status: StatusName
    score: float
    summary: str
    sensors: SensorValues
    source: SourceName
    features: DerivedFeatures | None = None
    quality: DataQuality | None = None
    biometrics: Biometrics = Field(default_factory=Biometrics)
    suit_pressure: SuitPressure = Field(default_factory=SuitPressure)
    suit_temperature: SuitTemperature = Field(default_factory=SuitTemperature)
    tasks: list[TaskMessage] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: HealthName
    version: str
    sensor_mode: str
    sample_age_seconds: float | None
    baseline_samples: int
    consecutive_failures: int
    last_error: str | None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
