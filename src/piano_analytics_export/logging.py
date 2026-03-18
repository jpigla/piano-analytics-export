"""Thread-safe table logging for CLI output."""
from __future__ import annotations

import threading

TABLE_COLUMNS = [
    ("Status", 10),
    ("Beschreibung", 24),
    ("Range", 23),
    ("Message", 60),
]
_PRINT_LOCK = threading.Lock()
LOG_LEVEL = 1


def set_log_level(level: int) -> None:
    global LOG_LEVEL
    LOG_LEVEL = level


def _truncate(value: str, width: int) -> str:
    if len(value) <= width:
        return value
    if width <= 3:
        return value[:width]
    return value[: width - 3] + "..."


def _table_line() -> str:
    return "+".join("-" * width for _, width in TABLE_COLUMNS)


def print_table_header() -> None:
    if LOG_LEVEL == 0:
        return
    header = " ".join(_truncate(label, width).ljust(width) for label, width in TABLE_COLUMNS)
    with _PRINT_LOCK:
        print(header)
        print(_table_line())


def print_table_row(
    status: str,
    beschreibung: str,
    start_date: str,
    end_date: str,
    message: str,
    level: int = 1,
) -> None:
    if LOG_LEVEL < level:
        return
    values = [
        _truncate(status, TABLE_COLUMNS[0][1]).ljust(TABLE_COLUMNS[0][1]),
        _truncate(beschreibung, TABLE_COLUMNS[1][1]).ljust(TABLE_COLUMNS[1][1]),
        _truncate(f"{start_date}..{end_date}", TABLE_COLUMNS[2][1]).ljust(TABLE_COLUMNS[2][1]),
        _truncate(message, TABLE_COLUMNS[3][1]).ljust(TABLE_COLUMNS[3][1]),
    ]
    with _PRINT_LOCK:
        print(" ".join(values))
