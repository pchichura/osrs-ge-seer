#!/usr/bin/env python3
"""
CLI tool to plot OSRS Grand Exchange trade history for an item.

Usage:
    python scripts/plot_trade_history.py --item-id 1925 --timestep 24h
    python scripts/plot_trade_history.py --item-id 1925 --timestep 1h --time-start "2025-12-20 00:00:00 UTC"
    python scripts/plot_trade_history.py --item-id 1925 --output prices.png
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import matplotlib.pyplot as plt
from ge_seer.plotting.history import plot_trade_history


def parse_args():
    parser = argparse.ArgumentParser(
        description="Plot OSRS GE trade history for a single item."
    )
    parser.add_argument(
        "--itemid",
        type=str,
        required=True,
        help="Item ID to plot (e.g., 1925).",
    )
    parser.add_argument(
        "--timestep",
        type=str,
        default="24h",
        choices=["5m", "1h", "6h", "24h"],
        help="Time interval aggregation (default: 24h).",
    )
    parser.add_argument(
        "--time-start",
        type=str,
        nargs="+",
        default=None,
        help="Start time as 'YYYY-MM-DD HH:MM:SS UTC' or timestamp.",
    )
    parser.add_argument(
        "--time-stop",
        type=str,
        nargs="+",
        default=None,
        help="End time as 'YYYY-MM-DD HH:MM:SS UTC' or timestamp (optional).",
    )
    parser.add_argument(
        "--alchemy",
        action="store_true",
        help="Overlay low and high alchemy values on the plot.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="If provided, saves the plot to this filename instead of displaying it.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # convert multi-token args back to strings
    time_start = " ".join(args.time_start) if args.time_start else None
    time_stop = " ".join(args.time_stop) if args.time_stop else None

    # generate plot
    fig, axs = plot_trade_history(
        item_id=args.itemid,
        timestep=args.timestep,
        time_start=time_start,
        time_stop=time_stop,
        filename=args.output,
        plot_alchemy=args.alchemy,
    )

    # display or save the plot
    if args.output:
        print(f"Plot saved to {args.output}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
