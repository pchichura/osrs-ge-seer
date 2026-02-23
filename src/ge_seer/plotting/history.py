import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from ..data import read_prices_data, get_item_map


def plot_trade_history(
    item_id,
    timestep,
    df=None,
    time_start=None,
    time_stop=None,
    filename=None,
):
    """
    Plot OSRS GE trade history for a single item showing prices, volumes, and values.

    Arguments:
    ----------
    item_id : int or str []
        Item ID to plot.
    timestep : str []
        Time interval over which data was averaged. Options: "5m", "1h", "6h", "24h".
    df : pd.DataFrame [None]
        Pre-loaded DataFrame with columns: time, avgHighPrice, highPriceVolume,
        avgLowPrice, lowPriceVolume. If provided, time_start/time_stop are ignored.
    time_start : int or str [None]
        Optional start time for data range (inclusive) when reading data from disk.
    time_stop : int or str [None]
        Optional end time for data range (inclusive) when reading data from disk.
    filename : str [None]
        If provided, saves the figure to this path (e.g., "price_history.png").

    Returns:
    --------
    fig, axs : matplotlib.figure.Figure, np.ndarray of matplotlib.axes.Axes
        The generated figure object and array of axes.
    """
    # validate DataFrame if provided
    if df is not None:
        required_cols = {
            "time",
            "avgHighPrice",
            "highPriceVolume",
            "avgLowPrice",
            "lowPriceVolume",
        }
        if not required_cols.issubset(df.columns):
            raise ValueError(f"DataFrame must contain columns: {required_cols}")
        if df.empty:
            raise ValueError("DataFrame is empty")

    # otherwise read in data from disk
    if df is None:
        df = read_prices_data(
            item_id=item_id,
            timestep=timestep,
            time_start=time_start,
            time_stop=time_stop,
        )
        if df.empty:
            raise ValueError(
                f"No data found for item {item_id} with timestep {timestep}"
            )

    # set up plot
    fig, axs = plt.subplots(
        nrows=3, ncols=1, figsize=(12, 8), sharex=True, gridspec_kw={"hspace": 0.05}
    )

    # plot dates on x axis
    dates = [datetime.utcfromtimestamp(ts) for ts in df["time"]]

    # settings for few vs many time samples
    big_range = len(df) > 100
    marker = "none" if big_range else "."
    linestyle = "solid" if big_range else "dotted"

    # color scheme
    buy_color = "mediumorchid"
    sell_color = "forestgreen"
    all_color = "black"

    # calculate some derived quantities
    total_volume = df["highPriceVolume"] + df["lowPriceVolume"]
    low_value = df["lowPriceVolume"] * df["avgLowPrice"]
    high_value = df["highPriceVolume"] * df["avgHighPrice"]
    total_value = low_value + high_value
    all_average_price = (total_value / total_volume).round()

    # plot price spreads
    ax = axs[0]
    ax.plot(
        dates,
        all_average_price,
        marker=marker,
        linestyle="solid",
        linewidth=1.5,
        color=all_color,
        zorder=10,
        label="All",
    )
    ax.plot(
        dates,
        df["avgHighPrice"],
        marker=marker,
        linestyle=linestyle,
        linewidth=1,
        color=buy_color,
        zorder=9,
        label="Instant-Buy",
    )
    ax.plot(
        dates,
        df["avgLowPrice"],
        marker=marker,
        linestyle=linestyle,
        linewidth=1,
        color=sell_color,
        zorder=9,
        label="Instant-Sell",
    )
    ax.fill_between(
        x=dates,
        y1=df["avgLowPrice"],
        y2=df["avgHighPrice"],
        zorder=0,
        color="whitesmoke",
    )

    # vertical lines from low to high price
    if not big_range:
        ax.plot(
            [dates, dates],
            df[["avgLowPrice", "avgHighPrice"]].T,
            color="grey",
            zorder=8,
            linewidth=1,
        )

    # use log scale for better visualizing large price swings
    if df["avgHighPrice"].max() / df["avgLowPrice"].min() >= 10:
        ax.set_yscale("log")

    # plot item volume
    ax = axs[1]
    ax.plot(
        dates,
        df["highPriceVolume"],
        marker=marker,
        linestyle=linestyle,
        linewidth=1,
        color=buy_color,
    )
    ax.plot(
        dates,
        df["lowPriceVolume"],
        marker=marker,
        linestyle=linestyle,
        linewidth=1,
        color=sell_color,
    )
    ax.plot(
        dates,
        total_volume,
        marker=marker,
        linestyle="solid",
        linewidth=1.5,
        color=all_color,
    )

    # use log scale for better visualizing large volume swings
    if total_volume.max() / df[["lowPriceVolume", "highPriceVolume"]].min().min() >= 10:
        ax.set_yscale("log")

    # plot total value exchanged
    ax = axs[2]
    ax.plot(
        dates,
        total_value,
        marker=marker,
        linestyle="solid",
        zorder=9,
        color=all_color,
        linewidth=1.5,
    )
    ax.plot(
        dates,
        high_value,
        marker=marker,
        linestyle=linestyle,
        zorder=8,
        color=buy_color,
        linewidth=1,
    )
    ax.plot(
        dates,
        low_value,
        marker=marker,
        linestyle=linestyle,
        zorder=8,
        color=sell_color,
        linewidth=1,
    )

    # use log scale for better visualizing large swings in total value
    if total_value.max() / total_value.min() >= 10:
        ax.set_yscale("log")

    # legend at top of figure, based on axs[0] labels
    handles, labels = axs[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        title="Transaction Type",
        loc="lower right",
        ncol=3,
        frameon=True,
        bbox_to_anchor=(0.9, 0.88),
    )

    # add grid lines
    for ax in axs:
        ax.grid(alpha=0.6, linestyle="solid", linewidth=0.5, color="darkgrey", axis="y")
        ax.grid(
            alpha=0.6,
            linestyle="dotted",
            which="minor",
            color="gainsboro",
            linewidth=0.5,
            axis="y",
        )

    # plot title
    id2item = get_item_map()
    item_name = id2item.get(str(item_id), "Unknown Item")
    title = f"{item_name} (ID {item_id}): {timestep}-Averaged Trade History\n"
    axs[0].set_title(title, loc="left")

    # axes labels
    axs[0].set_ylabel("Average Price [gp]")
    axs[1].set_ylabel("Volume Traded [items]")
    axs[2].set_ylabel("Value Traded [gp]")
    axs[2].set_xlabel("Date")

    # pretty up the axis labels and tick marks
    for ax in axs:
        ax.tick_params(
            direction="in",
            axis="both",
            which="both",
            top=True,
            bottom=True,
            left=True,
            right=True,
        )
        ax.tick_params(which="minor", color="gray")

    # clearer date labels
    xaxis = axs[2].xaxis
    date_range = dates[-1] - dates[0]
    if date_range < timedelta(days=3):
        xaxis.set_major_locator(mdates.DayLocator(interval=1))
        xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        xaxis.set_minor_locator(mdates.HourLocator(byhour=[6, 12, 18]))
        xaxis.set_minor_formatter(mdates.DateFormatter("%H:00"))
    elif date_range < timedelta(days=7):
        xaxis.set_major_locator(mdates.DayLocator())
        xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        xaxis.set_minor_locator(mdates.HourLocator(byhour=[12]))
        xaxis.set_minor_formatter(mdates.DateFormatter("%H:00"))
    elif date_range < timedelta(days=14):
        xaxis.set_major_locator(mdates.DayLocator(interval=3))
        xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        xaxis.set_minor_locator(mdates.DayLocator(interval=1))
        xaxis.set_minor_formatter(mdates.DateFormatter("%d"))
    elif date_range < timedelta(days=28):
        xaxis.set_major_locator(mdates.DayLocator(interval=7))
        xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        xaxis.set_minor_locator(mdates.DayLocator(interval=1))
        xaxis.set_minor_formatter(mdates.DateFormatter("%d"))
    elif date_range < timedelta(days=28 * 3):
        xaxis.set_major_locator(mdates.DayLocator(interval=4 * 7))
        xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        xaxis.set_minor_locator(mdates.DayLocator(interval=1 * 7))
        xaxis.set_minor_formatter(mdates.DateFormatter("%m-%d"))
    elif date_range < timedelta(days=365):
        xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        xaxis.set_minor_locator(mdates.MonthLocator(interval=1))
        xaxis.set_minor_formatter(mdates.DateFormatter("%m"))
    else:
        xaxis.set_major_locator(mdates.YearLocator())
        xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        xaxis.set_minor_locator(mdates.MonthLocator(interval=3))
        xaxis.set_minor_formatter(mdates.DateFormatter("%m"))
    fig.autofmt_xdate(which="both", rotation=20)

    # save figure if filename provided
    if filename is not None:
        fig.savefig(filename, dpi=150, bbox_inches="tight")

    return fig, axs
