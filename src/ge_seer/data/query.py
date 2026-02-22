import requests, json
from ..config.manager import load_config
from pathlib import Path


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


def query_prices():
    """
    Placeholder function for querying price data from the OSRS Wiki GE API. Retrieve and
    store price data in the data directory defined during package setup.
    """
    print("Querying price data from the OSRS Grand Exchange API... (placeholder)")
    pass
