# Kenya Local GDP Explorer

A Streamlit dashboard for exploring 0.5-degree predicted local GDP aggregated to Kenya's 47 ADM1 counties over 2012–2021.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Data coverage

- 47 counties retained
- 10 years (2012–2021)
- 470 county-year rows
- 60 county-year rows are missing because six counties receive no 0.5-degree grid centroid
- Missing estimates are retained as missing, not replaced with zero

## Files

- `data/kenya_adm1_county_year.csv`: county-year GDP and population panel
- `data/kenya_county_boundaries.geojson`: Kenya ADM1 county boundaries
- `data/kenya_adm0_national_year.csv`: national annual series
- `data/verification_totals.csv`: aggregation verification
- `data/kenya_grid_year_with_county.csv`: optional grid-level output

## Deployment

Upload the extracted folder to a public GitHub repository, then deploy `app.py` through Streamlit Community Cloud.
