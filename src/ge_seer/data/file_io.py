from pathlib import Path
import pandas as pd
import duckdb
from ..config.manager import load_config
from .time_utils import standardize_time_input


def _empty_prices_df():
    """Helper function to return an empty prices DataFrame with the expected columns."""
    return pd.DataFrame(
        columns=[
            "time",
            "avgHighPrice",
            "highPriceVolume",
            "avgLowPrice",
            "lowPriceVolume",
        ]
    )


def read_prices_data(item_id, timestep="24h", time_start=None, time_stop=None):
    """
    Read saved OSRS GE price data from parquet files using DuckDB.

    Arguments:
    ----------
    item_id : int or str
        Item ID for the item to read price data for.
    timestep : str ["24h"]
        The saved timestep partition to read. Options: "5m", "1h", "6h", "24h".
    time_start : int or str [None]
        Optional inclusive lower bound for timestamps. If str, expected format is
        "YYYY-MM-DD HH:MM:SS UTC".
    time_stop : int or str [None]
        Optional inclusive upper bound for timestamps. If str, expected format is
        "YYYY-MM-DD HH:MM:SS UTC".

    Returns:
    --------
    pd.DataFrame
        Combined data across matching files for that item. Columns include:
        "time", "avgHighPrice", "highPriceVolume", "avgLowPrice", "lowPriceVolume"
    """
    # validate timestep choice
    valid_timesteps = {"5m", "1h", "6h", "24h"}
    if timestep not in valid_timesteps:
        raise ValueError(
            f"Invalid timestep: {timestep}. Must be one of {sorted(valid_timesteps)}"
        )

    # standardize the requested time range inputs
    time_start = standardize_time_input(time_start)
    time_stop = standardize_time_input(time_stop)
    if time_start is not None and time_stop is not None and time_start > time_stop:
        raise ValueError(
            f"time_start ({time_start}) must be <= time_stop ({time_stop})."
        )

    # build optional time filters
    time_clauses = ""
    if time_start is not None:
        time_clauses += f" AND time >= {time_start}"
    if time_stop is not None:
        time_clauses += f" AND time <= {time_stop}"

    # read config file for data directory
    config = load_config()
    partition_root = (
        Path(config["data_dir"]) / "prices_raw" / "instance" / f"timestep={timestep}"
    )

    # ensure at least one parquet shard exists for this timestep partition
    if not partition_root.exists():
        return _empty_prices_df()
    if not any(partition_root.glob("time=*/data.parquet")):
        return _empty_prices_df()

    # query the partitioned parquet dataset directly with duckdb
    query = f"""
    SELECT time, avgHighPrice, highPriceVolume, avgLowPrice, lowPriceVolume
    FROM read_parquet('{str(partition_root)}')
    WHERE itemID = {item_id}
        AND timestep = '{timestep}'{time_clauses}
    ORDER BY time
    """
    df = duckdb.query(query).to_df()

    return df
