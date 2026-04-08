# Edbov Data

A project that gathers information about from different sources.
The sources currently implemented are Netatmo, Tibber, SMHI, and
Open-Meteo (as a drop-in alternative to SMHI).

For information on how to run and use the project see the project documentation.

## Weather provider configuration

Weather forecasts can be fetched from either SMHI (default) or Open-Meteo.
A primary provider is tried first, and on failure an automatic fallback to
the secondary provider is used.

```ini
[WEATHER]
provider = smhi        # primary: "smhi" or "open_meteo" (default: smhi)
fallback = open_meteo  # secondary: "smhi", "open_meteo", or "none"
                       # (default: the "other" provider)
```

Open-Meteo (https://open-meteo.com) requires no API key and maps its WMO
4677 weather codes to SMHI's 1-27 symbol codes so that downstream models
trained on SMHI data keep working unchanged.


## Documentation
To build the documentation:

``` shell
cd docs
make html
```

The html documentation can then be viewed by browsing to:
edbo_data/docs/_build/html/index.html
