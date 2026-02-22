#!/usr/bin/env python3
"""
Command-line interface for batch querying OSRS GE price data.

This script allows users to query and store price data for a range of timestamps
directly from the terminal, with progress tracking.
"""

import argparse
import sys
from pathlib import Path

# add parent directory to path to import ge_seer package
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ge_seer.data.query import query_prices_range


def main():
    """Parse arguments and execute batch price query."""
    parser = argparse.ArgumentParser(
        description="Batch query and store price data for a range of timestamps.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Query last 30 days at 24h intervals (default)
  python scripts/query_prices.py

  # Query specific timerange using datetime strings
  python scripts/query_prices.py --start "2025-01-01 00:00:00 UTC" --stop "2025-02-01 00:00:00 UTC"

  # Query specific timerange using Unix timestamps
  python scripts/query_prices.py --start 1761004800 --stop 1761608800
        """,
    )

    parser.add_argument(
        "--start",
        nargs="+",
        default=None,
        help=(
            "Start timestamp for the query range (inclusive). Can be a datetime string "
            '(format: "YYYY-MM-DD HH:MM:SS UTC") or a Unix timestamp (int). '
            "Default: 30 time steps before stop."
        ),
        metavar="TIME",
    )

    parser.add_argument(
        "--stop",
        nargs="+",
        default=None,
        help=(
            "End timestamp for the query range (inclusive). Can be a datetime string "
            '(format: "YYYY-MM-DD HH:MM:SS UTC") or a Unix timestamp (int). '
            "Default: now."
        ),
        metavar="TIME",
    )

    parser.add_argument(
        "--timestep",
        type=str,
        default="24h",
        choices=["5m", "1h", "6h", "24h"],
        help="Time interval for averaging. Default: 24h. Options: 5m, 1h, 6h, 24h.",
    )

    args = parser.parse_args()

    # reconstruct user-error string start/stop args, for example:
    # "2025-01-01 00:00:00 UTC" is the expected input, with quotes, but
    # 2025-01-01 00:00:00 UTC is parsed as ["2025-01-01", "00:00:00", "UTC"]
    time_start = " ".join(args.start) if args.start is not None else None
    time_stop = " ".join(args.stop) if args.stop is not None else None

    # try to convert to int if the string looks like a unix timestamp
    if time_start is not None and time_start.isdigit():
        time_start = int(time_start)
    if time_stop is not None and time_stop.isdigit():
        time_stop = int(time_stop)

    # call the batch query function
    try:
        query_prices_range(
            time_start=time_start, time_stop=time_stop, timestep=args.timestep
        )
        print("\nPrice data query completed successfully!")
    except Exception as e:
        print(f"\nError occurred during query: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
