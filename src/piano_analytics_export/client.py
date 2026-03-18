"""Piano API client: fetch, retry with rate-limit handling, and pagination."""
from __future__ import annotations

import json
import time
from typing import Any

import pandas as pd
import requests

from piano_analytics_export.logging import print_table_row

API_ENDPOINT = "https://api.atinternet.io/v3/data/getData"
MAX_ROWS_PER_PAGE = 10_000
MAX_PAGES = 20  # 200_000 / 10_000

REQUEST_TEMPLATE = {
    "period": {
        "p1": [
            {
                "type": "D",
                "start": "{{start}}",
                "end": "{{end}}",
            }
        ]
    },
    "max-results": 10000,
    "page-num": 1,
}


def render_payload(replacements: dict[str, str]) -> dict:
    payload_text = json.dumps(REQUEST_TEMPLATE)
    for placeholder, value in replacements.items():
        payload_text = payload_text.replace(f"{{{{{placeholder}}}}}", value)
    return json.loads(payload_text)


def build_headers(api_key: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "x-api-key": api_key,
    }


def response_to_dataframe(payload: dict[str, Any]) -> pd.DataFrame:
    data_feed = payload["DataFeed"]
    rows = data_feed.get("Rows", [])
    columns = [col["Name"] for col in data_feed.get("Columns", [])]
    df = pd.DataFrame(rows)
    if columns:
        df = df.reindex(columns=columns)
    return df


def _post_with_retry(
    session: requests.Session,
    payload: dict,
    headers: dict[str, str],
    timeout: int,
    beschreibung: str,
    start_date: str,
    end_date: str,
) -> tuple[requests.Response | None, bool]:
    """POST with 429 retry logic. Returns (response, rate_limited)."""
    attempt = 0
    total_wait = 0
    while True:
        try:
            response = session.post(API_ENDPOINT, json=payload, headers=headers, timeout=timeout)
            if response.status_code == 429:
                if total_wait >= 60:
                    print_table_row("ABORT", beschreibung, start_date, end_date, f"429 after {total_wait}s wait", level=0)
                    return None, True
                attempt += 1
                wait_seconds = attempt * 10
                total_wait += wait_seconds
                print_table_row("WAIT", beschreibung, start_date, end_date, f"429 wait {wait_seconds}s")
                time.sleep(wait_seconds)
                print_table_row("RETRY", beschreibung, start_date, end_date, f"Attempt {attempt}")
                continue
            response.raise_for_status()
            return response, False
        except requests.exceptions.RequestException as exc:
            print_table_row("ERROR", beschreibung, start_date, end_date, str(exc), level=0)
            return None, False


def fetch_for_entry(
    entry: dict[str, Any],
    start_date: str,
    end_date: str,
    timeout: int,
) -> tuple[pd.DataFrame | None, bool]:
    beschreibung = entry.get("beschreibung")
    api_key = entry.get("api_key")
    if not beschreibung or not api_key:
        print_table_row(
            "SKIP",
            beschreibung or "unbekannt",
            start_date,
            end_date,
            "Missing beschreibung/api_key",
        )
        return None, False

    try:
        payload = render_payload({"start": start_date, "end": end_date})
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Template render invalid JSON for {beschreibung}: {exc}")

    headers = build_headers(api_key)
    print_table_row("READY", beschreibung, start_date, end_date, "Prepared request")

    session = requests.Session()
    all_frames: list[pd.DataFrame] = []

    for page_num in range(1, MAX_PAGES + 1):
        paged_payload = {**payload, "max-results": MAX_ROWS_PER_PAGE, "page-num": page_num}
        response, rate_limited = _post_with_retry(
            session, paged_payload, headers, timeout, beschreibung, start_date, end_date
        )
        if rate_limited:
            return None, True
        if response is None:
            return None, False

        df = response_to_dataframe(response.json())
        raw_row_count = len(df)
        all_frames.append(df)

        if raw_row_count < MAX_ROWS_PER_PAGE:
            break

        print_table_row("PAGE", beschreibung, start_date, end_date, f"Page {page_num} full ({MAX_ROWS_PER_PAGE} rows), fetching next")

        if page_num == MAX_PAGES:
            print_table_row("WARN", beschreibung, start_date, end_date, f"Reached page limit ({MAX_PAGES}), result may be truncated", level=0)

    result = pd.concat(all_frames, ignore_index=True) if len(all_frames) > 1 else all_frames[0]
    total_rows = len(result)
    pages_fetched = len(all_frames)
    suffix = f" ({pages_fetched} pages)" if pages_fetched > 1 else ""
    print_table_row("OK", beschreibung, start_date, end_date, f"Rows {total_rows}{suffix}")
    return result, False
