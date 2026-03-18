"""CLI entry point for piano-analytics-export."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
from pathlib import Path

import pandas as pd

from piano_analytics_export.config import (
    DEFAULT_CONFIG_PATH,
    build_inline_credentials,
    init_config,
    load_config,
)
from piano_analytics_export.client import fetch_for_entry, render_payload
from piano_analytics_export.logging import print_table_header, print_table_row, set_log_level, LOG_LEVEL

DEFAULT_OUTPUT = Path("export.csv")


def _sanitize_filename(name: str) -> str:
    """Convert a beschreibung into a safe filename (without extension)."""
    name = name.strip().replace(" ", "-")
    name = re.sub(r"[^\w\-]", "", name)
    return name or "export"


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="piano-analytics-export",
        description="Export Piano Analytics data via restricted API keys to CSV",
    )

    parser.add_argument("--init", action="store_true", help="Create an api_keys.json template in the current directory")
    parser.add_argument("--start", help="Start date in ISO format (YYYY-MM-DD)")
    parser.add_argument("--end", help="End date in ISO format (YYYY-MM-DD)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output CSV path (default: export.csv)")
    parser.add_argument("--dry-run", action="store_true", help="Render payloads without issuing HTTP requests")
    parser.add_argument("--timeout", type=int, default=120, help="Request timeout in seconds (default: 120)")
    parser.add_argument("--max-workers", type=int, default=5, help="Maximum concurrent API requests (default: 5)")
    parser.add_argument("--filter", help="Comma-separated Beschreibung labels to fetch (default: all)")

    config_group = parser.add_mutually_exclusive_group()
    config_group.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH, help="Path to api_keys.json (default: ./api_keys.json)")
    config_group.add_argument("--api-key", help="Single API key for quick queries (no config file needed)")

    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument("--quiet", action="store_true", help="Suppress non-error output")
    verbosity.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    if args.quiet:
        set_log_level(0)
    elif args.verbose:
        set_log_level(2)

    # --init: create template and exit
    if args.init:
        init_config(args.config)
        return

    # --start and --end are required for all non-init operations
    if not args.start or not args.end:
        parser.error("--start and --end are required")

    # Load credentials
    if args.api_key:
        credentials = build_inline_credentials(args.api_key)
    else:
        credentials = load_config(args.config)

    if args.filter:
        requested = {item.strip() for item in args.filter.split(",") if item.strip()}
        credentials = [entry for entry in credentials if entry.get("beschreibung") in requested]
        if not credentials:
            raise SystemExit("No matching entries found for --filter")

    start_date, end_date = args.start, args.end

    print_table_header()

    from piano_analytics_export.logging import LOG_LEVEL as current_level
    if current_level >= 2:
        print_table_row(
            "INFO",
            "-",
            start_date,
            end_date,
            f"Workers {args.max_workers}, Timeout {args.timeout}s",
            level=2,
        )

    results: list[tuple[str, pd.DataFrame]] = []  # (beschreibung, dataframe)
    failed_entries: list[str] = []

    if args.dry_run:
        for entry in credentials:
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
                continue
            try:
                payload = render_payload({"start": start_date, "end": end_date})
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Template render invalid JSON for {beschreibung}: {exc}")
            print_table_row("DRYRUN", beschreibung, start_date, end_date, "Payload rendered")
            print(json.dumps(payload, indent=2))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_workers) as executor:
            future_map = {
                executor.submit(
                    fetch_for_entry,
                    entry,
                    start_date,
                    end_date,
                    args.timeout,
                ): entry.get("beschreibung") or "unbekannt"
                for entry in credentials
            }
            for future in concurrent.futures.as_completed(future_map):
                beschreibung = future_map[future]
                df, rate_limited = future.result()
                if df is not None:
                    results.append((beschreibung, df))
                elif rate_limited:
                    failed_entries.append(beschreibung)

    if not results:
        if not args.dry_run and failed_entries:
            failed_list = ", ".join(sorted(set(failed_entries)))
            raise SystemExit(f"Abbruch: Die folgenden Eintraege konnten nicht abgerufen werden: {failed_list}")
        if not args.dry_run:
            print_table_row("INFO", "-", start_date, end_date, "No data fetched")
        return

    # Single entry: write to --output (default: export.csv)
    # Multiple entries: one file per beschreibung in --output's parent directory
    output_dir = args.output.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    if len(results) == 1:
        beschreibung, df = results[0]
        df.to_csv(args.output, index=False)
        print_table_row("WRITE", beschreibung, start_date, end_date, f"Wrote {len(df)} rows to {args.output}")
    else:
        for beschreibung, df in results:
            filename = _sanitize_filename(beschreibung) + ".csv"
            filepath = output_dir / filename
            df.to_csv(filepath, index=False)
            print_table_row("WRITE", beschreibung, start_date, end_date, f"Wrote {len(df)} rows to {filepath}")

    if failed_entries:
        failed_list = ", ".join(sorted(set(failed_entries)))
        raise SystemExit(f"Abbruch: Die folgenden Eintraege konnten nicht abgerufen werden: {failed_list}")


if __name__ == "__main__":
    main()
