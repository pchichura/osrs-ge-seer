Code for building a dataset of Old School Runescape Grand Exchange price histories,
and training models to predict valuable products to buy and sell.

## Setup

In order to scrape the OSRS Wiki for data used throughout the package, a one-time configuration is required to comply with the [OSRS Wiki API Policy](https://oldschool.runescape.wiki/w/RuneScape:Real-time_Prices), which requires a custom User-Agent for contact purposes.

After installation, run the setup wizard in Python:

```python
import ge_seer
ge_seer.setup()
```

The wizard will:
- Ask for your Discord or Email to format your User-Agent
- Define where to store large datasets (default: ~/ge_seer_data)
- Save settings to ~/.ge_seer/config.json

## Building a Price Dataset

Grand Exchange price data is queried from the OSRS Wiki using their [API](https://oldschool.runescape.wiki/w/RuneScape:Real-time_Prices). Different methods are provided for calling the API to query data and either return the data or save it to disk. Data is automatically saved as parquet files and read from the user-specified directory during setup.

The data at each time instance consists of high and low prices for each item averaged over a specified time step, as well as the volume traded during that period. Specifically, the price data for each item and each time consists of:
- `"avgHighPrice"`: the volume-weighted average of instant-buy transactions
- `"highPriceVolume"`: the volume of instant-buy transactions
- `"avgLowPrice"`: the volume-weighted average of instant-sell transactions
- `"lowPriceVolume"`: the volume of instant-sell transactions

### Query a single time instance

Query price data for all items at a specified time instance for all items. Returns a `pandas.DataFrame` and optionally saves the data. Example:

```python
from ge_seer.data.query import query_prices_instance

# Unix timestamp (in UTC)
df = query_prices_instance(
    query_time=1761004800, timestep="24h", store=False
)

# datetime string (UTC)
df = query_prices_instance(
    query_time="2025-11-01 01:20:00 UTC", timestep="5m", store=True
)
```

### Query a single item time series

Query recent price data for one item across many time instances (up to the latest 365 samples at the selected timestep). Returns a `pandas.DataFrame` and optionally saves only new timestamps to disk. Example:

```python
from ge_seer.data.query import query_prices_timeseries

df = query_prices_timeseries(item_id=4151, timestep="24h", store=False)
```

Use this method for targeted, recent item histories. If you need many items across
many timestamps, prefer `query_prices_range`.

### Batch query a time range

Query price data for all items over a range in time, automatically saving the data to disk. Example:

```python
from ge_seer.data.query import query_prices_range

# defaults: stop is now, start is 30 steps before stop, step size 24h
query_prices_range()

# custom range (strings or ints both supported)
query_prices_range(
		time_start="2025-10-01 00:00:00 UTC",
		time_stop="2025-10-02 00:00:00 UTC",
		timestep="1h",
)
```

Or you can execute a script at the command line. Example:

```bash
python scripts/query_prices.py
python scripts/query_prices.py --start "2025-11-01 00:00:00 UTC" --stop "2025-11-08 00:00:00 UTC" --timestep 1h
python scripts/query_prices.py --start 1761004800 --stop 1761609600 --timestep 24h
```

## Reading Saved Price Data

Load previously queried price data from disk. Currently, only supports reading data for a single item. The reader merges data from both `instance` and `timeseries` storage layouts (when available), and de-duplicates overlapping timestamps. Example:

```python
from ge_seer.data import read_prices_data

# read all saved data for a single item
df = read_prices_data(item_id=2, timestep="24h")

# read with optional time bounds
df = read_prices_data(
    item_id=2,
    timestep="1h",
    time_start="2025-10-01 00:00:00 UTC",
    time_stop="2025-11-01 00:00:00 UTC",
)
```

Returns a `pandas.DataFrame` with columns: `time`, `avgHighPrice`, `highPriceVolume`, `avgLowPrice`, `lowPriceVolume`.
