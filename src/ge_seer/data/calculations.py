import numpy as np
import pandas as pd
from .file_io import read_prices_data
from .query import get_static_values
from .time_utils import (
    timestamp_to_datetime,
    normalize_timestep_rule,
    timestep_to_timedelta,
)


def add_derived_price_columns(df, inplace=False):
    """
    Add commonly used derived columns to a typical GE prices DataFrame, particularly:
    total_volume, low_value, high_value, total_value, and average_price

    Arguments:
    ----------
    df : pd.DataFrame
        DataFrame containing at least high/low price and volume columns.
    inplace : bool [False]
        If True, mutate and return the input DataFrame. If False, return a copy.

    Returns:
    --------
    pd.DataFrame
        DataFrame with derived columns appended.
    """
    # validate required columns
    required_cols = {"avgHighPrice", "highPriceVolume", "avgLowPrice", "lowPriceVolume"}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"DataFrame must contain columns: {required_cols}")

    # create a copy of the DataFrame if not modifying in place
    prices_df = df if inplace else df.copy()

    # compute derived columns, handling nan values (no trades) appropriately
    prices_df["total_volume"] = (
        prices_df["highPriceVolume"] + prices_df["lowPriceVolume"]
    )
    prices_df["low_value"] = prices_df["lowPriceVolume"] * prices_df[
        "avgLowPrice"
    ].to_numpy(na_value=np.nan, dtype=float)
    prices_df["high_value"] = prices_df["highPriceVolume"] * prices_df[
        "avgHighPrice"
    ].to_numpy(na_value=np.nan, dtype=float)
    prices_df["total_value"] = np.nansum(
        [prices_df["high_value"], prices_df["low_value"]], axis=0
    )
    prices_df["average_price"] = (
        prices_df["total_value"] / prices_df["total_volume"]
    ).round()

    return prices_df


def set_datetime_index(df, inplace=False, sort_index=True):
    """
    Convert the "time" column (Unix timestamp) into a UTC datetime index "date".

    Arguments:
    ----------
    df : pd.DataFrame
        DataFrame containing a "time" column in Unix seconds.
    inplace : bool [False]
        If True, mutate and return the input DataFrame. If False, return a copy.
    sort_index : bool [True]
        If True, sort the DataFrame by the resulting datetime index.

    Returns:
    --------
    pd.DataFrame
        DataFrame with a UTC datetime index named "date".
    """
    # validate required column
    if "time" not in df.columns:
        raise ValueError("DataFrame must contain column: time")

    # create a copy of the DataFrame if not modifying in place
    prices_df = df if inplace else df.copy()

    # convert the "time" column to UTC datetime and set as index
    prices_df["date"] = timestamp_to_datetime(prices_df["time"], as_string=False)
    prices_df.set_index("date", inplace=True)
    if sort_index:
        prices_df.sort_index(inplace=True)

    return prices_df


def add_alchemy_columns(
    df,
    item_id,
    timestep,
    inplace=False,
):
    """
    Add columns related to alchemy spells to an item prices DataFrame.

    Added columns:
    - nature_rune_price: approximate cost of a nature rune on the GE
    - lowalch: static low alchemy value for the item
    - highalch: static high alchemy value for the item
    - lowalch_profit: approximate profit from low alching (after nature rune cost)
    - highalch_profit: approximate profit from high alching (after nature rune cost)

    Arguments:
    ----------
    df : pd.DataFrame
        DataFrame containing at least time.
    item_id : int or str
        Item ID used to fetch static low/high alchemy values.
    timestep : str
        Saved timestep of df. Used to fetch matching nature rune prices.
    inplace : bool [False]
        If True, mutate and return the input DataFrame. If False, return a copy.

    Returns:
    --------
    pd.DataFrame
        DataFrame with alchemy columns appended.
    """

    # validate required column
    required_cols = {"time"}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"DataFrame must contain columns: {required_cols}")

    # create a copy of the DataFrame if not modifying in place
    prices_df = df if inplace else df.copy()

    # static alchemy values are constant for a given item
    static_values = get_static_values()
    item_values = static_values.get(str(item_id), {})
    lowalch = item_values.get("lowalch")
    highalch = item_values.get("highalch")
    prices_df["lowalch"] = lowalch
    prices_df["highalch"] = highalch

    # approximate nature rune cost from weighted average traded price
    prices_df["nature_rune_price"] = np.nan
    if not prices_df.empty:
        df_nature = read_prices_data(
            item_id=561, # nature rune item ID
            timestep=timestep,
            time_start=prices_df["time"].min(),
            time_stop=prices_df["time"].max(),
        )
        if not df_nature.empty:
            nature_total_volume = (
                df_nature["lowPriceVolume"] + df_nature["highPriceVolume"]
            )
            nature_rune_price = (
                df_nature["lowPriceVolume"] * df_nature["avgLowPrice"]
                + df_nature["highPriceVolume"] * df_nature["avgHighPrice"]
            ) / nature_total_volume
            nature_rune_price = nature_rune_price.round()

            # merge the nature rune price into the main df
            prices_df = prices_df.merge(
                df_nature[["time"]].assign(nature_rune_price=nature_rune_price),
                on="time",
                how="left",
                suffixes=("", "_new"),
            )
            prices_df["nature_rune_price"] = prices_df[
                "nature_rune_price_new"
            ].combine_first(prices_df["nature_rune_price"])
            prices_df.drop(columns=["nature_rune_price_new"], inplace=True)

    # compute alchemy profits after nature rune cost
    prices_df["nature_rune_price"] = prices_df["nature_rune_price"]
    prices_df["lowalch_profit"] = (
        prices_df["lowalch"] - prices_df["nature_rune_price"]
    )
    prices_df["highalch_profit"] = (
        prices_df["highalch"] - prices_df["nature_rune_price"]
    )

    return prices_df


