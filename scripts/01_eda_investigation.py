"""
01_eda_investigation.py
Runs checks on the merged raw data and prints the evidence behind each fix in data_decisions.md.
No fixes applied here - just look and report. Fixes happen in
02_prep_tableau_data.py.
"""

import pandas as pd
from pathlib import Path

IN_PATH = Path("outputs/raw_combined.csv")
df = pd.read_csv(IN_PATH, parse_dates=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

# ---------------------------------------------------------------
# 1. Boiler 3 looked way too high
# ---------------------------------------------------------------
print("=== 1. Boiler steam levels ===")
for b in ["Boiler 1", "Boiler 2", "Boiler 3"]:
    print(f"  {b} mean steam: {df[f'internal_steam | {b} Steam'].mean():,.1f}")
print("  Boiler 3 is dramatically higher than the others -> looks like a unit")
print("  mismatch. Header notes confirm a different unit for that sensor.")

# ---------------------------------------------------------------
# 2. Campus Load didn't behave like steam demand
# ---------------------------------------------------------------
print("\n=== 2. Campus Load vs temperature ===")
corr = df["internal_steam | Campus Load"].corr(df["weather | NOAA "])
print(f"  correlation with temperature: {corr:.3f}")
print("  Steam demand for heating should drop when it's warm (negative corr).")
print("  This is positive - rises with temperature. Its unit is KWH too,")
print("  while every other internal_steam column is K lbs/Hour.")
print("  -> Campus Load is actually electrical load, not steam demand.")

# ---------------------------------------------------------------
# 3. HRSG 2 has a big gap in exactly one place
# ---------------------------------------------------------------
print("\n=== 3. HRSG 2 missing data ===")
is_na = df["internal_steam | HRSG 2 Steam"].isna()
block_id = (is_na != is_na.shift()).cumsum()
gaps = (df.assign(is_na=is_na, block=block_id)
          .groupby("block")
          .agg(start=("timestamp", "min"), end=("timestamp", "max"), n=("timestamp", "size"), is_na=("is_na", "first")))
gaps = gaps[gaps.is_na].sort_values("n", ascending=False)
biggest = gaps.iloc[0]
print(f"  Longest gap: {biggest.start} to {biggest.end} ({biggest.n} hours)")
fuel_in_gap = df[(df.timestamp >= biggest.start) & (df.timestamp <= biggest.end)]["plant_inputs | HRSG 2 "]
print(f"  Fuel burned during that gap: mean {fuel_in_gap.mean():.2f}, max {fuel_in_gap.max():.2f}")
print("  Fuel is zero the whole time -> looks like a planned outage, not a broken sensor.")

# ---------------------------------------------------------------
# 4. Boilers show tiny steam readings even when fully off
# ---------------------------------------------------------------
print("\n=== 4. Phantom readings when boiler is off ===")
off_no_fuel = (df["assets_running | Boiler 1"] == 0) & (df["plant_inputs | Boiler 1"] < 0.5)
steam_while_off = df.loc[off_no_fuel, "internal_steam | Boiler 1 Steam"]
print(f"  Hours Boiler 1 is off with no fuel: {off_no_fuel.sum()}")
print(f"  Of those, {(steam_while_off > 0).sum()} still show a nonzero steam reading")
print(f"  Max phantom reading: {steam_while_off.max():.2f} K lbs/Hour (should be 0)")
print("  -> small sensor drift, not real steam. Safe to zero out.")

# ---------------------------------------------------------------
# 5. Some turbine meters are obviously dead
# ---------------------------------------------------------------
print("\n=== 5. Turbine steam meters ===")
for t in ["Turbine #1", "Turbine #2", "Turbine #3", "Turbine #7"]:
    col = f"internal_steam | {t} Steam"
    print(f"  {t}: mean {df[col].mean():,.3f}, max {df[col].max():,.1f}")
print("  Turbine #1 looks real (large nonzero values). #2 and #7 are flat zero.")
print("  #3 is basically zero too, next to Turbine #1's much larger readings")
print("  - noise, not signal.")
print("  These 3 meters get excluded from any steam-balance calculation.")

print("\nSee data_decisions.md for how each finding turned into a fix.")
