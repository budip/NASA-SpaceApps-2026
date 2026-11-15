from __future__ import annotations

import sqlite3
import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from app.models import (
    Biometrics,
    CrewMessage,
    CrewMessageCreate,
    DataQuality,
    DerivedFeatures,
    OrientationDegrees,
    SensorValues,
    SourceName,
    StatusResponse,
    SuitPressure,
    SuitTemperature,
    TaskMessage,
    Vector3,
    utc_now,
)


MOTION_COLUMNS = {
    "acceleration_x_g": "REAL",
    "acceleration_y_g": "REAL",
    "acceleration_z_g": "REAL",
    "gyroscope_x_rps": "REAL",
    "gyroscope_y_rps": "REAL",
    "gyroscope_z_rps": "REAL",
    "magnetic_x_uT": "REAL",
    "magnetic_y_uT": "REAL",
    "magnetic_z_uT": "REAL",
    "orientation_pitch_deg": "REAL",
    "orientation_roll_deg": "REAL",
    "orientation_yaw_deg": "REAL",
}

EDGE_COLUMNS = {
    "acceleration_magnitude_g": "REAL",
    "motion_rms_g": "REAL",
    "peak_acceleration_g": "REAL",
    "rotation_rms_rps": "REAL",
    "orientation_change_deg": "REAL",
    "quality_score": "REAL",
    "quality_sample_count": "INTEGER",
    "quality_expected_sample_count": "INTEGER",
    "quality_valid_ratio": "REAL",
    "quality_filtered": "INTEGER",
    "quality_flags_json": "TEXT",
    "biometrics_json": "TEXT",
    "suit_pressure_json": "TEXT",
    "suit_temperature_json": "TEXT",
    "tasks_json": "TEXT",
}


class StatusStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS status_readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp_utc TEXT NOT NULL,
                    status TEXT NOT NULL,
                    score REAL NOT NULL,
                    summary TEXT NOT NULL,
                    temperature_c REAL,
                    humidity_pct REAL,
                    pressure_hpa REAL,
                    acceleration_x_g REAL,
                    acceleration_y_g REAL,
                    acceleration_z_g REAL,
                    gyroscope_x_rps REAL,
                    gyroscope_y_rps REAL,
                    gyroscope_z_rps REAL,
                    magnetic_x_uT REAL,
                    magnetic_y_uT REAL,
                    magnetic_z_uT REAL,
                    orientation_pitch_deg REAL,
                    orientation_roll_deg REAL,
                    orientation_yaw_deg REAL,
                    acceleration_magnitude_g REAL,
                    motion_rms_g REAL,
                    peak_acceleration_g REAL,
                    rotation_rms_rps REAL,
                    orientation_change_deg REAL,
                    quality_score REAL,
                    quality_sample_count INTEGER,
                    quality_expected_sample_count INTEGER,
                    quality_valid_ratio REAL,
                    quality_filtered INTEGER,
                    quality_flags_json TEXT,
                    biometrics_json TEXT,
                    suit_pressure_json TEXT,
                    suit_temperature_json TEXT,
                    tasks_json TEXT,
                    source TEXT NOT NULL
                )
                """
            )
            existing = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(status_readings)"
                ).fetchall()
            }
            for column, column_type in {**MOTION_COLUMNS, **EDGE_COLUMNS}.items():
                if column not in existing:
                    connection.execute(
                        f"ALTER TABLE status_readings ADD COLUMN {column} {column_type}"
                    )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS crew_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recipient_id TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    text TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL,
                    delivered_at_utc TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_crew_messages_recipient_id
                ON crew_messages (recipient_id, id)
                """
            )

    def record(self, response: StatusResponse) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO status_readings (
                    timestamp_utc, status, score, summary, temperature_c,
                    humidity_pct, pressure_hpa,
                    acceleration_x_g, acceleration_y_g, acceleration_z_g,
                    gyroscope_x_rps, gyroscope_y_rps, gyroscope_z_rps,
                    magnetic_x_uT, magnetic_y_uT, magnetic_z_uT,
                    orientation_pitch_deg, orientation_roll_deg,
                    orientation_yaw_deg,
                    acceleration_magnitude_g, motion_rms_g,
                    peak_acceleration_g, rotation_rms_rps,
                    orientation_change_deg, quality_score,
                    quality_sample_count, quality_expected_sample_count,
                    quality_valid_ratio, quality_filtered, quality_flags_json,
                    biometrics_json,
                    suit_pressure_json,
                    suit_temperature_json,
                    tasks_json,
                    source
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    response.timestamp.isoformat(),
                    response.status,
                    response.score,
                    response.summary,
                    response.sensors.temperature_c,
                    response.sensors.humidity_pct,
                    response.sensors.pressure_hpa,
                    self._component(response.sensors.acceleration_g, "x"),
                    self._component(response.sensors.acceleration_g, "y"),
                    self._component(response.sensors.acceleration_g, "z"),
                    self._component(response.sensors.gyroscope_rps, "x"),
                    self._component(response.sensors.gyroscope_rps, "y"),
                    self._component(response.sensors.gyroscope_rps, "z"),
                    self._component(response.sensors.magnetic_uT, "x"),
                    self._component(response.sensors.magnetic_uT, "y"),
                    self._component(response.sensors.magnetic_uT, "z"),
                    self._component(response.sensors.orientation_deg, "pitch"),
                    self._component(response.sensors.orientation_deg, "roll"),
                    self._component(response.sensors.orientation_deg, "yaw"),
                    self._component(response.features, "acceleration_magnitude_g"),
                    self._component(response.features, "motion_rms_g"),
                    self._component(response.features, "peak_acceleration_g"),
                    self._component(response.features, "rotation_rms_rps"),
                    self._component(response.features, "orientation_change_deg"),
                    self._component(response.quality, "overall_score"),
                    self._component(response.quality, "sample_count"),
                    self._component(response.quality, "expected_sample_count"),
                    self._component(response.quality, "valid_ratio"),
                    (
                        int(response.quality.filtered)
                        if response.quality is not None
                        else None
                    ),
                    (
                        json.dumps(response.quality.flags)
                        if response.quality is not None
                        else None
                    ),
                    response.biometrics.model_dump_json(),
                    response.suit_pressure.model_dump_json(),
                    response.suit_temperature.model_dump_json(),
                    json.dumps(
                        [task.model_dump(mode="json") for task in response.tasks]
                    ),
                    response.source,
                ),
            )

    def count(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM status_readings"
            ).fetchone()
        return int(row[0]) if row else 0

    def create_message(self, request: CrewMessageCreate) -> CrewMessage:
        created_at = utc_now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO crew_messages (
                    recipient_id, sender, priority, text, created_at_utc
                ) VALUES (?, 'central-station', ?, ?, ?)
                """,
                (
                    request.recipient_id,
                    request.priority,
                    request.text,
                    created_at.isoformat(),
                ),
            )
            message_id = int(cursor.lastrowid)
        return CrewMessage(
            id=message_id,
            recipient_id=request.recipient_id,
            priority=request.priority,
            text=request.text,
            created_at=created_at,
            status="queued",
        )

    def messages(
        self,
        recipient_id: str | None = None,
        after_id: int = 0,
        pending_only: bool = False,
        limit: int = 50,
    ) -> list[CrewMessage]:
        bounded_limit = max(1, min(limit, 100))
        conditions: list[str] = []
        parameters: list[object] = []
        if recipient_id is not None:
            conditions.append("recipient_id = ?")
            parameters.append(recipient_id)
        if after_id > 0:
            conditions.append("id > ?")
            parameters.append(after_id)
        if pending_only:
            conditions.append("delivered_at_utc IS NULL")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        oldest_first = after_id > 0 or pending_only
        order = "ASC" if oldest_first else "DESC"
        parameters.append(bounded_limit)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT id, recipient_id, priority, text,
                       created_at_utc, delivered_at_utc
                FROM crew_messages
                {where_clause}
                ORDER BY id {order}
                LIMIT ?
                """,
                parameters,
            ).fetchall()

        messages = [self._message_from_row(row) for row in rows]
        return messages if oldest_first else list(reversed(messages))

    def acknowledge_message(
        self,
        message_id: int,
        recipient_id: str,
    ) -> CrewMessage | None:
        delivered_at = utc_now().isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE crew_messages
                SET delivered_at_utc = COALESCE(delivered_at_utc, ?)
                WHERE id = ? AND recipient_id = ?
                """,
                (delivered_at, message_id, recipient_id),
            )
            row = connection.execute(
                """
                SELECT id, recipient_id, priority, text,
                       created_at_utc, delivered_at_utc
                FROM crew_messages
                WHERE id = ? AND recipient_id = ?
                """,
                (message_id, recipient_id),
            ).fetchone()
        return self._message_from_row(row) if row else None

    def load_baseline_values(
        self,
        source: SourceName,
        limit: int,
    ) -> list[SensorValues]:
        if limit <= 0:
            return []

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT temperature_c, humidity_pct, pressure_hpa
                FROM status_readings
                WHERE source = ?
                  AND (
                    status = 'LEARNING'
                    OR (status = 'NORMAL' AND score < 0.5)
                  )
                  AND (
                    temperature_c IS NOT NULL
                    OR humidity_pct IS NOT NULL
                    OR pressure_hpa IS NOT NULL
                  )
                ORDER BY id DESC
                LIMIT ?
                """,
                (source, limit),
            ).fetchall()

        # The database query is newest-first so LIMIT keeps the latest window;
        # restore chronological order before seeding the rolling baseline.
        return [
            SensorValues(
                temperature_c=row[0],
                humidity_pct=row[1],
                pressure_hpa=row[2],
            )
            for row in reversed(rows)
        ]

    def recent(self, limit: int = 120) -> list[StatusResponse]:
        bounded_limit = max(1, min(limit, 300))
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT timestamp_utc, status, score, summary, temperature_c,
                       humidity_pct, pressure_hpa,
                       acceleration_x_g, acceleration_y_g, acceleration_z_g,
                       gyroscope_x_rps, gyroscope_y_rps, gyroscope_z_rps,
                       magnetic_x_uT, magnetic_y_uT, magnetic_z_uT,
                       orientation_pitch_deg, orientation_roll_deg,
                       orientation_yaw_deg,
                       acceleration_magnitude_g, motion_rms_g,
                       peak_acceleration_g, rotation_rms_rps,
                       orientation_change_deg, quality_score,
                       quality_sample_count, quality_expected_sample_count,
                       quality_valid_ratio, quality_filtered, quality_flags_json,
                       biometrics_json,
                       suit_pressure_json,
                       suit_temperature_json,
                       tasks_json,
                       source
                FROM status_readings
                ORDER BY id DESC
                LIMIT ?
                """,
                (bounded_limit,),
            ).fetchall()

        return [
            StatusResponse(
                timestamp=datetime.fromisoformat(row[0]),
                status=row[1],
                score=row[2],
                summary=row[3],
                sensors=SensorValues(
                    temperature_c=row[4],
                    humidity_pct=row[5],
                    pressure_hpa=row[6],
                    acceleration_g=self._vector(row[7], row[8], row[9]),
                    gyroscope_rps=self._vector(row[10], row[11], row[12]),
                    magnetic_uT=self._vector(row[13], row[14], row[15]),
                    orientation_deg=self._orientation(row[16], row[17], row[18]),
                ),
                features=self._features(row[19], row[20], row[21], row[22], row[23]),
                quality=self._quality(
                    row[24], row[25], row[26], row[27], row[28], row[29]
                ),
                biometrics=self._biometrics(row[30]),
                suit_pressure=self._suit_pressure(row[31]),
                suit_temperature=self._suit_temperature(row[32]),
                tasks=self._tasks(row[33]),
                source=row[34],
            )
            for row in reversed(rows)
        ]

    @staticmethod
    def _component(value: object | None, field: str) -> float | None:
        return getattr(value, field, None)

    @staticmethod
    def _vector(x: float | None, y: float | None, z: float | None) -> Vector3 | None:
        if x is None and y is None and z is None:
            return None
        return Vector3(x=x, y=y, z=z)

    @staticmethod
    def _orientation(
        pitch: float | None,
        roll: float | None,
        yaw: float | None,
    ) -> OrientationDegrees | None:
        if pitch is None and roll is None and yaw is None:
            return None
        return OrientationDegrees(pitch=pitch, roll=roll, yaw=yaw)

    @staticmethod
    def _features(
        acceleration_magnitude_g: float | None,
        motion_rms_g: float | None,
        peak_acceleration_g: float | None,
        rotation_rms_rps: float | None,
        orientation_change_deg: float | None,
    ) -> DerivedFeatures | None:
        values = (
            acceleration_magnitude_g,
            motion_rms_g,
            peak_acceleration_g,
            rotation_rms_rps,
            orientation_change_deg,
        )
        if all(value is None for value in values):
            return None
        return DerivedFeatures(
            acceleration_magnitude_g=acceleration_magnitude_g,
            motion_rms_g=motion_rms_g,
            peak_acceleration_g=peak_acceleration_g,
            rotation_rms_rps=rotation_rms_rps,
            orientation_change_deg=orientation_change_deg,
        )

    @staticmethod
    def _quality(
        score: float | None,
        sample_count: int | None,
        expected_sample_count: int | None,
        valid_ratio: float | None,
        filtered: int | None,
        flags_json: str | None,
    ) -> DataQuality | None:
        if score is None:
            return None
        try:
            flags = json.loads(flags_json) if flags_json else []
        except (json.JSONDecodeError, TypeError):
            flags = ["invalid_stored_quality_flags"]
        return DataQuality(
            overall_score=score,
            sample_count=sample_count or 0,
            expected_sample_count=expected_sample_count or 1,
            valid_ratio=valid_ratio or 0.0,
            filtered=bool(filtered),
            flags=flags if isinstance(flags, list) else [],
        )

    @staticmethod
    def _biometrics(value: str | None) -> Biometrics:
        if not value:
            return Biometrics()
        try:
            return Biometrics.model_validate_json(value)
        except ValueError:
            return Biometrics()

    @staticmethod
    def _tasks(value: str | None) -> list[TaskMessage]:
        if not value:
            return []
        try:
            rows = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
        if not isinstance(rows, list):
            return []
        tasks: list[TaskMessage] = []
        for row in rows:
            try:
                tasks.append(TaskMessage.model_validate(row))
            except ValueError:
                continue
        return tasks

    @staticmethod
    def _suit_pressure(value: str | None) -> SuitPressure:
        if not value:
            return SuitPressure()
        try:
            return SuitPressure.model_validate_json(value)
        except ValueError:
            return SuitPressure(flags=["invalid_stored_suit_pressure"])

    @staticmethod
    def _suit_temperature(value: str | None) -> SuitTemperature:
        if not value:
            return SuitTemperature()
        try:
            return SuitTemperature.model_validate_json(value)
        except ValueError:
            return SuitTemperature(flags=["invalid_stored_suit_temperature"])

    @staticmethod
    def _message_from_row(row: tuple[object, ...]) -> CrewMessage:
        delivered_at = datetime.fromisoformat(str(row[5])) if row[5] else None
        return CrewMessage(
            id=int(row[0]),
            recipient_id=str(row[1]),
            priority=str(row[2]),
            text=str(row[3]),
            created_at=datetime.fromisoformat(str(row[4])),
            delivered_at=delivered_at,
            status="delivered" if delivered_at else "queued",
        )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=5.0)
        try:
            with connection:
                yield connection
        finally:
            connection.close()
