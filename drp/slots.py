"""Helpers to enumerate and format the 2-hour availability blocks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import re

from .config import DAY_END_HOUR, DRP, SCHEDULE_WINDOW, SLOT_START_HOURS

_KEY_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\|(\d{1,2})$")


@dataclass(frozen=True)
class Slot:
    day: date
    hour: int

    @property
    def key(self) -> str:
        return slot_key(self.day, self.hour)


def slot_key(day: date, hour: int) -> str:
    return f"{day.isoformat()}|{hour}"


def parse_slot_key(key: str) -> tuple[date, int] | None:
    m = _KEY_RE.match(key)
    if not m:
        return None
    return date.fromisoformat(m.group(1)), int(m.group(2))


def schedule_dates() -> list[date]:
    """Every eligible calendar day in the window."""
    out: list[date] = []
    cur = SCHEDULE_WINDOW["start"]
    end = SCHEDULE_WINDOW["end"]
    while cur <= end:
        if cur.weekday() in SCHEDULE_WINDOW["allowed_weekdays"] and cur not in SCHEDULE_WINDOW["excluded_dates"]:
            out.append(cur)
        cur += timedelta(days=1)
    return out


def all_slots() -> list[Slot]:
    """Every 1-hour cell a member can mark."""
    return [Slot(d, h) for d in schedule_dates() for h in SLOT_START_HOURS]


def valid_slot_keys() -> set[str]:
    return {s.key for s in all_slots()}


def window_start_hours() -> list[int]:
    """Start hours of every possible `duration_hours`-long window within the day."""
    dur = DRP["duration_hours"]
    return [h for h in SLOT_START_HOURS if h + dur <= DAY_END_HOUR]


def window_hours(start: int) -> list[int]:
    """The 1-hour cells covered by a window starting at `start`."""
    return list(range(start, start + DRP["duration_hours"]))


def find_windows(availability: dict[int, set[str]], total: int) -> tuple[list[tuple[date, int, list[int]]], list[tuple[date, int, list[int]]]]:
    """
    Given {member_id: set(slot_key)}, return (full, near):
      full = windows where every member is free for the whole window
      near = windows where exactly one member is missing
    Each entry is (date, start_hour, [missing_member_ids]).
    """
    full: list[tuple[date, int, list[int]]] = []
    near: list[tuple[date, int, list[int]]] = []
    if total == 0:
        return full, near
    for d in schedule_dates():
        for start in window_start_hours():
            needed = {slot_key(d, h) for h in window_hours(start)}
            missing = [mid for mid, keys in availability.items() if not needed <= keys]
            if not missing:
                full.append((d, start, []))
            elif len(missing) == 1 and total > 1:
                near.append((d, start, missing))
    return full, near


def weeks() -> list[list[date]]:
    """Group eligible dates by Monday-anchored week for grid rendering."""
    grouped: list[list[date]] = []
    current: list[date] = []
    current_monday: date | None = None
    for d in schedule_dates():
        monday = d - timedelta(days=d.weekday())
        if monday != current_monday:
            if current:
                grouped.append(current)
            current = []
            current_monday = monday
        current.append(d)
    if current:
        grouped.append(current)
    return grouped


def fmt_hour(h: int) -> str:
    suffix = "PM" if h >= 12 else "AM"
    h12 = 12 if h % 12 == 0 else h % 12
    return f"{h12}:00 {suffix}"


def fmt_hour_short(h: int) -> str:
    suffix = "pm" if h >= 12 else "am"
    h12 = 12 if h % 12 == 0 else h % 12
    return f"{h12}{suffix}"


def fmt_range(hour: int, length: int | None = None) -> str:
    """'10:00 AM – 12:00 PM'. Defaults to the full presentation length."""
    length = DRP["duration_hours"] if length is None else length
    return f"{fmt_hour(hour)} – {fmt_hour(hour + length)}"


def fmt_range_short(hour: int, length: int | None = None) -> str:
    length = DRP["duration_hours"] if length is None else length
    return f"{fmt_hour_short(hour)}–{fmt_hour_short(hour + length)}"


def fmt_date(d: date, style: str = "short") -> str:
    if style == "short":  # Mon, Nov 2
        return d.strftime("%a, %b %-d")
    if style == "long":  # Monday, November 2
        return d.strftime("%A, %B %-d")
    if style == "month_day":  # November 2
        return d.strftime("%B %-d")
    if style == "full":  # November 2, 2026
        return d.strftime("%B %-d, %Y")
    return d.isoformat()
