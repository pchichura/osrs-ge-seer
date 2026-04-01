from ge_seer import data, plotting
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.ticker import FuncFormatter
import mplfinance as mpf
import argparse

# ======================================================================================
# Color and theme configuration
# ======================================================================================


def get_alpha_hex(color, alpha):
    """Convert named color to RGBA hex string with embedded alpha channel."""
    return mcolors.to_hex(mcolors.to_rgba(color, alpha), keep_alpha=True)


# color palette for candlesticks and volume bars
COLORS = {
    "bg": "#1E1E1E",
    "grid": "grey",
    "axis_text": "lightgrey",
    "edge_up": "limegreen",
    "edge_down": "orangered",
    "face_alpha": 0.3,
}
COLORS["face_up"] = get_alpha_hex("lightgreen", COLORS["face_alpha"])
COLORS["face_down"] = get_alpha_hex("lightcoral", COLORS["face_alpha"])

# ======================================================================================
# Plotting function
# ======================================================================================


def plot_candlesticks(item_id, mav=(3,), output_file=None):
    """
    Create and display/save a candlestick chart with volume.

    Args:
        item_id: OSRS Grand Exchange item ID to plot
        mav: Tuple of moving average periods to apply
        output_file: Optional filename to save plot; if None, display instead
    """

    # query hourly price data, rebin to daily OHLCV, and estimate high alch profit
    df = data.query_prices_timeseries(item_id, timestep="1h", store=True)
    df = data.rebin_to_ohlcv(
        df,
        input_timestep="1h",
        output_timestep="24h",
        trim_partial_end=True,
        trim_partial_start=True,
    )
    df = data.add_alchemy_columns(df, item_id=item_id, timestep="24h")

    # create a new figure of two vertically stacked subplots
    fig, ax = plt.subplots(
        nrows=2,
        ncols=1,
        figsize=(7, 6),
        gridspec_kw={"height_ratios": [2.5, 1], "hspace": 0.07},
        sharex=True,
    )

    # set overall figure background and axis backgrounds, grid, and label colors
    fig.patch.set_facecolor(COLORS["bg"])
    for axis in ax:
        axis.set_facecolor(COLORS["bg"])
        axis.grid(color=COLORS["grid"], linestyle="dotted", zorder=0)
        axis.tick_params(colors=COLORS["axis_text"])
        for spine in axis.spines.values():
            spine.set_color(COLORS["grid"])

    # create custom mplfinance style with our color scheme
    market_colors = mpf.make_marketcolors(
        up=COLORS["face_up"],
        down=COLORS["face_down"],
        edge={"up": COLORS["edge_up"], "down": COLORS["edge_down"]},
        wick={"up": COLORS["edge_up"], "down": COLORS["edge_down"]},
        volume="inherit",
        alpha=COLORS["face_alpha"],
    )
    mpf_style = mpf.make_mpf_style(
        marketcolors=market_colors, mavcolors=plt.color_sequences["Set2"]
    )

    # plot candlesticks
    plotting.plot_mplfinance(df, ax=ax[0], type="candle", style=mpf_style)

    # plot moving averages with labels
    close_prices = df["close"]
    colors = plt.color_sequences["Set2"]
    for i, ma_period in enumerate(mav):
        ma = close_prices.rolling(window=ma_period).mean()
        ax[0].plot(
            df.index,
            ma,
            linestyle="solid",
            linewidth=1.7,
            color=colors[i % len(colors)],
            label=f"{ma_period}-Day Moving Avg",
            zorder=1,
        )

    # overlay estimated high alch profit without changing the existing y limits
    price_ymin, price_ymax = ax[0].get_ylim()
    if df["highalch_profit"].between(price_ymin, price_ymax).any():
        ax[0].plot(
            df.index,
            df["highalch_profit"],
            linestyle="solid",
            linewidth=1.7,
            color="goldenrod",
            zorder=1,
            label="High Alchemy Profit",
        )
        ax[0].set_ylim(price_ymin, price_ymax)

    # add all plotted lines to legend (moving averages + high alch profit)
    handles, labels = ax[0].get_legend_handles_labels()
    if handles:
        legend = fig.legend(
            handles,
            labels,
            loc="lower right",
            ncol=1,
            frameon=False,
            bbox_to_anchor=(0.91, 0.87),
            labelcolor=COLORS["axis_text"],
            fontsize=9,
        )

    # determine which candles are up (close >= open) to color volume bars accordingly
    is_up = (df["close"] >= df["open"]).values
    x_coords = list(range(len(df)))

    # build volume color arrays
    vol_face_colors = [COLORS["face_up"] if up else COLORS["face_down"] for up in is_up]
    vol_edge_colors = [COLORS["edge_up"] if up else COLORS["edge_down"] for up in is_up]

    # draw volume on second plot
    ax[1].bar(
        x_coords,
        df["volume"],
        color=vol_face_colors,
        edgecolor=vol_edge_colors,
        linewidth=1.5,
        width=0.97,  # Matches standard candlestick width
    )

    # number formatting for large y axis tick marks
    def format_volume(x, pos):
        """Convert large numbers to human-readable K/M/B"""
        if x >= 1e10:
            return f"{round(x * 1e-9):.0f}B"  # e.g., 30B
        if x >= 1e9:
            return f"{round(x * 1e-9, 2):.2f}B"  # e.g., 3.0B
        elif x >= 1e7:
            return f"{round(x * 1e-6):.0f}M"  # e.g., 30M
        elif x >= 1e6:
            return f"{round(x * 1e-6, 2):.2f}M"  # e.g., 3.0M
        elif x >= 1e4:
            return f"{round(x * 1e-3):.0f}K"  # e.g., 30K
        elif x >= 1e3:
            return f"{round(x * 1e-3, 2):.2f}K"  # e.g., 3.0K
        else:
            return f"{round(x):.0f}"

    # apply formatter to both price and volume axes for readable large numbers
    ax[0].yaxis.set_major_formatter(FuncFormatter(format_volume))
    ax[1].yaxis.set_major_formatter(FuncFormatter(format_volume))

    # set axis labels with consistent styling
    ax[0].set_ylabel("Price [gp]", color=COLORS["axis_text"], fontweight="bold")
    ax[1].set_ylabel("Volume", color=COLORS["axis_text"], fontweight="bold")
    ax[1].set_xlabel("Date", color=COLORS["axis_text"], fontweight="bold")

    # plot title
    id2item = data.get_item_map()
    item_name = id2item.get(str(item_id), "Unknown Item")
    title = f"{item_name} (ID {item_id}): Trade History\n"
    ax[0].set_title(
        title,
        loc="left",
        color=COLORS["axis_text"],
        fontweight="bold",
        y=0.93,
        va="bottom",
        fontsize=11,
    )

    # set volume axis limits with 10% headroom above max volume
    ax[1].set_ylim(0, df["volume"].max() * 1.1)

    # rotate x-axis date labels for better readability
    plt.setp(
        ax[1].xaxis.get_majorticklabels(),
        rotation=30,
        ha="right",
        rotation_mode="anchor",
    )

    # display or save the final plot
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches="tight", facecolor=COLORS["bg"])
        print(f"Plot saved to {output_file}")
    else:
        plt.show()


# ======================================================================================
# CLI entry point
# ======================================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Plot OSRS Grand Exchange candlestick chart with volume",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("item_id", type=int, help="OSRS Grand Exchange item ID to plot")
    parser.add_argument(
        "--mav",
        type=int,
        nargs="+",
        default=[3],
        help="Moving average periods (default: 3)",
    )
    parser.add_argument(
        "--save",
        type=str,
        default=None,
        help="File path to save plot (if not provided, displays plot instead)",
    )

    args = parser.parse_args()

    # generate plot
    plot_candlesticks(args.item_id, mav=tuple(args.mav), output_file=args.save)
