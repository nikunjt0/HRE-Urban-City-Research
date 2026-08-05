# Storm from the Steppes — Eurasian rulers/dynasties 1000–1799 (substitute for Blaydes & Chaney 2013)

## Why this is here
The actual Blaydes & Chaney (2013) "The Feudal Revolution and Europe's Rise" (APSR)
ruler-duration replication files are **not publicly downloadable** (see ../MISSING.md).
This dataset is the closest public, machine-readable ruler-level panel covering both
European and Islamic-world (plus wider Eurasian) polities with ruler duration and
deposition — it explicitly builds on/extends the Blaydes–Chaney research design.

## Source
- Harvard Dataverse doi:10.7910/DVN/D1XSBR — "Replication Data for: Storm from the
  Steppes: Warfare and Succession Institutions in Pre-Modern Eurasia, 1000–1799 CE"
  (APSR, 2025). Downloaded 2026-07-20 via Dataverse API (`format=original` → CSV).

## Citation
See `README_authors.txt` (the authors' own README from the deposit) for the exact
citation of the APSR 2025 article and dataset doi:10.7910/DVN/D1XSBR.

## License
CC BY 4.0.

## Files & structure (CSV, latin-1 encoded — NOT utf-8)
| File | Rows × Cols | Unit |
|---|---|---|
| `Eurasian_Rulers_1000_1799.csv` | 3,015 × 24 | ruler (reign) |
| `Eurasian_Dynasties_1000_1799.csv` | 311 × 30 | dynasty |
| `Eurasian_Polity_Century_1000_1800.csv` | 719 × 14 | polity × century |
| `Storm_Replication_Code.R` | — | authors' replication code |

Key ruler-level columns: `polity_name`, `truhart_id`, `dynasty`, `ruler`, `start_year`,
`end_year`, `duration`, `deposed`, `dynastic_order`, `son`, `father_to_son`,
`parliament`, `military_slave_corps` (mamluk-style corps — the Blaydes–Chaney mechanism),
`IACW` (Inner-Asian conquest-wave polity), core coordinates and region.

## Caveats
- Read with `encoding="latin-1"` in pandas (0x92 smart quotes in ruler names).
- Coverage starts at 1000 CE (Blaydes–Chaney went back to 700 CE) and spans all of
  Eurasia, not just Europe vs. Islamic world — filter on `core_region`.
