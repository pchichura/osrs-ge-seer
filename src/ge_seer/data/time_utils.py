from datetime import datetime, timezone
import pandas as pd


def get_current_timestamp():
    """
    Returns the current Unix timestamp in UTC.
    """
    return int(datetime.now(timezone.utc).timestamp())


def timestamp_to_datetime(time, as_string=True):
    """
    Converts Unix timestamp values to UTC datetimes or UTC-formatted strings.

    Arguments:
    ----------
    time : int, float, pd.Series, pd.Index, list, tuple
        Unix timestamp value(s) in seconds.
    as_string : bool [True]
        Returns UTC-formatted string values if True, otherwise returns timezone-aware
        datetime values.

    Returns:
    --------
    str, datetime, or pd.Series
        Converted datetime representation.
    """
    format_str = "%Y-%m-%d %H:%M:%S UTC"

    # vectorized conversion for pandas objects
    if isinstance(time, (pd.Series, pd.Index, list, tuple)):
        converted = pd.to_datetime(time, unit="s", utc=True)
        if as_string:
            return converted.strftime(format_str)
        return converted

    # scalar conversion
    converted = datetime.fromtimestamp(time, timezone.utc)
    if as_string:
        return converted.strftime(format_str)
    return converted


def datetime_to_timestamp(time):
    """
    Converts datetime value(s) to Unix timestamp(s) in UTC.

    Arguments:
    ----------
    time : str, datetime, pd.Timestamp, pd.Series, pd.Index, list, tuple
        Datetime value(s) to convert. Naive datetime inputs are treated as UTC.

    Returns:
    --------
    int or pd.Series
        Corresponding Unix timestamp value(s) in seconds.
    """
    # vectorized conversion for pandas/list-like objects
    if isinstance(time, (pd.Series, pd.Index, list, tuple)):
        converted = pd.to_datetime(time, utc=True)
        return converted.astype("int64") // 10**9

    # scalar conversion
    if isinstance(time, str):
        converted = pd.to_datetime(time, utc=True)
    elif isinstance(time, (datetime, pd.Timestamp)):
        converted = pd.Timestamp(time)
        if converted.tzinfo is None:
            converted = converted.tz_localize("UTC")
        else:
            converted = converted.tz_convert("UTC")
    else:
        raise TypeError(
            "time must be str, datetime-like, or a pandas/list-like collection"
        )

    return int(converted.timestamp())


def normalize_timestep_rule(timestep):
    """
    Normalize timestep strings into pandas-compatible resample rules.

    Arguments:
    ----------
    timestep : str
        Timestep string to normalize: "5m", "1h", "6h", "24h"

    Returns:
    --------
    str
        Normalized pandas resample rule: "5min", "1h", "6h", "24h"
    """
    if not isinstance(timestep, str) or timestep.strip() == "":
        raise ValueError("timestep must be a non-empty string")

    # convert to pandas-compatible format
    ts = timestep.strip().lower()
    if ts.endswith("m"):
        return f"{int(ts[:-1])}min"
    if ts.endswith("h"):
        return f"{int(ts[:-1])}h"
    return ts


def timestep_to_timedelta(timestep):
    """
    Convert a timestep string to pandas Timedelta for comparisons.

    Arguments:
    ----------
    timestep : str
        Timestep string to convert: "5m", "1h", "6h", "24h"
    
    Returns:
    --------
    pd.Timedelta
        Corresponding pandas Timedelta object.
    """
    rule = normalize_timestep_rule(timestep)
    try:
        return pd.to_timedelta(rule)
    except ValueError as exc:
        raise ValueError(f"Unable to parse timestep: {timestep}") from exc


def standardize_time_input(time):
    """
    Standardizes time input to a Unix timestamp. Accepts either an integer timestamp
    or a human-readable datetime string in the format "YYYY-MM-DD HH:MM:SS UTC".

    Arguments:
    ----------
    time : int, str, or None
        The time input to standardize.

    Returns:
    --------
    int or None
        The standardized Unix timestamp, or None if the input is None.
    """
    if time is None:
        return None
    elif isinstance(time, str):
        return datetime_to_timestamp(time)
    else:
        return int(time)
