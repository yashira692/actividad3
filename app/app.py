"""Aplicación web para predicciones de partidos del Mundial.

Incluye salas, invitaciones por código, participantes, predicciones, resultados,
leaderboard y estadísticas básicas. Está diseñada para correr replicada detrás de
Nginx, por eso mantiene el estado en PostgreSQL y no en memoria local.
"""

from __future__ import annotations

import os
import random
import socket
import string
from datetime import datetime, timedelta, timezone
from typing import Any

from flask import Flask, jsonify, render_template, request

from db import get_conn, init_db, new_id, wait_for_database
from scoring import calculate_base_score, calculate_streak_bonus, is_winner_correct

app = Flask(__name__)


def parse_int(value: Any, field: str, minimum: int = 0) -> int:
    """Convierte valores recibidos por JSON en enteros seguros."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} debe ser un número entero")
    if parsed < minimum:
        raise ValueError(f"{field} debe ser mayor o igual a {minimum}")
    return parsed


def parse_datetime(value: str) -> datetime:
    """Acepta datetime ISO-8601 y normaliza a UTC cuando no hay zona horaria."""
    if not value:
        raise ValueError("La fecha/hora es obligatoria")
    value = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def generate_room_code(length: int = 6) -> str:
    """Genera un código corto para invitar participantes a una sala."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


def json_error(message: str, status: int = 400):
    return jsonify({"error": message}), status


def room_by_code(code: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM rooms WHERE code = %s", (code.upper(),))
            return cur.fetchone()


def calculate_leaderboard(room_id: str) -> list[dict[str, Any]]:
    """Calcula el tablero general usando resultados oficiales ya registrados."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.id AS participant_id, p.name AS participant_name
                FROM participants p
                WHERE p.room_id = %s
                ORDER BY p.created_at ASC
                """,
                (room_id,),
            )
            participants = cur.fetchall()

            leaderboard: list[dict[str, Any]] = []
            for participant in participants:
                cur.execute(
                    """
                    SELECT
                        pr.id AS prediction_id,
                        pr.pred_home,
                        pr.pred_away,
                        pr.created_at AS prediction_created_at,
                        m.id AS match_id,
                        m.home_team,
                        m.away_team,
                        m.starts_at,
                        m.home_score,
                        m.away_score,
                        m.status
                    FROM predictions pr
                    JOIN matches m ON m.id = pr.match_id
                    WHERE pr.participant_id = %s
                      AND m.status = 'finished'
                      AND m.home_score IS NOT NULL
                      AND m.away_score IS NOT NULL
                    ORDER BY m.starts_at ASC
                    """,
                    (participant["participant_id"],),
                )
                rows = cur.fetchall()

                evaluated = []
                total_without_streak = 0
                correct_flags = []

                for row in rows:
                    breakdown = calculate_base_score(
                        row["pred_home"],
                        row["pred_away"],
                        row["home_score"],
                        row["away_score"],
                        row["prediction_created_at"],
                        row["starts_at"],
                    )
                    winner_ok = is_winner_correct(
                        row["pred_home"], row["pred_away"], row["home_score"], row["away_score"]
                    )
                    correct_flags.append(winner_ok)
                    total_without_streak += breakdown.total
                    evaluated.append(
                        {
                            "match": f"{row['home_team']} vs {row['away_team']}",
                            "prediction": f"{row['pred_home']}-{row['pred_away']}",
                            "result": f"{row['home_score']}-{row['away_score']}",
                            "winner_correct": winner_ok,
                            "points_without_streak": breakdown.total,
                            "breakdown": breakdown.__dict__,
                        }
                    )

                streak_bonus = calculate_streak_bonus(correct_flags)
                leaderboard.append(
                    {
                        "participant_id": participant["participant_id"],
                        "name": participant["participant_name"],
                        "matches_evaluated": len(evaluated),
                        "points_base_and_early": total_without_streak,
                        "streak_bonus": streak_bonus,
                        "total_points": total_without_streak + streak_bonus,
                        "details": evaluated,
                    }
                )

            leaderboard.sort(key=lambda item: (-item["total_points"], item["name"].lower()))
            for position, item in enumerate(leaderboard, start=1):
                item["position"] = position
            return leaderboard


