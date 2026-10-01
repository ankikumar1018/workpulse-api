"""Tests for timezone-aware schedule execution calculations."""

from datetime import UTC, datetime, time

import pytest

from app.domain.scheduling import calculate_next_execution_at_utc


def calculate(reference_at: datetime) -> datetime:
    return calculate_next_execution_at_utc(
        reference_at=reference_at,
        timezone="America/Los_Angeles",
        window_start_local=time(8, 0),
        window_end_local=time(17, 0),
        interval_seconds=3600,
    )


def test_next_execution_uses_window_start_before_daily_window():
    next_run = calculate(datetime(2026, 10, 1, 13, 0, tzinfo=UTC))

    assert next_run == datetime(2026, 10, 1, 15, 0, tzinfo=UTC)


def test_next_execution_uses_next_interval_inside_window():
    next_run = calculate(datetime(2026, 10, 1, 17, 15, tzinfo=UTC))

    assert next_run == datetime(2026, 10, 1, 18, 0, tzinfo=UTC)


def test_next_execution_rolls_to_next_local_day_after_window():
    next_run = calculate(datetime(2026, 10, 2, 1, 0, tzinfo=UTC))

    assert next_run == datetime(2026, 10, 2, 15, 0, tzinfo=UTC)


def test_next_execution_skips_nonexistent_spring_forward_times():
    next_run = calculate_next_execution_at_utc(
        reference_at=datetime(2026, 3, 8, 9, 45, tzinfo=UTC),
        timezone="America/Los_Angeles",
        window_start_local=time(1, 0),
        window_end_local=time(4, 0),
        interval_seconds=1800,
    )

    assert next_run == datetime(2026, 3, 8, 10, 0, tzinfo=UTC)


def test_next_execution_selects_future_occurrence_during_fall_back_fold():
    next_run = calculate_next_execution_at_utc(
        reference_at=datetime(2026, 11, 1, 9, 20, tzinfo=UTC),
        timezone="America/Los_Angeles",
        window_start_local=time(1, 0),
        window_end_local=time(2, 30),
        interval_seconds=1800,
    )

    assert next_run == datetime(2026, 11, 1, 9, 30, tzinfo=UTC)


def test_next_execution_requires_aware_reference_time():
    with pytest.raises(ValueError, match="timezone-aware"):
        calculate(datetime(2026, 10, 1, 13, 0))
