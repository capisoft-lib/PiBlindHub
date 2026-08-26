"""Transactional control state and audit event persistence."""

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from piblindhub.domain import Direction, PositionConfidence, PositionEstimate, utc_now_iso


@dataclass(frozen=True)
class PersistedState:
    movement_active: bool
    direction: Optional[Direction]
    position: PositionEstimate
    movement_started_at: Optional[str]
    last_stop_reason: Optional[str]
    last_error: Optional[str]


class StateRepository:
    def __init__(self, database_path: str) -> None:
        self.path = Path(database_path)

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(self.path), timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS runtime_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    movement_active INTEGER NOT NULL DEFAULT 0,
                    direction TEXT,
                    position REAL,
                    position_confidence TEXT NOT NULL DEFAULT 'unknown',
                    position_updated_at TEXT NOT NULL,
                    movement_started_at TEXT,
                    last_stop_reason TEXT,
                    last_error TEXT,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS control_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    occurred_at TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    details_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_control_events_occurred_at
                    ON control_events(occurred_at DESC);
                """
            )
            now = utc_now_iso()
            connection.execute(
                """
                INSERT OR IGNORE INTO runtime_state (
                    id, movement_active, direction, position, position_confidence,
                    position_updated_at, movement_started_at, last_stop_reason,
                    last_error, updated_at
                ) VALUES (1, 0, NULL, NULL, 'unknown', ?, NULL, 'initialization', NULL, ?)
                """,
                (now, now),
            )

    def load(self) -> PersistedState:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM runtime_state WHERE id = 1").fetchone()
        assert row is not None
        direction = Direction(row["direction"]) if row["direction"] else None
        confidence = PositionConfidence(row["position_confidence"])
        position = PositionEstimate(
            value=row["position"],
            confidence=confidence,
            updated_at=row["position_updated_at"],
        )
        return PersistedState(
            movement_active=bool(row["movement_active"]),
            direction=direction,
            position=position,
            movement_started_at=row["movement_started_at"],
            last_stop_reason=row["last_stop_reason"],
            last_error=row["last_error"],
        )

    def mark_movement_started(self, direction: Direction) -> str:
        now = utc_now_iso()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE runtime_state
                SET movement_active = 1, direction = ?, movement_started_at = ?,
                    last_error = NULL, updated_at = ?
                WHERE id = 1
                """,
                (direction.value, now, now),
            )
            self._append_event(connection, "movement_started", {"direction": direction.value}, now)
        return now

    def mark_stopped(
        self,
        position: PositionEstimate,
        reason: str,
        clear_error: bool = True,
    ) -> None:
        now = utc_now_iso()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE runtime_state
                SET movement_active = 0, direction = NULL, position = ?,
                    position_confidence = ?, position_updated_at = ?,
                    movement_started_at = NULL, last_stop_reason = ?,
                    last_error = CASE WHEN ? THEN NULL ELSE last_error END,
                    updated_at = ?
                WHERE id = 1
                """,
                (
                    position.value,
                    position.confidence.value,
                    position.updated_at,
                    reason,
                    clear_error,
                    now,
                ),
            )
            self._append_event(connection, "movement_stopped", {"reason": reason}, now)

    def mark_position_unknown(self, reason: str) -> PositionEstimate:
        position = PositionEstimate.unknown()
        now = utc_now_iso()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE runtime_state
                SET movement_active = 0, direction = NULL, position = NULL,
                    position_confidence = 'unknown', position_updated_at = ?,
                    movement_started_at = NULL, last_stop_reason = ?, updated_at = ?
                WHERE id = 1
                """,
                (position.updated_at, reason, now),
            )
            self._append_event(connection, "position_unknown", {"reason": reason}, now)
        return position

    def clear_fault(self, reason: str) -> PositionEstimate:
        position = PositionEstimate.unknown()
        now = utc_now_iso()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE runtime_state
                SET movement_active = 0, direction = NULL, position = NULL,
                    position_confidence = 'unknown', position_updated_at = ?,
                    movement_started_at = NULL, last_stop_reason = ?,
                    last_error = NULL, updated_at = ?
                WHERE id = 1
                """,
                (position.updated_at, reason, now),
            )
            self._append_event(connection, "fault_cleared", {"reason": reason}, now)
        return position

    def set_estimated_position(self, value: float, reason: str) -> PositionEstimate:
        position = PositionEstimate.estimated(value)
        now = utc_now_iso()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE runtime_state
                SET position = ?, position_confidence = 'estimated',
                    position_updated_at = ?, updated_at = ?
                WHERE id = 1
                """,
                (position.value, position.updated_at, now),
            )
            self._append_event(
                connection,
                "estimated_position_set",
                {"position": position.value, "reason": reason},
                now,
            )
        return position

    def mark_fault(self, error: str) -> None:
        now = utc_now_iso()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE runtime_state
                SET movement_active = 0, direction = NULL, position = NULL,
                    position_confidence = 'unknown', position_updated_at = ?,
                    movement_started_at = NULL, last_error = ?, updated_at = ?
                WHERE id = 1
                """,
                (now, error, now),
            )
            self._append_event(connection, "fault", {"error": error}, now)

    def append_event(self, event_type: str, details: dict[str, Any]) -> None:
        with self._connect() as connection:
            self._append_event(connection, event_type, details, utc_now_iso())

    def _append_event(
        self,
        connection: sqlite3.Connection,
        event_type: str,
        details: dict[str, Any],
        occurred_at: str,
    ) -> None:
        connection.execute(
            "INSERT INTO control_events (occurred_at, event_type, details_json) VALUES (?, ?, ?)",
            (occurred_at, event_type, json.dumps(details, sort_keys=True)),
        )

    def recent_events(self, limit: int = 100) -> list[dict[str, Any]]:
        safe_limit = max(1, min(500, int(limit)))
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, occurred_at, event_type, details_json
                FROM control_events ORDER BY id DESC LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "occurred_at": row["occurred_at"],
                "event_type": row["event_type"],
                "details": json.loads(row["details_json"]),
            }
            for row in rows
        ]
