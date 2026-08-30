# Data Decisions (Portfolio / Simulated Data)

> All numbers below are placeholders (`X`, `X%`). This document describes
> the *type* of fix and the reasoning, not real values.

Source: raw historian export, ~X hourly rows, roughly a X-year period.

## Fixes applied

1. **Unit mismatch on one boiler's steam sensor**: raw reading was ~X
   times higher than the other boilers. Header notes confirmed it was in
   a different unit (lbs/hr instead of K lbs/hr). Fixed by dividing by
   1,000.
2. **In-service date for that boiler resolved from data**: before a
   certain point the boiler had zero fuel and an OFF run-state while the
   steam sensor still read a small nonzero value (phantom drift). After
   that point: real fuel, ON run-state, and two other boilers backed off
   at the same time (load redistribution). Conclusion: the boiler
   genuinely entered service on that date. No client input needed.
3. **Phantom drift cleanup (several boilers)**: readings zeroed when
   run-state = OFF, fuel < X, and reading < X. Zeroed a few hundred
   readings per affected boiler.
4. **One heat-recovery unit's outage fill**: a multi-week gap with zero
   fuel the whole time → planned outage, filled with 0.
5. **Demand redefined**: one "load" sensor turned out to be campus
   ELECTRICAL load (correlates positively with temperature), not steam.
   True steam demand = sum of several export flow transmitters (strongly
   negative correlation with temperature, as expected for heating).
6. **Excluded (bad meters)**: two turbine meters read flat zero the whole
   time, and a third read essentially zero (noise) next to a comparable
   turbine reading realistic values - all three excluded from steam
   balance calculations.
7. **Some off-state flows kept, not zeroed**: two assets show real steam
   flow with zero fuel and an OFF run-state - but the plant's overall
   steam balance only closes (production ≈ export + condensate) if these
   flows are included. Flow meters trusted; asset ATTRIBUTION flagged for
   follow-up instead of dropped.
8. **Run state** derived from steam flow > X (sensor run-state columns
   were patchy / incomplete for part of the date range).

## Gap decomposition (the key finding)

Production minus export gap is NOT waste. It is almost entirely
cogeneration: steam condensed in two turbines to generate electricity,
plus a smaller share to steam-driven chillers. Electrical confirmation:
correlation between one turbine's condensate and its matching generator
output was very strong (near 1.0).
→ The optimization question is cogeneration economics (steam-to-power vs.
grid purchase), not "eliminating excess steam."

## Final validated metrics (illustrative only, not real numbers)

- Steam demand: mean X, max X K lbs/hr; winter about 2x summer;
  correlation with temperature strongly negative
- Total production: mean X K lbs/hr
- Gap: mean X; positive nearly all hours; close to turbine condensate
- Median utilization (export/production): around X
- Per-asset mean flow / runtime: varies by asset, roughly X% runtime
  across boilers and close to X% for the heat-recovery units

## Open questions (client, when reachable)

1. One boiler shows summer steam with no coal and an OFF run-state - is
   this meter on a different header?
2. One set of heat-recovery residual flows persist with both the gas
   turbine and duct burner off - economizer/blowdown recovery?
3. Confirm the heat-recovery outage was planned.
4. Confirm the forecasting model target matches the export-meter
   definition of demand.

## Files (generic names - see README for the real script names)

- hourly_summary.csv - one row per hour, adds turbine condensate,
  chiller steam, and generator kW total
- generation_long.csv - one row per hour per asset (run-state derived +
  sensor run-state)
- prep script - reproducible, with a validation gate before anything
  loads into the dashboard tool
