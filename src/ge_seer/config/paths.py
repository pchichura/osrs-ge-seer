from pathlib import Path

# define important paths for the project
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"

# ensure that the data directories exist
for path in [DATA_DIR, RAW_DATA_DIR]:
    path.mkdir(parents=True, exist_ok=True)
