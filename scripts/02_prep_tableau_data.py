"""
Reads the raw SCADA export and builds clean CSVs for Tableau

See data_decisions.md for why each fix below is needed.
"""

import pandas as pd
from pathlib import Path

SRC = Path("data/combined_export.xlsx")
OUT = Path("outputs")
OUT.mkdir(exist_ok=True)

df = pd.read_excel(SRC, sheet_name="combined_output", engine="openpyxl")
print(f"Raw shape: {df.shape}")

# ---------------------------------------------------------------
# 1. Rename columns to clean snake_case
# ---------------------------------------------------------------
rename = {
    "Timestamp": "timestamp",
    "internal_steam | Campus Load": "campus_load",  # actually electrical load, see FIX C
    "internal_steam | Boiler 1 Steam": "boiler1_steam",
    "internal_steam | Boiler 2 Steam": "boiler2_steam",
    "internal_steam | Boiler 3 Steam": "boiler3_steam",
    "internal_steam | Boiler 5 Steam": "boiler5_steam",
    "internal_steam | Boiler 6 Steam": "boiler6_steam",
    "internal_steam | HRSG 1 Steam": "hrsg1_steam",
    "internal_steam | HRSG 2 Steam": "hrsg2_steam",
    "assests_running | Boiler 1": "run_boiler1",
    "assests_running | Boiler 2": "run_boiler2",
    "assests_running | Boiler 3": "run_boiler3",
    "assests_running | Boiler 5": "run_boiler5",
    "assests_running | Boiler 6": "run_boiler6",
    "assests_running | HRSG1": "run_hrsg1",
    "assests_running | HRSG2": "run_hrsg2",
    "plant_inputs | Boiler 1 NatGas": "gas_boiler1",
    "plant_inputs | Boiler 2 NatGas": "gas_boiler2",
    "plant_inputs | Boiler 3 NatGas": "gas_boiler3",
    "plant_inputs | Gas Turbine 1Nat Gas": "gas_gt1",
    "plant_inputs | Gas Turbine 2 NatGas": "gas_gt2",
    "plant_inputs | HRSG #1 NatGas": "gas_hrsg1",
    "plant_inputs | HRSG #2 NatGas": "gas_hrsg2",
    "plant_inputs | Boiler 5 N. Coal Scale": "coal_boiler5_n",
    "plant_inputs | Boiler 5 S. Coal Scale": "coal_boiler5_s",
    "plant_inputs | Boiler 6 N. Coal Scale": "coal_boiler6_n",
    "plant_inputs | Boiler 6 S. Coal Scale": "coal_boiler6_s",
    "electrical | Plant In-House Elec usage": "plant_inhouse_elec",
    "electrical | CG01-107B GT#2 KW": "gt2_kw",
    "electrical | CG02-106B GT#1 KW": "gt1_kw",
    "internal_steam | Turbine #6 Condensate": "t6_condensate",
    "internal_steam | Turbine #9 Condensate": "t9_condensate",
    "steam_output | Steam Driven chiller#1 Condensate(steam)": "chiller1_steam",
    "steam_output | Steam Driven chiller#2 Condensate(steam)": "chiller2_steam",
    "electrical | CG01-103B STG#9 KW": "stg9_kw",
    "electrical | CG02-102B STG#10 KW": "stg10_kw",
    "electrical | AP99-108B STG#1 KW": "stg1_kw",
    "electrical | AP99-109B STG#2 KW": "stg2_kw",
    "electrical | AP99-102B STG#3 KW": "stg3_kw",
    "steam_output | Stm Flow xmtr FT-CS121": "export_cs121",
    "steam_output | Stm Flow xmtr FT-CS122": "export_cs122",
    "steam_output | Stm Flow xmtr FT-CS141": "export_cs141",
    "steam_output | Stm Flow xmtr FT-CS142": "export_cs142",
    "steam_output | Stm Flow xmtr FT-US801": "export_us801",
    "steam_output | Stm Flow xmtr FT-US101": "export_us101",
    "steam_output | Stm Flow xmtr FT-US051": "export_us051",
    "weather | NOAA Temperature": "noaa_temp",
    "weather | NOAA DewPoint": "noaa_dewpoint",
    "weather | NOAA Wind Speed": "noaa_wind",
}
df = df.rename(columns=rename)[list(rename.values())]

# ---------------------------------------------------------------
# 2. Data-quality fixes (details in data_decisions.md)
# ---------------------------------------------------------------

# FIX A: Boiler 3 was recorded in lbs/hr, all others in K lbs/hr
df["boiler3_steam"] = df["boiler3_steam"] / 1000.0

# FIX B: HRSG 2 has a planned-outage gap (Sep 26 - Nov 5, 2025), fill as 0
df["hrsg2_steam"] = df["hrsg2_steam"].fillna(0.0)

# FIX B2: sensor drift when a boiler is OFF and using no fuel, it should
# read 0 steam. Zero out small (<5 K lbs/hr) readings in that case.
# Not applied to Boiler 6 / HRSGs - their off-state flow looks real
# (removing it would break the plant's steam balance).
phantom_targets = [
    ("boiler1_steam", "run_boiler1", ["gas_boiler1"]),
    ("boiler2_steam", "run_boiler2", ["gas_boiler2"]),
    ("boiler3_steam", "run_boiler3", ["gas_boiler3"]),
    ("boiler5_steam", "run_boiler5", ["coal_boiler5_n", "coal_boiler5_s"]),
]
for steam_col, run_col, fuel_cols in phantom_targets:
    fuel = df[fuel_cols].sum(axis=1)
    is_drift = (df[run_col] == 0) & (fuel < 0.5) & (df[steam_col] < 5.0)
    df.loc[is_drift, steam_col] = 0.0

