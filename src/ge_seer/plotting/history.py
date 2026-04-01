import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from ..data import (
    read_prices_data,
    get_item_map,
    add_derived_price_columns,
    add_alchemy_columns,
    rebin_to_ohlcv,
    set_datetime_index,
)


def format_number(n: int) -> str:
    """
    Helper function to convert a large integer into a more human-readable string with
    suffixes, in the style of RuneScape item values. For example:
        1500 -> "1.5k", 2000000 -> "2M", 3500000000 -> "3.5B"

    Arguments:
    ----------
    n : int
        The number to convert.

    Returns:
    --------
    str
        The formatted string representation of the number.

    """
    abs_n = abs(n)
    sign = "-" if n < 0 else ""

    def fmt(value, suffix):
        # Remove trailing .0 if it’s an integer after division
        s = f"{value:.1f}".rstrip("0").rstrip(".")
        return f"{sign}{s}{suffix}"

    if abs_n >= 1_000_000_000 and abs_n % 100_000_000 == 0:
        return fmt(abs_n / 1_000_000_000, "B")
    elif abs_n >= 1_000_000 and abs_n % 100_000 == 0:
        return fmt(abs_n / 1_000_000, "M")
    elif abs_n >= 1_000 and abs_n % 100 == 0:
        return fmt(abs_n / 1_000, "k")
    else:
        return str(n)


