from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _positive_float(name: str, default: float) -> float:
    value = float(os.getenv(name, str(default)))
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


def _positive_int(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


def _boolean(name: str, default: bool) -> bool:
    raw_value = os.getenv(name, str(default)).strip().lower()
    if raw_value in {"1", "true", "yes", "on"}:
        return True
    if raw_value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be true or false")


def _bounded_float(
    name: str,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    value = float(os.getenv(name, str(default)))
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    host: str
    port: int
    sensor_mode: str
    biometrics_mode: str
    suit_telemetry_mode: str
    simulation_profile: str
    sample_interval_seconds: float
    imu_sample_hz: int
    task_interval_seconds: float
    llm_enabled: bool
    llm_binary_path: Path
    llm_model_path: Path
    llm_timeout_seconds: float
    llm_max_tokens: int
    llm_max_temperature: float
    llm_threads: int
    database_path: Path
    baseline_samples: int
    state_confirmation_samples: int
    restore_baseline: bool

    @classmethod
    def from_environment(cls) -> "Settings":
        sensor_mode = os.getenv("ASTRA_SENSOR_MODE", "simulated").strip().lower()
        if sensor_mode not in {"simulated", "sense-hat"}:
            raise ValueError("ASTRA_SENSOR_MODE must be 'simulated' or 'sense-hat'")

        biometrics_mode = os.getenv(
            "ASTRA_BIOMETRICS_MODE", "simulated"
        ).strip().lower()
        if biometrics_mode not in {"disabled", "simulated"}:
            raise ValueError(
                "ASTRA_BIOMETRICS_MODE must be 'disabled' or 'simulated'"
            )

        suit_telemetry_mode = os.getenv(
            "ASTRA_SUIT_TELEMETRY_MODE", "simulated"
        ).strip().lower()
        if suit_telemetry_mode not in {"disabled", "simulated"}:
            raise ValueError(
                "ASTRA_SUIT_TELEMETRY_MODE must be 'disabled' or 'simulated'"
            )

        profile = os.getenv("ASTRA_SIMULATION_PROFILE", "cycle").strip().lower()
        if profile not in {"normal", "cycle"}:
            raise ValueError(
                "ASTRA_SIMULATION_PROFILE must be 'normal' or 'cycle'"
            )

        return cls(
            host=os.getenv("ASTRA_HOST", "0.0.0.0"),
            port=int(os.getenv("ASTRA_PORT", "8000")),
            sensor_mode=sensor_mode,
            biometrics_mode=biometrics_mode,
            suit_telemetry_mode=suit_telemetry_mode,
            simulation_profile=profile,
            sample_interval_seconds=_positive_float(
                "ASTRA_SAMPLE_INTERVAL_SECONDS", 1.0
            ),
            imu_sample_hz=_positive_int("ASTRA_IMU_SAMPLE_HZ", 20),
            task_interval_seconds=_positive_float(
                "ASTRA_TASK_INTERVAL_SECONDS", 300.0
            ),
            llm_enabled=_boolean("ASTRA_LLM_ENABLED", True),
            llm_binary_path=Path(
                os.getenv(
                    "ASTRA_LLM_BINARY_PATH",
                    "/home/pi/llm-benchmark/llama.cpp/build/bin/llama-completion",
                )
            ),
            llm_model_path=Path(
                os.getenv(
                    "ASTRA_LLM_MODEL_PATH",
                    "/home/pi/llm-benchmark/models/"
                    "gemma-3-270m-it-Q4_K_M.gguf",
                )
            ),
            llm_timeout_seconds=_positive_float(
                "ASTRA_LLM_TIMEOUT_SECONDS", 120.0
            ),
            llm_max_tokens=_positive_int("ASTRA_LLM_MAX_TOKENS", 32),
            llm_max_temperature=_bounded_float(
                "ASTRA_LLM_MAX_TEMPERATURE", 0.4, 0.0, 1.0
            ),
            llm_threads=_positive_int("ASTRA_LLM_THREADS", 4),
            database_path=Path(
                os.getenv("ASTRA_DATABASE_PATH", "data/astra.db")
            ),
            baseline_samples=_positive_int("ASTRA_BASELINE_SAMPLES", 20),
            state_confirmation_samples=_positive_int(
                "ASTRA_STATE_CONFIRMATION_SAMPLES", 2
            ),
            restore_baseline=_boolean("ASTRA_RESTORE_BASELINE", True),
        )
