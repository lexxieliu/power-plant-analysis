"""
00_eda_data_cleaning.py
Cleans the raw historian export and merges all tabs into one hourly table.

  - "Internal Steam", "Asset Running", "Electrical": still raw. Each
    variable has its own timestamp column right before its value column
    (the historian exports one column pair per point). 3 header rows on
    top (Data Type / Description / Units), then data starts.

"""

import pandas as pd
from pathlib import Path

SRC = Path("data/raw__export.xlsx")
OUT = Path("outputs")
OUT.mkdir(exist_ok=True)


def parse_raw_tab(sheet, n_header_rows=3):
    """Turn one raw tab (timestamp+value column pairs) into a clean table."""
    raw = pd.read_excel(SRC, sheet_name=sheet, header=None, engine="openpyxl")
    labels = raw.iloc[1]  # 2nd row holds the variable names
    data = raw.iloc[n_header_rows:].reset_index(drop=True)

    variables = {}
    ts_col = None
    bad_values = 0
    for col in data.columns:
        sample = data[col].dropna()
        if sample.empty:
            continue
        if hasattr(sample.iloc[0], "year"):
            ts_col = col  # this column is a timestamp column
            continue
        label = labels[col]
        if label is None or ts_col is None:
            continue
        ts = pd.to_datetime(data[ts_col].values, errors="coerce")
        raw_series = pd.Series(data[col].values, index=ts)
        series = pd.to_numeric(raw_series, errors="coerce")
        bad_values += (series.isna() & raw_series.notna()).sum()  # sensor error codes etc.
        # drop bad timestamps (blank cells sometimes read as year 1970)
        series = series[series.index.notna()
                         & (series.index.year >= 2020)
                         & (series.index.year <= 2030)]
        series.index = series.index.round("h")
        series = series[~series.index.duplicated(keep="first")]
        variables[str(label).strip()] = series

    if bad_values:
        print(f"  {sheet}: {bad_values} non-numeric readings (sensor errors) -> NaN")
    return pd.DataFrame(variables)


print("Parsing raw tabs...")
internal = parse_raw_tab("Internal Steam").add_prefix("internal_steam | ")
asset = parse_raw_tab("Asset Running").add_prefix("assets_running | ")
elec = parse_raw_tab("Electrical").add_prefix("electrical | ")

print("Loading already-cleaned tabs...")
plant = pd.read_excel(SRC, sheet_name="Plant Inputs (2)").rename(columns={"Date": "timestamp"})
plant["timestamp"] = plant["timestamp"].dt.round("h")
plant = (plant.drop(columns=["Date_rt"])
              .drop_duplicates("timestamp")
              .set_index("timestamp")
              .add_prefix("plant_inputs | "))

weather = (pd.read_excel(SRC, sheet_name="weather (2)")
             .rename(columns={"Date": "timestamp"})
             .set_index("timestamp"))
# sensor error codes like "[-11059] No Good Data For Calculation" -> NaN
error_code = "[-11059] No Good Data For Calculation"
n_sensor_errors = (weather == error_code).sum().sum()
print(f"Sensor error codes in weather tab (converted to NaN): {n_sensor_errors}")
weather = weather.apply(pd.to_numeric, errors="coerce").add_prefix("weather | ")

# ---------------------------------------------------------------
# Merge everything on one hourly timeline
# ---------------------------------------------------------------
combined = internal.join(asset, how="outer").join(elec, how="outer") \
                    .join(plant, how="outer").join(weather, how="outer")
combined = combined.sort_index()
combined.index.name = "timestamp"

print(f"\nCombined shape: {combined.shape}")
print(f"Range: {combined.index.min()} to {combined.index.max()}")

combined.to_csv(OUT / "raw_combined.csv")
print(f"Saved outputs/raw_combined.csv")

# ---------------------------------------------------------------
# Data quality checks
# ---------------------------------------------------------------
print("\n=== Data quality ===")

dupes = combined.index.duplicated().sum()
print(f"Duplicate timestamps: {dupes}")

expected = pd.date_range(combined.index.min(), combined.index.max(), freq="h")
gaps = expected.difference(combined.index)
print(f"Missing hours in timeline: {len(gaps)}")

missing = combined.isna().sum()
missing = missing[missing > 0].sort_values(ascending=False)
print(f"\nColumns with missing values: {len(missing)} of {combined.shape[1]}")
print(missing.head(10))

non_numeric = combined.select_dtypes(exclude="number").columns.tolist()
print(f"\nNon-numeric columns (should be empty): {non_numeric}")

negatives = (combined.select_dtypes("number") < 0).sum()
negatives = negatives[negatives > 0]
print(f"\nColumns with negative values (check if expected, e.g. export to grid):")
print(negatives)
