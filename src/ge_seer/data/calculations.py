import numpy as np
import pandas as pd
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


def rebin_to_ohlcv(df, input_timestep, output_timestep, inplace=False, sort_index=True):
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
