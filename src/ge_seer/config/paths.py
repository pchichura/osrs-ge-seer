from pathlib import Path

# default store config files in a hidden folder in user home directory
DEFAULT_BASE_DIR = Path.home() / ".ge_seer"
DEFAULT_CONFIG_FILE = DEFAULT_BASE_DIR / "config.json"


def get_config_path():
    """
    Get the path to the user configuration file, ensuring the directory exists.

    Returns:
    --------
    Path
        The path to the configuration file.
    """
    DEFAULT_BASE_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_CONFIG_FILE