# FIX C: "Campus Load" is electrical load, not steam. Real steam demand
# is the sum of the 7 export flow meters.
export_cols = [c for c in df.columns if c.startswith("export_")]
df["campus_steam_demand"] = df[export_cols].sum(axis=1)

# FIX D: drop the few rows still missing key values (~0.1% of data)
prod_cols = ["boiler1_steam", "boiler2_steam", "boiler3_steam",
             "boiler5_steam", "boiler6_steam", "hrsg1_steam", "hrsg2_steam"]
before = len(df)
df = df.dropna(subset=prod_cols + ["campus_steam_demand", "campus_load"]).reset_index(drop=True)
print(f"Dropped {before - len(df)} incomplete rows -> {len(df)} rows left")

# ---------------------------------------------------------------
# 3. Derived columns
# ---------------------------------------------------------------
df["total_production"] = df[prod_cols].sum(axis=1)
df["campus_electrical_load"] = df["campus_load"]

# gap = production not sent to campus. Mostly cogeneration (condensed
# through turbines for electricity) + chillers, not waste.
df["excess_production"] = df["total_production"] - df["campus_steam_demand"]
df["utilization_pct"] = df["campus_steam_demand"] / df["total_production"]

df["gt_kw_total"] = df[["gt1_kw", "gt2_kw"]].fillna(0).sum(axis=1)
df["turbine_condensate"] = df["t6_condensate"] + df["t9_condensate"]
df["chiller_steam"] = df["chiller1_steam"].fillna(0) + df["chiller2_steam"].fillna(0)
df["stg_kw_total"] = df[["stg9_kw", "stg10_kw", "stg1_kw", "stg2_kw", "stg3_kw"]].fillna(0).sum(axis=1)
df["total_natgas"] = df[[c for c in df.columns if c.startswith("gas_")]].sum(axis=1)
df["total_coal"] = df[[c for c in df.columns if c.startswith("coal_")]].sum(axis=1)

ts = pd.to_datetime(df["timestamp"])
df["date"] = ts.dt.date
df["hour"] = ts.dt.hour
df["month"] = ts.dt.month
df["weekday"] = ts.dt.day_name()
df["season"] = ts.dt.month.map({
    12: "Winter", 1: "Winter", 2: "Winter",
    3: "Spring", 4: "Spring", 5: "Spring",
    6: "Summer", 7: "Summer", 8: "Summer",
    9: "Fall", 10: "Fall", 11: "Fall",
})

# ---------------------------------------------------------------
# 4. Write hourly_summary.csv (wide, one row per hour)
# ---------------------------------------------------------------
summary_cols = [
    "timestamp", "date", "hour", "month", "weekday", "season",
    "campus_steam_demand", "campus_electrical_load",
    "total_production", "excess_production",
    "gt_kw_total", "turbine_condensate", "chiller_steam", "stg_kw_total",
    "utilization_pct", "total_natgas", "total_coal", "plant_inhouse_elec",
    "noaa_temp", "noaa_dewpoint", "noaa_wind",
]
df[summary_cols].to_csv(OUT / "hourly_summary.csv", index=False)
print(f"hourly_summary.csv: {len(df)} rows")

# ---------------------------------------------------------------
# 5. Write generation_long.csv (tidy, one row per hour per asset)
# ---------------------------------------------------------------
assets = {
    "Boiler 1": ("boiler1_steam", "run_boiler1", "Natural Gas"),
    "Boiler 2": ("boiler2_steam", "run_boiler2", "Natural Gas"),
    "Boiler 3": ("boiler3_steam", "run_boiler3", "Natural Gas"),
    "Boiler 5": ("boiler5_steam", "run_boiler5", "Coal"),
    "Boiler 6": ("boiler6_steam", "run_boiler6", "Coal"),
    "HRSG 1":   ("hrsg1_steam",   "run_hrsg1",   "Natural Gas"),
    "HRSG 2":   ("hrsg2_steam",   "run_hrsg2",   "Natural Gas"),
}
frames = []
for asset, (steam_col, run_col, fuel) in assets.items():
    frames.append(pd.DataFrame({
        "timestamp": df["timestamp"],
        "season": df["season"],
        "asset": asset,
        "steam_flow": df[steam_col],
        "run_state_sensor": df[run_col],
        "run_state": (df[steam_col] > 1.0).astype(int),  # flow > 1 K lbs/hr = running
        "fuel_type": fuel,
    }))
long_df = pd.concat(frames, ignore_index=True)
long_df.to_csv(OUT / "generation_long.csv", index=False)
print(f"generation_long.csv: {len(long_df)} rows")

# ---------------------------------------------------------------
# 6. Sanity checks before loading into Tableau
# ---------------------------------------------------------------
checks = [
    ("Boiler 3 mean in range (10-60)", 10 < df["boiler3_steam"].mean() < 60),
    ("Steam demand mean in range (100-250)", 100 < df["campus_steam_demand"].mean() < 250),
    ("No negative production", (df[prod_cols] >= 0).all().all()),
    ("No negative campus load", (df["campus_load"] > 0).all()),
    ("Utilization median in range (0.2-1.2)", 0.2 < df["utilization_pct"].median() < 1.2),
    ("Steam demand vs temp corr < -0.5", df["campus_steam_demand"].corr(df["noaa_temp"]) < -0.5),
    ("Electrical load vs temp corr > 0.3", df["campus_electrical_load"].corr(df["noaa_temp"]) > 0.3),
    ("T9 condensate tracks STG#9 output (r > 0.8)", df["t9_condensate"].corr(df["stg9_kw"]) > 0.8),
]
print("\n--- checks ---")
for name, ok in checks:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
