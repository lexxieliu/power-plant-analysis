"""
Takes hourly_summary.csv and turns it into three "long" (melted) CSVs,
one per Tableau chart. Tableau charts read long data better than wide.

Outputs:
  - demand_weather_long.csv   for the "Demand vs weather" chart
  - power_mix_long.csv        for the "Campus power mix" chart
  - steam_destinations_long.csv  for the "Where every pound goes" chart
"""

import pandas as pd
from pathlib import Path

OUT = Path("outputs")
df = pd.read_csv(OUT / "hourly_summary.csv", parse_dates=["timestamp"])

# ---------------------------------------------------------------
# 1. demand_weather_long.csv
#    Total demand, heating-only demand (chillers removed), and temperature
# ---------------------------------------------------------------
dw = df[["timestamp", "month", "season"]].copy()
dw["Total demand"] = df["campus_steam_demand"]
dw["Heating only"] = df["campus_steam_demand"] - df["chiller_steam"]
dw["Temperature"] = df["noaa_temp"]

demand_weather_long = dw.melt(
    id_vars=["timestamp", "month", "season"],
    var_name="series", value_name="value",
)
demand_weather_long.to_csv(OUT / "demand_weather_long.csv", index=False)
print(f"demand_weather_long.csv: {len(demand_weather_long)} rows")

# ---------------------------------------------------------------
# 2. power_mix_long.csv
#    Gas turbines, steam turbines, and purchased power (MW)
# ---------------------------------------------------------------
pm = df[["timestamp", "month", "season"]].copy()
pm["Gas turbines"] = df["gt_kw_total"] / 1000
pm["Steam turbines"] = df["stg_kw_total"] / 1000
generated = pm["Gas turbines"] + pm["Steam turbines"]
campus_mw = df["campus_electrical_load"] / 1000
pm["Purchased"] = (campus_mw - generated).clip(lower=0)

power_mix_long = pm.melt(
    id_vars=["timestamp", "month", "season"],
    var_name="source", value_name="mw",
)
power_mix_long.to_csv(OUT / "power_mix_long.csv", index=False)
print(f"power_mix_long.csv: {len(power_mix_long)} rows")

# ---------------------------------------------------------------
# 3. steam_destinations_long.csv
#    "Produced" bar = total production.
#    "Where it went" bar = campus export + chillers + condensed (turbines).
#    Campus export is the export meters minus chiller draw, since
#    chillers pull from the same line but aren't campus heating steam.
# ---------------------------------------------------------------
rows = []
for _, r in df[["timestamp", "season", "total_production",
                 "campus_steam_demand", "chiller_steam",
                 "turbine_condensate"]].iterrows():
    campus_export = r["campus_steam_demand"] - r["chiller_steam"]
    rows.append((r["timestamp"], r["season"], "Produced", "Produced", r["total_production"]))
    rows.append((r["timestamp"], r["season"], "Where it went", "Campus Export", campus_export))
    rows.append((r["timestamp"], r["season"], "Where it went", "Chillers", r["chiller_steam"]))
    rows.append((r["timestamp"], r["season"], "Where it went", "Condensed", r["turbine_condensate"]))

steam_destinations_long = pd.DataFrame(
    rows, columns=["timestamp", "season", "bar", "destination", "steam_flow"]
)
steam_destinations_long.to_csv(OUT / "steam_destinations_long.csv", index=False)
print(f"steam_destinations_long.csv: {len(steam_destinations_long)} rows")
