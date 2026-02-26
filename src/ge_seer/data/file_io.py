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


def read_prices_data(
    item_id, timestep="24h", time_start=None, time_stop=None, source="all"
):
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
    source : str ["all"]
        Data source(s) to read from. Options:
        - "all": merge instance and timeseries data (instance preferred on overlap)
        - "instance": read only instance data
        - "timeseries": read only timeseries data

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

    # validate source choice
    valid_sources = {"all", "instance", "timeseries"}
    if source not in valid_sources:
        raise ValueError(
            f"Invalid source: {source}. Must be one of {sorted(valid_sources)}"
        )

    # standardize the requested time range inputs
    time_start = standardize_time_input(time_start)
    time_stop = standardize_time_input(time_stop)
    if time_start is not None and time_stop is not None and time_start > time_stop:
        raise ValueError(
            f"time_start ({time_start}) must be <= time_stop ({time_stop})."
        )

    # sanitize item_id input
    item_id = int(item_id)

    # build optional time filters
    time_clauses = ""
    if time_start is not None:
        time_clauses += f" AND time >= {time_start}"
    if time_stop is not None:
        time_clauses += f" AND time <= {time_stop}"

    # read config file for data directory
    config = load_config()
    instance_root = (
        Path(config["data_dir"]) / "prices_raw" / "instance" / f"timestep={timestep}"
    )
    timeseries_root = (
        Path(config["data_dir"])
        / "prices_raw"
        / "timeseries"
        / f"timestep={timestep}"
        / f"itemID={item_id}"
    )

    # ensure at least one parquet shard exists in either data source
    has_instance_data = (
        source in {"all", "instance"}
        and instance_root.exists()
        and any(instance_root.glob("time=*/data.parquet"))
    )
    has_timeseries_data = (
        source in {"all", "timeseries"}
        and timeseries_root.exists()
        and any(timeseries_root.glob("*.parquet"))
    )
    if source == "instance" and not has_instance_data:
        return _empty_prices_df()
    if source == "timeseries" and not has_timeseries_data:
        return _empty_prices_df()
    if source == "all" and not has_instance_data and not has_timeseries_data:
        return _empty_prices_df()

    # build the DuckDB queries for reading from both sources
    source_queries = []
    if has_instance_data:
        source_queries.append(
            f"""
            SELECT
                time,
                avgHighPrice,
                highPriceVolume,
                avgLowPrice,
                lowPriceVolume,
                1 AS source_priority
            FROM read_parquet('{str(instance_root)}')
            WHERE itemID = {item_id}
                AND timestep = '{timestep}'{time_clauses}
            """
        )
    if has_timeseries_data:
        source_queries.append(
            f"""
            SELECT
                time,
                avgHighPrice,
                highPriceVolume,
                avgLowPrice,
                lowPriceVolume,
                2 AS source_priority
            FROM read_parquet('{str(timeseries_root)}')
            WHERE 1 = 1{time_clauses}
            """
        )

    # merge both sources and deduplicate by time, preferring instance when overlapping
    union_query = "\nUNION ALL\n".join(source_queries)
    query = f"""
    WITH merged AS (
        {union_query}
    )
    SELECT time, avgHighPrice, highPriceVolume, avgLowPrice, lowPriceVolume
    FROM (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY time
                ORDER BY source_priority
            ) AS row_num
        FROM merged
    )
    WHERE row_num = 1
    ORDER BY time
    """
    df = duckdb.query(query).to_df()

    return df
