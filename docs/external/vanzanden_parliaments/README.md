# Van Zanden, Buringh & Bosker — European parliaments, 1188–1789 (activity index)

## Source
- Machine-readable version obtained **secondhand** from the replication archive of:
  Grzymala-Busse, Anna. 2023. "Tilly Goes to Church: The Religious and Medieval Roots of
  European State Fragmentation." *APSR*. Harvard Dataverse doi:10.7910/DVN/DWQLIB,
  file `parliamentsVBB.tab` (downloaded 2026-07-20 via Dataverse API, `format=original`
  → Stata file, renamed `parliamentsVBB.dta`).
- The **original** publication's data appendix (Appendix S1) is only distributed as a PDF
  supplement behind Wiley's paywall (403 for anonymous download); no first-party
  machine-readable deposit was found (checked Harvard Dataverse, CGEH/cgeh.nl incl.
  Wayback Machine, CEPR DP7809/SSRN).

## Citation
Van Zanden, Jan Luiten, Eltjo Buringh, and Maarten Bosker. 2012. "The Rise and Decline of
European Parliaments, 1188–1789." *Economic History Review* 65 (3): 835–861.
Cite also the redistribution source: Grzymala-Busse 2023, doi:10.7910/DVN/DWQLIB.

## License
The Dataverse deposit it was taken from is CC0 1.0. Underlying index constructed by
van Zanden/Buringh/Bosker — cite the 2012 EHR article.

## Structure — `parliamentsVBB.dta`
- **6,787 rows × 7 columns**: city × century panel, years **800–1800** (century steps).
- **618 cities**, **20 countries** (western/Latin Europe).
- Columns: `country`, `city`, `year`, `lon`, `lat`, `parliament` (0/1 dummy: parliament
  active in the city's polity), `parl_ai` (parliament activity index — share of years the
  polity's parliament was in session per century, scaled ~0–100).
- Verified readable with pandas `read_stata`.

## Caveats
- **One corrupt value**: a single row has `parl_ai` = 1,931,488,360 (year 1500) —
  clearly a coding error in the redistributed file. Filter `parl_ai > 100` before use.
- This is the country-level activity index broadcast onto cities; for country×period
  analysis, collapse by `country`×`year`.
