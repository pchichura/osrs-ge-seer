from datetime import datetime, timezone


def get_current_timestamp():
    """
    Returns the current Unix timestamp in UTC.
    """
    return int(datetime.now(timezone.utc).timestamp())


def timestamp_to_datetime(time):
    """
    Converts a Unix timestamp to a human-readable string in UTC.

    Arguments:
    ----------
    timestamp : int
        The Unix timestamp to convert.

    Returns:
    --------
    str
        The human-readable string representation of the timestamp in UTC.
    """
    return datetime.fromtimestamp(time, timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def datetime_to_timestamp(time):
    """
    Converts a human-readable datetime string in UTC to a Unix timestamp.

    Arguments:
    ----------
    time : str
        The datetime string to convert, in the format "YYYY-MM-DD HH:MM:SS UTC".

    Returns:
    --------
    int
        The corresponding Unix timestamp.
    """
    dt = datetime.strptime(time, "%Y-%m-%d %H:%M:%S UTC")
    return int(dt.replace(tzinfo=timezone.utc).timestamp())


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
