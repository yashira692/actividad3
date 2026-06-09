"""Acceso a PostgreSQL y creación automática del esquema.

La aplicación está pensada para ejecutarse en Docker Compose con PostgreSQL. Al iniciar,
crea las tablas necesarias y algunos partidos de ejemplo para facilitar la demostración.
"""

from __future__ import annotations

import os
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Iterator

import psycopg2
from psycopg2.extras import RealDictCursor


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/worldcup")


def new_id() -> str:
    return str(uuid.uuid4())


@contextmanager
def get_conn() -> Iterator[psycopg2.extensions.connection]:
    """Abre una conexión transaccional a PostgreSQL."""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def wait_for_database(max_attempts: int = 30) -> None:
    """Espera a que PostgreSQL esté disponible antes de iniciar Flask/Gunicorn."""
    last_error: Exception | None = None
    for _ in range(max_attempts):
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            return
        except Exception as exc:  # pragma: no cover - depende del contenedor
            last_error = exc
            time.sleep(1)
    raise RuntimeError(f"No se pudo conectar a la base de datos: {last_error}")


def init_db() -> None:
    """Crea tablas e inserta datos de demostración si la base está vacía."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS rooms (
                    id UUID PRIMARY KEY,
                    code VARCHAR(12) UNIQUE NOT NULL,
                    name VARCHAR(120) NOT NULL,
                    owner_name VARCHAR(120) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS participants (
                    id UUID PRIMARY KEY,
                    room_id UUID NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                    name VARCHAR(120) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE(room_id, name)
                );

                CREATE TABLE IF NOT EXISTS matches (
                    id UUID PRIMARY KEY,
                    home_team VARCHAR(80) NOT NULL,
                    away_team VARCHAR(80) NOT NULL,
                    starts_at TIMESTAMPTZ NOT NULL,
                    home_score INTEGER,
                    away_score INTEGER,
                    status VARCHAR(20) NOT NULL DEFAULT 'scheduled',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE(home_team, away_team, starts_at),
                    CONSTRAINT valid_result CHECK (
                        (home_score IS NULL AND away_score IS NULL)
                        OR (home_score >= 0 AND away_score >= 0)
                    )
                );

                CREATE TABLE IF NOT EXISTS predictions (
                    id UUID PRIMARY KEY,
                    participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
                    match_id UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
                    pred_home INTEGER NOT NULL CHECK (pred_home >= 0),
                    pred_away INTEGER NOT NULL CHECK (pred_away >= 0),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE(participant_id, match_id)
                );
                """
            )

            cur.execute("SELECT COUNT(*) AS total FROM matches")
            if cur.fetchone()["total"] == 0:
                now = datetime.now(timezone.utc)
                sample_matches = [
                    ("Perú", "Brasil", now + timedelta(days=2, hours=3)),
                    ("Argentina", "Francia", now + timedelta(days=3, hours=1)),
                    ("España", "Alemania", now + timedelta(days=4, hours=2)),
                    ("Japón", "Croacia", now + timedelta(days=5, hours=4)),
                    ("México", "Uruguay", now + timedelta(days=6, hours=1)),
                    ("Inglaterra", "Portugal", now + timedelta(days=7, hours=2)),
                ]
                for home, away, starts_at in sample_matches:
                    cur.execute(
                        """
                        INSERT INTO matches (id, home_team, away_team, starts_at)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (home_team, away_team, starts_at) DO NOTHING
                        """,
                        (new_id(), home, away, starts_at),
                    )
