"""Pure schedule execution-time calculations."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from math import ceil
from zoneinfo import ZoneInfo


def calculate_next_execution_at_utc(
    *,
    reference_at: datetime,
    timezone: str,
    window_start_local: time,
    window_end_local: time,
    interval_seconds: int,
) -> datetime:
    """Return the next interval boundary at or after reference time in UTC.

    Local times that do not exist during a daylight-saving jump are skipped;
    ambiguous local times use the earliest occurrence that is not in the past.
    """
    if reference_at.tzinfo is None or reference_at.utcoffset() is None:
        raise ValueError("reference_at must be timezone-aware")
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be greater than zero")
    if window_start_local >= window_end_local:
        raise ValueError("window_end_local must be later than window_start_local")

    zone = ZoneInfo(timezone)
    local_reference = reference_at.astimezone(zone)
    reference_wall_time = local_reference.replace(tzinfo=None)

    for day_offset in range(3):
        execution_date = local_reference.date() + timedelta(days=day_offset)
        window_start = datetime.combine(execution_date, window_start_local)
        window_end = datetime.combine(execution_date, window_end_local)
        elapsed = max(0.0, (reference_wall_time - window_start).total_seconds())
        interval_index = ceil(elapsed / interval_seconds)

        while True:
            candidate_wall_time = window_start + timedelta(
                seconds=interval_index * interval_seconds
            )
            if candidate_wall_time > window_end:
                break

            valid_instants: list[datetime] = []
            for fold in (0, 1):
                candidate = candidate_wall_time.replace(tzinfo=zone, fold=fold)
                candidate_utc = candidate.astimezone(UTC)
                round_trip = candidate_utc.astimezone(zone)
                if round_trip.replace(tzinfo=None) != candidate_wall_time:
                    continue
                if candidate_utc >= reference_at.astimezone(UTC):
                    valid_instants.append(candidate_utc)
            if valid_instants:
                return min(valid_instants)
            interval_index += 1

    raise ValueError("No valid execution time found in the next three schedule windows")


__all__ = ["calculate_next_execution_at_utc"]
