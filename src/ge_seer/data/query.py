import requests, json, time
from pathlib import Path
from functools import wraps
from glob import glob
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from tqdm import tqdm
from ..config.manager import load_config
from .time_utils import datetime_to_timestamp, get_current_timestamp


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
def query_prices_instance(query_time, timestep="24h", store=True):
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
    query_time : int or str
        The Unix timestamp (in UTC) for which to query price data, or a human-readable
        datetime string in the format "YYYY-MM-DD HH:MM:SS UTC" to be converted to a
        Unix timestamp. The timestamp must be an integer multiple of the timestep.
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

    # convert query_time to unix timestamp if it's a string
    if isinstance(query_time, str):
        query_time = datetime_to_timestamp(query_time)
    query_time = int(query_time)  # ensure it's an integer

    # check that the timestamp is an integer multiple of the timestep
    timestep_seconds = {"5m": 300, "1h": 3600, "6h": 21600, "24h": 86400}
    if query_time % timestep_seconds[timestep] != 0:
        raise ValueError(
            f"Time must be an integer multiple of the timestep ({timestep})."
        )

    # query the price data for the specified time and timestep
    response = requests.get(
        f"https://prices.runescape.wiki/api/v1/osrs/{timestep}?timestamp={query_time}",
        headers=headers,
    )
    response.raise_for_status()  # raise an error for bad responses

    # convert the response to a DataFrame
    df = pd.DataFrame(response.json()["data"]).T
    df["itemID"] = df.index
    df["timestep"] = timestep
    df["time"] = query_time
    df = df.convert_dtypes()

    # store the data if requested
    # path: data_dir/prices_raw/instance/timestep={timestep}/time={time}/data.parquet
    if store:
        partition_dir = (
            data_dir
            / "prices_raw"
            / "instance"
            / f"timestep={timestep}"
            / f"time={query_time}"
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


def query_prices_range(time_start=None, time_stop=None, timestep="24h"):
    """
    Wrapper for query_prices_instance to batch query and store price data for all valid
    time instances within a range, inclusively. Data is automatically stored to disk in
    the directory specified during setup. Query is rate-limited to max 1 per second.

    Arguments:
    ----------
    time_start : int or str [None]
        The Unix timestamp (in UTC) for the time range start, inclusively. If a str, it
        should be formatted "YYYY-MM-DD HH:MM:SS UTC". Default: 30 steps before stop.
    time_stop : int or str [None]
        The Unix timestamp (in UTC) for the time range stop, inclusively. If a str, it
        should be formatted "YYYY-MM-DD HH:MM:SS UTC". Default: now.
    timestep : str ["24h"]
        The time interval for price averaging. Options: "5m", "1h", "6h", "24h"
    """
    # define timestep in seconds
    step_size = {"5m": 300, "1h": 3600, "6h": 21600, "24h": 86400}[timestep]

    # format start/stop times; defaults: stop = now, start = 30 timesteps before stop
    if time_stop is None:
        time_stop = get_current_timestamp()
    elif isinstance(time_stop, str):
        time_stop = datetime_to_timestamp(time_stop)
    time_stop = int(time_stop)
    if time_start is None:
        time_start = time_stop - (30 * step_size)  # 30 steps before stop
    elif isinstance(time_start, str):
        time_start = datetime_to_timestamp(time_start)
    time_start = int(time_start)
    if time_start > time_stop:
        raise ValueError(f"start ({time_start}) must be before stop ({time_stop}).")

    # find the nearest valid start and stop times within the range, inclusively
    if time_start % step_size != 0:
        time_start = time_start + (step_size - (time_start % step_size))
    if time_stop % step_size != 0:
        time_stop = time_stop - (time_stop % step_size)

    # validate that there is at least one valid timestamp in the range
    if time_start > time_stop:
        raise ValueError(
            f"No valid timestamps in the range after adjusting for timestep. "
            f"Nearest valid start: {time_start}, nearest valid stop: {time_stop}."
        )

    # load user configuration for data directory path
    config = load_config()
    data_dir = Path(config["data_dir"])

    # get all valid timestamps not yet queried and saved in the range
    all_timestamps = set(range(time_start, time_stop + 1, step_size))
    queried_files = glob(
        str(
            data_dir
            / "prices_raw"
            / "instance"
            / f"timestep={timestep}"
            / "time=*/data.parquet"
        )
    )
    queried_timestamps = set(
        [int(Path(file).parent.name.split("=")[1]) for file in queried_files]
    )
    timestamps_to_query = all_timestamps - queried_timestamps

    # Query and store data for each timestamp that needs to be queried
    for query_time in tqdm(
        timestamps_to_query, desc=f"Querying {timestep} prices", unit=" queries"
    ):
        query_prices_instance(query_time=query_time, timestep=timestep, store=True)