@app.route("/")
def index():
    return render_template("index.html", host=socket.gethostname())


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "node": socket.gethostname()})


@app.post("/api/rooms")
def create_room():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    owner_name = (data.get("owner_name") or "").strip()
    if not name or not owner_name:
        return json_error("El nombre de la sala y el responsable son obligatorios")

    with get_conn() as conn:
        with conn.cursor() as cur:
            # Intenta varios códigos por si ocurre una colisión improbable.
            for _ in range(10):
                code = generate_room_code()
                try:
                    room_id = new_id()
                    owner_id = new_id()
                    cur.execute(
                        "INSERT INTO rooms (id, code, name, owner_name) VALUES (%s, %s, %s, %s)",
                        (room_id, code, name, owner_name),
                    )
                    cur.execute(
                        "INSERT INTO participants (id, room_id, name) VALUES (%s, %s, %s)",
                        (owner_id, room_id, owner_name),
                    )
                    return jsonify(
                        {
                            "room": {"id": room_id, "code": code, "name": name, "owner_name": owner_name},
                            "owner_participant": {"id": owner_id, "name": owner_name},
                            "invite_url": f"/sala/{code}",
                        }
                    ), 201
                except Exception:
                    conn.rollback()
            return json_error("No se pudo generar un código de sala único", 500)


@app.get("/sala/<code>")
def room_page(code: str):
    room = room_by_code(code)
    if not room:
        return "Sala no encontrada", 404
    return render_template("index.html", host=socket.gethostname(), initial_code=code.upper())


@app.get("/api/rooms/<code>")
def get_room(code: str):
    room = room_by_code(code)
    if not room:
        return json_error("Sala no encontrada", 404)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, created_at FROM participants WHERE room_id = %s ORDER BY created_at ASC",
                (room["id"],),
            )
            participants = cur.fetchall()
    return jsonify({"room": dict(room), "participants": participants})


@app.post("/api/rooms/<code>/participants")
def join_room(code: str):
    room = room_by_code(code)
    if not room:
        return json_error("Sala no encontrada", 404)
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return json_error("El nombre del participante es obligatorio")

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO participants (id, room_id, name)
                VALUES (%s, %s, %s)
                ON CONFLICT (room_id, name) DO UPDATE SET name = EXCLUDED.name
                RETURNING id, name, created_at
                """,
                (new_id(), room["id"], name),
            )
            participant = cur.fetchone()
    return jsonify({"participant": participant}), 201


@app.get("/api/rooms/<code>/leaderboard")
def leaderboard(code: str):
    room = room_by_code(code)
    if not room:
        return json_error("Sala no encontrada", 404)
    return jsonify({"room": dict(room), "leaderboard": calculate_leaderboard(room["id"])})


@app.get("/api/matches")
def list_matches():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM matches ORDER BY starts_at ASC")
            matches = cur.fetchall()
    return jsonify({"matches": matches})


@app.post("/api/matches")
def create_match():
    data = request.get_json(force=True, silent=True) or {}
    home_team = (data.get("home_team") or "").strip()
    away_team = (data.get("away_team") or "").strip()
    if not home_team or not away_team:
        return json_error("Los equipos son obligatorios")
    try:
        starts_at = parse_datetime(data.get("starts_at"))
    except ValueError as exc:
        return json_error(str(exc))

    with get_conn() as conn:
        with conn.cursor() as cur:
            match_id = new_id()
            cur.execute(
                """
                INSERT INTO matches (id, home_team, away_team, starts_at)
                VALUES (%s, %s, %s, %s)
                RETURNING *
                """,
                (match_id, home_team, away_team, starts_at),
            )
            match = cur.fetchone()
    return jsonify({"match": match}), 201


@app.patch("/api/matches/<match_id>/result")
def update_result(match_id: str):
    data = request.get_json(force=True, silent=True) or {}
    try:
        home_score = parse_int(data.get("home_score"), "home_score")
        away_score = parse_int(data.get("away_score"), "away_score")
    except ValueError as exc:
        return json_error(str(exc))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE matches
                SET home_score = %s, away_score = %s, status = 'finished'
                WHERE id = %s
                RETURNING *
                """,
                (home_score, away_score, match_id),
            )
            match = cur.fetchone()
    if not match:
        return json_error("Partido no encontrado", 404)
    return jsonify({"match": match})


