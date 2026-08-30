# Power Plant Operational Analysis (Portfolio / Simulated Data)

> **Note:** This repo is a portfolio piece. The dataset, dashboard, and all
> figures below are simulated / fake, not real facility data. Numbers in
> the findings are placeholders (`X`, `X%`) and do not represent actual
> operating values. Only the analysis approach and code are meant to be
> real.

Analysis of hourly SCADA data from a central utility plant, covering fuel
inputs, boiler/turbine run states, steam metering, electrical metering,
campus steam export, and weather over roughly X years (~X hourly rows).
The result is a dashboard for non-technical plant stakeholders.

![dashboard](docs/dashboard_screenshot.png)

## Repo layout

```
scripts/
  00_eda_data_cleaning.py       raw tabs -> outputs/raw_combined.csv
                                 (merges timestamp/value column pairs,
                                 fixes sensor error codes, checks quality)
  01_eda_investigation.py       the detective work: runs checks that
                                 surface each problem, with evidence
  02_prep_tableau_data.py       raw export -> hourly_summary.csv, generation_long.csv
  03_build_dashboard_extracts.py  -> demand_weather_long.csv, power_mix_long.csv,
                                      steam_destinations_long.csv (one per chart)
data_decisions.md               every data-quality fix, and why
docs/
  presentation_script.md        spoken walkthrough for the dashboard
  dashboard_screenshot.png      (numbers blurred - simulated data)
```

Run in order:
```bash
python scripts/00_eda_data_cleaning.py
python scripts/01_eda_investigation.py
python scripts/02_prep_tableau_data.py
python scripts/03_build_dashboard_extracts.py
```

`00_eda_data_cleaning.py` reads the raw historian export, which has a
messy layout - one timestamp column per variable, 3 header rows, sensor
error codes as text. `01_eda_investigation.py` runs on that merged output
and shows the evidence for each problem (e.g. one boiler reading X times
higher than the others, a demand sensor correlating the wrong way with
temperature). `02_prep_tableau_data.py` reads an already-merged export
instead - point it at your own combined file, or swap in
`outputs/raw_combined.csv` to run the whole pipeline from the raw file
end to end.

Note: the raw export used here doesn't include a "Steam Output" tab
(export flow meters, chiller condensate) - those columns are missing from
`raw_combined.csv`.

## Key findings (numbers are placeholders - see disclaimer above)

- **Steam demand looks weather-driven, but only after separating chillers
  from heating.** Both draw from the same meter and move in opposite
  directions by season, so together they hide the real relationship.
- **The steam a boiler makes isn't the same as steam sent to campus.**
  About X% of production goes to turbines for electricity instead of to
  campus - that's cogeneration, not waste. Following the steam bar by bar
  makes this visible.
- **The plant supplies about X% of campus electricity**, from gas
  turbines and steam turbines combined - not steam turbines alone.
- **A multi-week gas turbine outage exposed a single point of failure.**
  The heat-recovery units depend entirely on gas turbine exhaust; when
  both gas turbines went down, self-sufficiency dropped from X% to X%.

## Data quality notes (flagged, not silently fixed)

- One set of meters reads exactly zero for a summer stretch - likely a
  metering gap, not zero real load.
- One turbine carries a large share of turbine steam but has no
  generation meter.
- A production outage looks the same in the data whether it was planned
  maintenance or a failure - can't tell which from readings alone.
- The raw export has sensor error codes (text strings) in a number of
  readings across two tabs - converted to missing values, not
  interpolated.
- The electrical tab and asset run-state sensors only cover roughly the
  first half of the full date range.

Full details (still with placeholder numbers) in `data_decisions.md`.

## Tools

Python (pandas), SQL, Tableau.
