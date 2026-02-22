import requests, json, time
from pathlib import Path
from functools import wraps
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from ..config.manager import load_config
from .time_utils import datetime_to_timestamp


def rate_limit(min_interval=1.0):
    """
    Decorator that enforces a minimum time interval between function calls.
    
    Arguments:
    ----------
    min_interval : float [1.0]
        Minimum time in seconds between successive calls to the decorated function. If a
        call is made too soon, the decorator sleeps to enforce the interval.
    """
    def decorator(func):
        func._last_call_time = 0
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - func._last_call_time
            if elapsed < min_interval:
                sleep_time = min_interval - elapsed
                time.sleep(sleep_time)

            func._last_call_time = time.time()
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def get_item_map(force_refresh=False):
    """
    Retrieves the mapping of item IDs to human-readable names from the OSRS Wiki API.
    The first time this function is called, it will fetch the data using the API and
    create a local file to store the mapping. Subsequent calls will load from this file.

    Arguments:
    ----------
    force_refresh : bool [False]
        If True, forces a refresh of the item mapping from the API, even if a local
        file already exists.

    Returns:
    --------
    item_map : dict
        A dictionary mapping item IDs (str of integer) to item names (str).
    """
    # load user configuration for user-agent for API requests
    config = load_config()
    data_dir = config["data_dir"]
    headers = {"User-Agent": config["user_agent"]}

    # fetch the item mapping if the file doesn't exist or if force_refresh is True
    item_map_path = Path(data_dir) / "item_map.json"
    if force_refresh or not item_map_path.exists():
        response = requests.get(
            "https://prices.runescape.wiki/api/v1/osrs/mapping",
            headers=headers,
        )
        response.raise_for_status()  # raise an error for bad responses

        # save the mapping
        item_map = {item["id"]: item["name"] for item in response.json()}
        with open(item_map_path, "w") as f:
            json.dump(item_map, f, indent=4)

    # return the mapping from the file
    with open(item_map_path, "r") as f:
        item_map = json.load(f)
    return item_map


@rate_limit(min_interval=1.0)
def query_prices_instance(time_unix=None, time_str=None, timestep="24h", store=True):
    """
    Fetch price data from the OSRS Wiki GE API for all items at some instant in time.
    Data consists of the high and low prices each item averaged over the specified
    timestep, as well as the volume traded during that period.
    
    NOTE: This function is rate-limited to max 1 call per second (enforced by decorator)
    according to OSRS Wiki guidelines. If called more frequently, it will automatically
    sleep to enforce the constraint.

    For more info: https://oldschool.runescape.wiki/w/RuneScape:Real-time_Prices

    Arguments:
    ----------
    time_unix : int []
        The Unix timestamp (in UTC) for which to query price data. Must provide either
        time_unix or time_str, but not both. Time must be an integer multiple of the
        timestep.
    time_str : str []
        The human-readable datetime string (in UTC) for which to query price data, in
        the format "YYYY-MM-DD HH:MM:SS UTC". May provide instead of time_unix.
    timestep : str ["24h"]
        The time interval for price averaging. Options: "5m", "1h", "6h", "24h"
    store : bool [True]
        If True, stores the queried data as a parquet file in the user's data directory,
        organized by timestep and time.

    Returns:
    --------
    pd.DataFrame
        A DataFrame containing the price data for all items at the specified time, with
        columns:
            "itemID" : str of integer item ID
            "avgHighPrice" : int, volume-weighted average of instant-buy transactions
            "highPriceVolume" : int, volume of instant-buy transactions
            "avgLowPrice" : int, volume-weighted average of instant-sell transactions
            "lowPriceVolume" : int, volume of instant-sell transactions
    """
    # load user configuration for user-agent for API requests
    config = load_config()
    headers = {"User-Agent": config["user_agent"]}
    data_dir = Path(config["data_dir"])

    # determine the timestamp to query based on the provided arguments
    if time_unix is None and time_str is None:
        raise ValueError("Must provide either time_unix or time_str.")
    if time_unix is not None and time_str is not None:
        raise ValueError("Provide either time_unix or time_str, but not both.")
    if time_unix is None:
        time_unix = datetime_to_timestamp(time_str)
    time_unix = int(time_unix)  # ensure it's an integer

    # check that the timestamp is an integer multiple of the timestep
    timestep_seconds = {"5m": 300, "1h": 3600, "6h": 21600, "24h": 86400}
    if time_unix % timestep_seconds[timestep] != 0:
        raise ValueError(
            f"Time must be an integer multiple of the timestep ({timestep})."
        )

    # query the price data for the specified time and timestep
    response = requests.get(
        f"https://prices.runescape.wiki/api/v1/osrs/{timestep}?timestamp={time_unix}",
        headers=headers,
    )
    response.raise_for_status()  # raise an error for bad responses

    # convert the response to a DataFrame
    df = pd.DataFrame(response.json()["data"]).T
    df["itemID"] = df.index
    df["timestep"] = timestep
    df["time"] = time_unix
    df = df.convert_dtypes()

    # store the data if requested
    # path: data_dir/prices_raw/instance/timestep={timestep}/time={time}/data.parquet
    if store:
        partition_dir = (
            data_dir
            / "prices_raw"
            / "instance"
            / f"timestep={timestep}"
            / f"time={time_unix}"
        )
        partition_dir.mkdir(parents=True, exist_ok=True)

        # write to a single fixed-name file, overwrites if it already exists
        table = pa.Table.from_pandas(df)
        output_file = partition_dir / "data.parquet"
        pq.write_table(table, output_file)

    # return the DataFrame
    return df[
        ["itemID", "avgHighPrice", "highPriceVolume", "avgLowPrice", "lowPriceVolume"]
    ]
