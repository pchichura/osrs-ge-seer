import json
from pathlib import Path
from .paths import get_config_path


def save_config(contact_info, contact_type, data_dir, verbose=True):
    """
    Saves the user configuration to a JSON file. This includes the user-agent string
    for scraping the OSRS Wiki for data, and the user's preferred data directory.

    Arguments:
    ----------
    contact_info : str
        The user's contact information (e.g., Discord handle, email).
    contact_type : str
        The type of contact information provided (e.g., "Discord", "Email").
    data_dir : str or Path
        Path to the directory where data will be stored.
    verbose : bool [True]
        If True, prints status messages.
    """

    # format the user-agent as requested by OSRS Wiki
    # for details, see: https://oldschool.runescape.wiki/w/RuneScape:Real-time_Prices
    if contact_type == "discord":
        contact = f"{contact_info} on Discord"
    elif contact_type == "email":
        contact = f"{contact_info} via Email"
    else:
        raise ValueError("Invalid contact type. Must be 'discord' or 'email'.")
    user_agent = f"osrs-ge-seer (GE price history + modeling) - {contact}"

    # ensure the user's chosen data directory exists
    resolved_data_path = Path(data_dir).expanduser().resolve()
    resolved_data_path.mkdir(parents=True, exist_ok=True)

    # create the config file
    config = {"user_agent": user_agent, "data_dir": str(resolved_data_path)}
    with open(get_config_path(), "w") as f:
        json.dump(config, f, indent=4)

    # status updates
    if verbose:
        print(f"OSRS Wiki API User-Agent set to: {user_agent}")
        print(f"Configuration saved to {get_config_path()}")
        print(f"Data directory set to: {resolved_data_path}")


def load_config():
    """
    Loads the user configurations from the JSON file created during setup.
    """
    path = get_config_path()
    if not path.exists():
        raise FileNotFoundError("Package not configured. Please run 'ge_seer.setup()'.")

    with open(path, "r") as f:
        return json.load(f)
