from datetime import datetime, timedelta, timezone

from app.scoring import (
    calculate_base_score,
    calculate_streak_bonus,
    is_goal_difference_correct,
    is_winner_correct,
)


def test_exact_score_gets_five_points_only_for_base_result():
    score = calculate_base_score(2, 1, 2, 1)
    assert score.exact_points == 5
    assert score.winner_points == 0
    assert score.goal_diff_points == 0
    assert score.total == 5


def test_winner_correct_gets_three_points_when_not_exact():
    score = calculate_base_score(1, 0, 3, 1)
    assert score.winner_points == 3
    assert score.total == 3


def test_goal_difference_correct_gets_two_points_and_winner_points():
    score = calculate_base_score(3, 1, 2, 0)
    assert score.winner_points == 3
    assert score.goal_diff_points == 2
    assert score.total == 5


def test_draw_winner_logic():
    assert is_winner_correct(1, 1, 0, 0) is True
    assert is_goal_difference_correct(1, 1, 0, 0) is True


def test_early_prediction_bonus():
    created = datetime(2026, 6, 1, 10, tzinfo=timezone.utc)
    starts = created + timedelta(hours=25)
    score = calculate_base_score(0, 0, 0, 0, created, starts)
    assert score.early_points == 1
    assert score.total == 6


def test_no_early_bonus_at_exactly_24_hours():
    created = datetime(2026, 6, 1, 10, tzinfo=timezone.utc)
    starts = created + timedelta(hours=24)
    score = calculate_base_score(0, 0, 0, 0, created, starts)
    assert score.early_points == 0


def test_streak_bonus_every_three_consecutive_winner_hits():
    assert calculate_streak_bonus([True, True, True]) == 2
    assert calculate_streak_bonus([True, True, True, True, True, True]) == 4
    assert calculate_streak_bonus([True, True, False, True, True, True]) == 2
