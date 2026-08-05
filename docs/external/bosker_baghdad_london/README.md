# Bosker, Buringh & van Zanden (2013) — "From Baghdad to London" city dataset

## Source
- Dataset page: https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/24747
  (Review of Economics and Statistics Dataverse, Harvard Dataverse)
- Files downloaded 2026-07-20 via the Dataverse API (`format=original` for the Stata file).

## Citation
Bosker, Maarten, Eltjo Buringh, and Jan Luiten van Zanden. 2013. "From Baghdad to London:
Unraveling Urban Development in Europe, the Middle East, and North Africa, 800–1800."
*Review of Economics and Statistics* 95 (4): 1418–1437.
Replication data: doi:10.7910/DVN/24747, Harvard Dataverse.

## License
CC0 1.0 (Dataverse standard terms; no additional terms of use recorded).

## Files
| File | Description |
|---|---|
| `bagdad_london_final_restat.dta` | Main dataset (Stata; verified readable with pandas 2.2.3 `read_stata`) |
| `baghdad_london_dofile.do` | Authors' do-file generating all results in the paper |
| `variable_description.pdf` | Authors' variable descriptions (5 pp.) |

## Structure
- **8,723 rows × 69 columns**: unbalanced city × century panel.
- **792 cities**, **40 countries** (Europe + Middle East/North Africa), years
  **800, 900, …, 1800** (century observations).
- Key columns:
  - IDs/geography: `indicator`, `city`, `country`, `year`, `latitude`, `longitude`,
    `elevation_m`, `rugg10`, `soilquality`, `ecozones`, `arab_peninsula`, `me_na`
  - Population: `citypop_le10` (population in 1,000s, 10k threshold), `citypop_le5` (5k threshold),
    `total_pop_country`
  - Institutions: `commune`, `capital`, `bishop`, `archbishop`, `university`, `plundered`,
    `muslim`, `muslim_holy_city`, `free_prince_dls` (De Long–Shleifer free city/prince
    classification!)
  - Transport/geography: `sea`, `river`, `hub_3rr`, `rom_road_nohub`, `caravan_hub`,
    `caravan_nohub`
  - Urban-potential / spatial-lag variables: `fup`, `musfup`, `chrfup`, distance and
    nearest-city variables (`d*`, `nrcities_*`, `citypop_le10_0_20`, …).

## Notes
- This dataset embeds Bairoch-style city populations for Europe plus the authors' own
  MENA city population estimates — so a separate Bairoch download (target 8) is redundant.
- `free_prince_dls` provides a machine-readable version of the De Long & Shleifer (1993)
  "Princes and Merchants" regime classification at the city level.
