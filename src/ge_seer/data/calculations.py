import numpy as np
import pandas as pd


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
    required_cols = {
        "avgHighPrice",
        "highPriceVolume",
        "avgLowPrice",
        "lowPriceVolume",
    }
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
