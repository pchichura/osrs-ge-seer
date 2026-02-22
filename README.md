Code for building a dataset of Old School Runescape Grand Exchange price histories,
and training models to predict valuable products to buy and sell.

## Setup

In order to scrape the OSRS Wiki for data used throughout the package, a one-time configuration is required to comply with the [OSRS Wiki API Policy](https://oldschool.runescape.wiki/w/RuneScape:Real-time_Prices), which requires a custom `User-Agent` for contact purposes.

After installation, run the setup wizard in Python:

```python
import ge_seer
ge_seer.setup()
```

The wizard will:
- Ask for your Discord or Email to format your User-Agent
- Define where to store large datasets (default: ~/ge_seer_data)
- Save settings to ~/.ge_seer/config.json