def rebin_to_ohlcv(
    df,
    input_timestep,
    output_timestep,
    inplace=False,
    sort_index=True,
    trim_partial_start=True,
    trim_partial_end=True,
):
    """
    Re-bin GE averaged data into general OHLCV columns with "date" datetime index and
    "open", "high``, "low", "close", "volume" columns over the rebinned timestep.

    Arguments:
    ----------
    df : pd.DataFrame
        DataFrame with time, avg high/low price, and high/low volume columns.
    input_timestep : str
        Native timestep of the input DataFrame (e.g. "5m", "1h").
    output_timestep : str
        Desired rebinned timestep (must be greater than or equal to input timestep).
    inplace : bool [False]
        If True, reuse input data where possible. If False, operate on a copy.
    sort_index : bool [True]
        If True, sort by datetime index before rebinning.
    trim_partial_start : bool [True]
        If True, drop rows in the first partial output_timestep window by trimming the
        start timestamp up to the next output_timestep boundary.
    trim_partial_end : bool [True]
        If True, drop rows in the last partial output_timestep window by trimming the
        end timestamp down to the previous output_timestep boundary.

    Returns:
    --------
    pd.DataFrame
        Datetime-indexed OHLCV DataFrame.
    """
    # validate required columns
    required_cols = {
        "time", "avgHighPrice", "highPriceVolume", "avgLowPrice", "lowPriceVolume"
    }
    if not required_cols.issubset(df.columns):
        raise ValueError(f"DataFrame must contain columns: {required_cols}")

    # validate rebinned timestep is greater than input timestep
    input_delta = timestep_to_timedelta(input_timestep)
    output_delta = timestep_to_timedelta(output_timestep)
    if output_delta <= input_delta:
        raise ValueError("output_timestep must be greater than input_timestep")

    # add derived columns and set datetime index for rebinning
    prices_df = df if inplace else df.copy()
    prices_df = add_derived_price_columns(prices_df, inplace=True)
    prices_df = set_datetime_index(prices_df, inplace=True, sort_index=sort_index)

    # compute lowest and highest prices for OHLCV aggregation
    prices_df["low_price"] = prices_df[["avgLowPrice", "avgHighPrice"]].min(axis=1)
    prices_df["high_price"] = prices_df[["avgLowPrice", "avgHighPrice"]].max(axis=1)

    # optionally trim partial boundary windows before resampling
    if (trim_partial_start or trim_partial_end) and not prices_df.empty:
        resample_rule = normalize_timestep_rule(output_timestep)
        index_mask = pd.Series(True, index=prices_df.index)
        
        if trim_partial_start:
            first_ts = prices_df.index.min()
            start_boundary = first_ts.ceil(resample_rule)
            index_mask &= prices_df.index >= start_boundary

        if trim_partial_end:
            last_ts = prices_df.index.max()
            end_boundary = last_ts.floor(resample_rule)
            index_mask &= prices_df.index < end_boundary

        prices_df = prices_df[index_mask]

    # rebin to OHLCV using pandas resample
    resample_rule = normalize_timestep_rule(output_timestep)
    ohlcv_df = prices_df.resample(resample_rule).agg(
        {
            "average_price": ["first", "last"],
            "low_price": "min",
            "high_price": "max",
            "total_volume": "sum",
        }
    )

    # flatten multi-level columns and rename to standard OHLCV names
    ohlcv_df.columns = ["open", "close", "low", "high", "volume"]
    ohlcv_df = ohlcv_df[["open", "high", "low", "close", "volume"]]
    ohlcv_df = ohlcv_df.dropna(subset=["open", "high", "low", "close"])
    # XXX check if we should be dropping na columns

    return ohlcv_df
