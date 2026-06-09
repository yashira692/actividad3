"""Reglas de puntuación para el predictor del Mundial.

Este módulo está separado de Flask para poder probar las reglas de negocio sin levantar
la aplicación web ni la base de datos.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Optional


@dataclass(frozen=True)
class ScoreBreakdown:
    """Detalle de puntos obtenido por una predicción evaluada."""

    exact_points: int = 0
    winner_points: int = 0
    goal_diff_points: int = 0
    early_points: int = 0
    streak_bonus_points: int = 0

    @property
    def total(self) -> int:
        return (
            self.exact_points
            + self.winner_points
            + self.goal_diff_points
            + self.early_points
            + self.streak_bonus_points
        )


def _winner(home_goals: int, away_goals: int) -> str:
    """Retorna H, A o D para local, visitante o empate."""
    if home_goals > away_goals:
        return "H"
    if away_goals > home_goals:
        return "A"
    return "D"


def _goal_difference(home_goals: int, away_goals: int) -> int:
    """Diferencia de goles desde la perspectiva del equipo local."""
    return home_goals - away_goals


def is_winner_correct(pred_home: int, pred_away: int, real_home: int, real_away: int) -> bool:
    """Indica si la predicción acierta ganador o empate."""
    return _winner(pred_home, pred_away) == _winner(real_home, real_away)


def is_goal_difference_correct(pred_home: int, pred_away: int, real_home: int, real_away: int) -> bool:
    """Indica si acierta el margen de victoria, sin ser marcador exacto.

    Para evitar premiar márgenes en sentidos contrarios, se exige que también coincida
    el ganador/empate. Ejemplo válido: predice 3-1 y termina 2-0; ambos tienen margen
    +2 para el local.
    """
    return (
        _goal_difference(pred_home, pred_away) == _goal_difference(real_home, real_away)
        and is_winner_correct(pred_home, pred_away, real_home, real_away)
    )


def is_early_prediction(prediction_created_at: datetime, match_starts_at: datetime) -> bool:
    """Valida si la predicción fue registrada con más de 24 horas de anticipación."""
    if prediction_created_at.tzinfo is None:
        prediction_created_at = prediction_created_at.replace(tzinfo=timezone.utc)
    if match_starts_at.tzinfo is None:
        match_starts_at = match_starts_at.replace(tzinfo=timezone.utc)
    seconds_before_match = (match_starts_at - prediction_created_at).total_seconds()
    return seconds_before_match > 24 * 60 * 60


def calculate_base_score(
    pred_home: int,
    pred_away: int,
    real_home: int,
    real_away: int,
    prediction_created_at: Optional[datetime] = None,
    match_starts_at: Optional[datetime] = None,
) -> ScoreBreakdown:
    """Calcula los puntos base y el punto extra por predicción anticipada.

    Criterio aplicado:
    - Marcador exacto: 5 puntos y no suma adicional por ganador/diferencia.
    - Si no es exacto: ganador correcto suma 3; diferencia correcta suma 2.
    - Anticipación mayor a 24 horas: suma 1 punto adicional.
    """
    exact = pred_home == real_home and pred_away == real_away

    exact_points = 5 if exact else 0
    winner_points = 0 if exact else (3 if is_winner_correct(pred_home, pred_away, real_home, real_away) else 0)
    goal_diff_points = 0 if exact else (2 if is_goal_difference_correct(pred_home, pred_away, real_home, real_away) else 0)

    early_points = 0
    if prediction_created_at is not None and match_starts_at is not None:
        early_points = 1 if is_early_prediction(prediction_created_at, match_starts_at) else 0

    return ScoreBreakdown(
        exact_points=exact_points,
        winner_points=winner_points,
        goal_diff_points=goal_diff_points,
        early_points=early_points,
    )


def calculate_streak_bonus(winner_correct_flags: Iterable[bool]) -> int:
    """Suma 2 puntos por cada bloque de 3 aciertos consecutivos de ganador.

    Ejemplos:
    - TTT => 2 puntos
    - TTTT => 2 puntos
    - TTTTTT => 4 puntos
    - TTFTTT => 2 puntos
    """
    consecutive = 0
    bonus = 0
    for correct in winner_correct_flags:
        if correct:
            consecutive += 1
            if consecutive % 3 == 0:
                bonus += 2
        else:
            consecutive = 0
    return bonus
