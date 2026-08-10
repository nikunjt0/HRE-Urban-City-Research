# Krauer & Schmid — digitized Biraben & Sticker plague outbreak data

## Source
- Zenodo record: https://zenodo.org/records/6587267 (DOI 10.5281/zenodo.6587267;
  concept DOI 10.5281/zenodo.4724015). Downloaded plague.zip 2026-08-10, open access.
  (The v1.0 record 4724016 is RESTRICTED — use the latest version, which is open.)

## Citation
Krauer, Fabienne, and Boris V. Schmid. 2022. "Mapping the plague through natural
language processing." Epidemics / (data deposit, CC-BY). Digitizes Biraben (1975)
and Sticker (1908) plague outbreak inventories.

## Files kept (code/ and NLP intermediates from the zip retained under data/)
| File | Description |
|---|---|
| `data/plague_biraben_v1.csv` | 11,180 geocoded outbreak records, 1346–1900: name, YEAR (dated events), certain/status flags, country, lat/lon + bounding box, type (city vs admin unit) |
| `data/plague_sticker_v1.csv` | Sticker (1908) digitization, same structure |
| `data/plague_datadict.xlsx` | Variable dictionary |

## Relevance
City-level PLAGUE ARRIVAL dates. Black Death first wave 1347–1352: 413 records.
This is the dataset the paper's §7 caveat calls for: testing the port-entry
mechanism (did coastal cities suffer because plague arrived through harbors?)
with actual arrival dates instead of inference from century growth. Filter
type=="Place" for city-level rows; merge by lat/lon (bbox_diag_km gives
geocoding precision). Caveat: Roosen & Curtis (2018) document undercoverage in
Biraben's inventory (esp. Low Countries) — treat absence of an outbreak record
as weak evidence, mirror of our privilege-coverage discipline.

## Alternative copies
- Zenodo 14973 (Schmid et al. 2015 PNAS deposit) has an earlier merged
  Biraben digitization (7,711 records, 1339–1900) inside
  europe-pnas/resources/plague-db-europe.txt (EDN format).
