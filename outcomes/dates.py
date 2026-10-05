"""Bounds of a complete or partial registry date."""

import calendar


def interval(s):
    if len(s) == 10:
        return (s, s)
    if len(s) == 7:
        y, m = map(int, s.split("-"))
        return (s + "-01", s + f"-{calendar.monthrange(y, m)[1]:02}")
    if len(s) == 4:
        return (s + "-01-01", s + "-12-31")
    raise ValueError(f"Invalid date {s}")
