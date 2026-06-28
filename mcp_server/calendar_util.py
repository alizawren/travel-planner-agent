from datetime import date, datetime, time, timedelta
from pathlib import Path

from icalendar import Calendar
import recurring_ical_events


def _dates_in_range(start: date, end: date) -> set[date]:
    days: set[date] = set()
    current = start
    while current <= end:
        days.add(current)
        current += timedelta(days=1)
    return days


def _event_busy_dates(component) -> set[date]:
    dtstart = component.decoded("dtstart")
    dtend = component.decoded("dtend")

    if isinstance(dtstart, datetime):
        start = dtstart.date()
    else:
        start = dtstart

    if dtend is None:
        return {start}

    if isinstance(dtend, datetime):
        if dtend.time() == time.min and dtend.date() > start:
            end = dtend.date() - timedelta(days=1)
        else:
            end = dtend.date()
    else:
        end = dtend - timedelta(days=1)

    if end < start:
        end = start
    return _dates_in_range(start, end)


def _collect_busy_dates(
    calendar: Calendar, horizon_start: date, horizon_end: date
) -> set[date]:
    busy: set[date] = set()
    range_start = datetime.combine(horizon_start, time.min)
    range_end = datetime.combine(horizon_end, time.max)

    for component in recurring_ical_events.of(calendar).between(range_start, range_end):
        if component.get("STATUS") == "CANCELLED":
            continue
        if component.get("TRANSP") == "TRANSPARENT":
            continue
        busy |= _event_busy_dates(component)

    return {day for day in busy if horizon_start <= day <= horizon_end}


def _find_soonest_date_ranges(
    busy: set[date],
    min_trip_days: int,
    max_trip_days: int,
    start_from: date,
    search_until: date,
    num_date_ranges: int,
) -> list[tuple[date, date]]:
    trips: list[tuple[date, date]] = []
    current = start_from

    while current <= search_until and len(trips) < num_date_ranges:
        trip = _find_next_date_range(
            busy, min_trip_days, max_trip_days, current, search_until
        )
        if trip is None:
            break

        trips.append(trip)
        current = trip[1] + timedelta(days=1)

    return trips


def _find_next_date_range(
    busy: set[date],
    min_trip_days: int,
    max_trip_days: int,
    start_from: date,
    search_until: date,
) -> tuple[date, date] | None:
    current = start_from
    while current <= search_until:
        if current in busy:
            current += timedelta(days=1)
            continue

        free_run = 0
        probe = current
        while probe <= search_until and probe not in busy:
            free_run += 1
            probe += timedelta(days=1)

        if free_run >= min_trip_days:
            trip_days = min(free_run, max_trip_days)
            return current, current + timedelta(days=trip_days - 1)

        current = probe

    return None


def find_soonest_free_dates(
    calendar_path: Path,
    min_trip_days: int = 2,
    max_trip_days: int = 15,
    num_date_ranges: int = 5,
) -> list[dict]:
    if min_trip_days < 1:
        raise ValueError("min_trip_days must be at least 1")
    if max_trip_days < min_trip_days:
        raise ValueError("max_trip_days must be greater than or equal to min_trip_days")
    if num_date_ranges < 1:
        raise ValueError("num_date_ranges must be at least 1")
    if not calendar_path.is_file():
        raise ValueError(f"Not a file: {calendar_path}")

    calendar = Calendar.from_ical(calendar_path.read_text(encoding="utf-8"))

    today = date.today()
    search_until = today + timedelta(days=365 * 2)
    busy = _collect_busy_dates(calendar, today, search_until)

    trips = _find_soonest_date_ranges(
        busy, min_trip_days, max_trip_days, today, search_until, num_date_ranges
    )
    if not trips:
        return {"error": "No free dates found within the search window", "date_ranges": []}

    date_ranges = []
    for start_date, end_date in trips:
        trip_days = (end_date - start_date).days + 1
        date_ranges.append(
            {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "trip_days": trip_days,
            }
        )

    return date_ranges
