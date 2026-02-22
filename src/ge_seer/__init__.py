from .config.manager import save_config, load_config
from pathlib import Path

__all__ = [
    "setup",
    "config",
    "data",
]

__version__ = "0.1.0"


def setup():
    """
    Interactive setup wizard to configure the package for first-time use. This setup
    prompts the user for necessary information which are then stored in a configuration
    file. Information includes:
        1. Contact information (Discord username or email) if needed by OSRS Wiki staff.
        2. Preferred data directory for storing large datasets.
    """
    print("\n--- OSRS GE Seer Setup ---")
    print("\nThe OSRS Wiki API requires a User-Agent that includes contact info.")
    print("This allows them to reach out if your tool causes technical issues.")

    # get contact info for user-agent
    print("\nHow should the Wiki staff contact you if needed?")
    print("[1] Discord Username")
    print("[2] Email Address")
    choice = input("Select [1/2]: ").strip()

    contact_type = "discord" if choice == "1" else "email"
    contact_info = input(f"Enter your {contact_type}: ").strip()

    # get desired data directory for storing large datasets
    default_data = Path.home() / "ge_seer_data"
    print(f"\nWhere should large datasets be stored?")
    print(f"Default: {default_data}")
    custom_dir = input(
        "Press Enter for default, or provide a new absolute path: "
    ).strip()
    data_dir = Path(custom_dir) if custom_dir else default_data
    resolved_data_path = Path(data_dir).expanduser().resolve()

    # save the configuration
    print()
    save_config(contact_info, contact_type, resolved_data_path, verbose=True)
    print("\nSetup complete!")
