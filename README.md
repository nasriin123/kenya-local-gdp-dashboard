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

- `data/kenya_adm1_county_year.gpkg`: county-year panel with geometry
- `data/kenya_adm1_county_year.csv`: same panel without geometry
- `data/kenya_adm0_national_year.csv`: national annual series
- `data/verification_totals.csv`: aggregation verification
- `data/kenya_grid_year_with_county.*`: optional grid-level outputs

## Deployment

Upload the extracted folder to a public GitHub repository, then deploy `app.py` through Streamlit Community Cloud.
