"""Locale-independent dates for the Spanish dashboard."""

from datetime import date

MONTHS_ES = (
    "ene",
    "feb",
    "mar",
    "abr",
    "may",
    "jun",
    "jul",
    "ago",
    "sep",
    "oct",
    "nov",
    "dic",
)


def short_date(day: date, *, year: bool = False) -> str:
    label = f"{day.day} {MONTHS_ES[day.month - 1]}"
    return f"{label} {day.year}" if year else label


def short_range(start: date, end: date) -> str:
    year = start.year != end.year
    return f"{short_date(start, year=year)} al {short_date(end, year=year)}"