def plot_trade_history(
    item_id,
    timestep,
    df=None,
    time_start=None,
    time_stop=None,
    filename=None,
    plot_alchemy=False,
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
    plot_alchemy : bool [False]
        Whether to plot and annotate low and high alchemy values.

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
    df = add_derived_price_columns(df)

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
    alch_color = "goldenrod"

    # plot price spreads
    ax = axs[0]
    ax.plot(
        dates,
        df["average_price"],
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
        # filter out rows where either price is NaN
        valid_mask = df["avgLowPrice"].notna() & df["avgHighPrice"].notna()
        valid_dates = [dates[i] for i in range(len(dates)) if valid_mask.iloc[i]]
        valid_prices = df.loc[valid_mask, ["avgLowPrice", "avgHighPrice"]]
        if len(valid_dates) > 0:
            ax.plot(
                [valid_dates, valid_dates],
                valid_prices.T,
                color="grey",
                zorder=8,
                linewidth=1,
            )

    # use log scale for better visualizing large price swings
    if df["avgHighPrice"].max() / df["avgLowPrice"].min() >= 10:
        ax.set_yscale("log")

    # get alchemy values for plotting
    if plot_alchemy:
        df = add_alchemy_columns(df, item_id=item_id, timestep=timestep)
        lowalch = list(df["lowalch"])[0]
        highalch = list(df["highalch"])[0]

        # plot low alch values
        ymin, ymax = ax.get_ylim()
        if not pd.isna(lowalch):
            if lowalch > ymax:
                ax.scatter(dates[0], ymax, marker="^", color=alch_color)
                ax.annotate(
                    f"LA:\n{format_number(lowalch)}",
                    xy=(dates[0], ymax),
                    xytext=(-4, -4),
                    textcoords="offset points",
                    horizontalalignment="right",
                    verticalalignment="center",
                    fontsize=7,
                    color=alch_color,
                )
            elif lowalch < ymin:
                ax.scatter(dates[0], ymin, marker="v", color=alch_color)
                ax.annotate(
                    f"LA:\n{format_number(lowalch)}",
                    xy=(dates[0], ymin),
                    xytext=(-4, 4),
                    textcoords="offset points",
                    horizontalalignment="right",
                    verticalalignment="center",
                    fontsize=7,
                    color=alch_color,
                )
            else:
                ax.axhline(
                    lowalch,
                    color=alch_color,
                    linestyle="dashed",
                    linewidth=0.5,
                )
                ax.annotate(
                    f"LA:\n{format_number(lowalch)}",
                    xy=(dates[0], lowalch),
                    xytext=(-4, -4),
                    textcoords="offset points",
                    horizontalalignment="right",
                    verticalalignment="top",
                    fontsize=7,
                    color=alch_color,
                )

        # plot high alch values
        if not pd.isna(highalch):
            if highalch > ymax:
                ax.scatter(dates[-1], ymax, marker="^", color=alch_color)
                ax.annotate(
                    f"HA:\n{format_number(highalch)}",
                    xy=(dates[-1], ymax),
                    xytext=(4, -4),
                    textcoords="offset points",
                    horizontalalignment="left",
                    verticalalignment="center",
                    fontsize=7,
                    color=alch_color,
                )
            elif highalch < ymin:
                ax.scatter(dates[-1], ymin, marker="v", color=alch_color)
                ax.annotate(
                    f"HA:\n{format_number(highalch)}",
                    xy=(dates[-1], ymin),
                    xytext=(4, 4),
                    textcoords="offset points",
                    horizontalalignment="left",
                    verticalalignment="center",
                    fontsize=7,
                    color=alch_color,
                )
            else:
                ax.axhline(
                    highalch,
                    color=alch_color,
                    linestyle="dashed",
                    linewidth=0.5,
                )
                ax.annotate(
                    f"HA:\n{format_number(highalch)}",
                    xy=(dates[-1], highalch),
                    xytext=(4, 2),
                    textcoords="offset points",
                    horizontalalignment="left",
                    verticalalignment="bottom",
                    fontsize=7,
                    color=alch_color,
                )

        # plot approx high alch profit, after subtracting approx nature rune cost
        ymin, ymax = ax.get_ylim()
        ax.set_ylim(ymin, ymax)
        if not pd.isna(highalch):
            ax.plot(
                df["time"].apply(lambda ts: datetime.utcfromtimestamp(ts)),
                df["highalch_profit"],
                linestyle="solid",
                linewidth=1,
                color=alch_color,
                zorder=7,
            )
            ax.annotate(
                f"HA\nProfit",
                xy=(dates[0], list(df["highalch_profit"])[0]),
                xytext=(-3, 0),
                textcoords="offset points",
                horizontalalignment="right",
                verticalalignment="center",
                fontsize=7,
                color=alch_color,
            )

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
        df["total_volume"],
        marker=marker,
        linestyle="solid",
        linewidth=1.5,
        color=all_color,
    )

    # use log scale for better visualizing large volume swings
    if (
        df["total_volume"].max() / df[["lowPriceVolume", "highPriceVolume"]].min().min()
        >= 10
    ):
        ax.set_yscale("log")

    # plot total value exchanged
    ax = axs[2]
    ax.plot(
        dates,
        df["total_value"],
        marker=marker,
        linestyle="solid",
        zorder=9,
        color=all_color,
        linewidth=1.5,
    )
    ax.plot(
        dates,
        df["high_value"],
        marker=marker,
        linestyle=linestyle,
        zorder=8,
        color=buy_color,
        linewidth=1,
    )
    ax.plot(
        dates,
        df["low_value"],
        marker=marker,
        linestyle=linestyle,
        zorder=8,
        color=sell_color,
        linewidth=1,
    )

    # use log scale for better visualizing large swings in total value
    if df["total_value"].max() / df["total_value"].min() >= 10:
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
        fig.savefig(filename, dpi=300, bbox_inches="tight")

    return fig, axs


def plot_mplfinance(df, input_timestep=None, output_timestep=None, **kwargs):
    """
    Wrapper around mplfinance.plot for plotting OHLCV data or rebinned OSRS Wiki GE data

    Arguments:
    ----------
    df : pd.DataFrame
        Input DataFrame, required to be in OHLCV format, or be standard GE data to be
        rebinned into OHLCV format
    input_timestep : str [None]
        When df is not in OHLCV format, the native timestep of the input DataFrame
    output_timestep : str [None]
        When df is not in OHLCV format, the desired rebinned timestep, which must be
        greater than the input timestep
    trim_partial_start : bool [True]
        When df is not in OHLCV format, whether to drop rows in the first partial
        output_timestep window when rebinning.
    trim_partial_end : bool [True]
        When df is not in OHLCV format, whether to drop rows in the last partial
        output_timestep window when rebinning.
    **kwargs
        Any keyword arguments to pass to mplfinance.plot
    """
    import mplfinance as mpf

    # check if required columns are present
    required_cols = {"Open", "High", "Low", "Close", "Volume"}
    required_cols_lower = {col.lower() for col in required_cols}
    if required_cols.issubset(df.columns) or required_cols_lower.issubset(df.columns):
        mpf_df = df.copy()

    # create required columns otherwise
    else:
        if input_timestep is None or output_timestep is None:
            raise ValueError(
                "timestep arguments required when data is not already in OHLCV format"
            )
        mpf_df = rebin_to_ohlcv(
            df=df,
            input_timestep=input_timestep,
            output_timestep=output_timestep,
            inplace=False,
            trim_partial_start=trim_partial_start,
            trim_partial_end=trim_partial_end,
        )

    # mplfinance expects a datetime index
    if not isinstance(mpf_df.index, pd.DatetimeIndex):
        mpf_df = set_datetime_index(mpf_df, inplace=False, sort_index=True)
    mpf_df.index.name = "Date"

    # mplfinance expects capitalized OHLCV column names and int/float columns
    mpf_df.rename(columns={col.lower(): col for col in required_cols}, inplace=True)
    for col in required_cols:
        mpf_df[col] = mpf_df[col].astype(int)

    mpf.plot(mpf_df, **kwargs)