@app.post("/api/predictions")
def save_prediction():
    data = request.get_json(force=True, silent=True) or {}
    participant_id = data.get("participant_id")
    match_id = data.get("match_id")
    try:
        pred_home = parse_int(data.get("pred_home"), "pred_home")
        pred_away = parse_int(data.get("pred_away"), "pred_away")
    except ValueError as exc:
        return json_error(str(exc))

    if not participant_id or not match_id:
        return json_error("participant_id y match_id son obligatorios")

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT starts_at FROM matches WHERE id = %s", (match_id,))
            match = cur.fetchone()
            if not match:
                return json_error("Partido no encontrado", 404)

            # Se bloquea el registro durante los últimos 10 minutos para evitar cambios indebidos.
            now = datetime.now(timezone.utc)
            if match["starts_at"] - now <= timedelta(minutes=10):
                return json_error("La predicción se cerró 10 minutos antes del inicio del partido", 409)

            cur.execute("SELECT id FROM participants WHERE id = %s", (participant_id,))
            if not cur.fetchone():
                return json_error("Participante no encontrado", 404)

            cur.execute(
                """
                INSERT INTO predictions (id, participant_id, match_id, pred_home, pred_away)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (participant_id, match_id)
                DO UPDATE SET pred_home = EXCLUDED.pred_home,
                              pred_away = EXCLUDED.pred_away,
                              updated_at = NOW()
                RETURNING *
                """,
                (new_id(), participant_id, match_id, pred_home, pred_away),
            )
            prediction = cur.fetchone()
    return jsonify({"prediction": prediction}), 201


@app.get("/api/participants/<participant_id>/predictions")
def participant_predictions(participant_id: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT pr.*, m.home_team, m.away_team, m.starts_at, m.home_score, m.away_score, m.status
                FROM predictions pr
                JOIN matches m ON m.id = pr.match_id
                WHERE pr.participant_id = %s
                ORDER BY m.starts_at ASC
                """,
                (participant_id,),
            )
            predictions = cur.fetchall()
    return jsonify({"predictions": predictions})


@app.get("/api/stats/<code>")
def stats(code: str):
    """Estadísticas simples para el tablero de la sala."""
    room = room_by_code(code)
    if not room:
        return json_error("Sala no encontrada", 404)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM participants WHERE room_id = %s", (room["id"],))
            participants = cur.fetchone()["total"]
            cur.execute("SELECT COUNT(*) AS total FROM predictions pr JOIN participants p ON p.id = pr.participant_id WHERE p.room_id = %s", (room["id"],))
            predictions = cur.fetchone()["total"]
            cur.execute("SELECT COUNT(*) AS total FROM matches WHERE status = 'finished'")
            finished_matches = cur.fetchone()["total"]
    board = calculate_leaderboard(room["id"])
    leader = board[0] if board else None
    return jsonify(
        {
            "participants": participants,
            "predictions": predictions,
            "finished_matches": finished_matches,
            "leader": leader,
            "node": socket.gethostname(),
        }
    )


@app.errorhandler(500)
def internal_error(exc):  # pragma: no cover - respuesta defensiva
    return jsonify({"error": "Error interno del servidor", "detail": str(exc)}), 500


# Gunicorn importa este módulo; por eso la inicialización se ejecuta al cargar la app.
wait_for_database()
init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")), debug=True)
