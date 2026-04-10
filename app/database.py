from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


class Database:
    def __init__(self, db_path: Path, catalog: list[dict[str, str]]) -> None:
        self.db_path = Path(db_path)
        self.catalog = catalog
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS products (
                    sku TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    class_name TEXT NOT NULL UNIQUE
                );

                CREATE TABLE IF NOT EXISTS detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sku TEXT NOT NULL,
                    class_name TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    track_id INTEGER NOT NULL,
                    detected_at TEXT NOT NULL,
                    FOREIGN KEY (sku) REFERENCES products (sku)
                );

                CREATE TABLE IF NOT EXISTS inventory (
                    sku TEXT PRIMARY KEY,
                    quantity INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (sku) REFERENCES products (sku)
                );
                """
            )

            for product in self.catalog:
                sku = product["sku"]
                name = product["name"]
                class_name = product["class_name"]
                conn.execute(
                    """
                    INSERT OR IGNORE INTO products (sku, name, class_name)
                    VALUES (?, ?, ?)
                    """,
                    (sku, name, class_name),
                )
                conn.execute(
                    """
                    INSERT OR IGNORE INTO inventory (sku, quantity, updated_at)
                    VALUES (?, 0, ?)
                    """,
                    (sku, self.now_iso()),
                )

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def get_products(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT sku, name, class_name FROM products ORDER BY name"
            ).fetchall()
        return [dict(row) for row in rows]

    def reset_inventory(self) -> None:
        timestamp = self.now_iso()
        with self.connect() as conn:
            conn.execute("DELETE FROM detections")
            conn.execute(
                """
                UPDATE inventory
                SET quantity = 0,
                    updated_at = ?
                """,
                (timestamp,),
            )

    def get_inventory(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT p.sku, p.name, p.class_name, i.quantity, i.updated_at
                FROM inventory i
                JOIN products p ON p.sku = i.sku
                ORDER BY p.name
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_recent_detections(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT d.id, d.sku, p.name, d.class_name, d.confidence, d.track_id, d.detected_at
                FROM detections d
                JOIN products p ON p.sku = d.sku
                ORDER BY d.detected_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_sku_for_class(self, class_name: str) -> str | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT sku FROM products WHERE class_name = ?",
                (class_name,),
            ).fetchone()
        return row["sku"] if row else None

    def register_detection(
        self,
        *,
        sku: str,
        class_name: str,
        confidence: float,
        track_id: int,
    ) -> None:
        timestamp = self.now_iso()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO detections (sku, class_name, confidence, track_id, detected_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (sku, class_name, confidence, track_id, timestamp),
            )
            conn.execute(
                """
                UPDATE inventory
                SET quantity = quantity + 1,
                    updated_at = ?
                WHERE sku = ?
                """,
                (timestamp, sku),
            )
