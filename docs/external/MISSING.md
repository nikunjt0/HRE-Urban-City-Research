# Datasets not obtained (and why)

Attempts made 2026-07-20.

## Blaydes & Chaney (2013) "The Feudal Revolution and Europe's Rise" (APSR) — ruler duration data
**Status: not publicly downloadable.**
- No deposit on Harvard Dataverse (searched "Blaydes", "Chaney", "Feudal Revolution";
  Blaydes has 7 datasets there, none for this paper — APSR did not require deposits in 2013).
- Cambridge Core supplementary material is only a 152 KB PDF appendix.
- Eric Chaney's Google Sites publications page links a "Replication" file at
  https://drive.google.com/file/d/0B3KR-Nt6eQwSbkFGUzl3eFMxcWs/view?usp=sharing — the
  Drive file returns 401/Google sign-in for anonymous access (legacy `0B…` file id that
  now requires a `resourcekey`; none is embedded in the page HTML).
- Wayback Machine has no capture of the file; scholar.harvard.edu/chaney only archived PDFs.
- Lisa Blaydes' Stanford research page has no data links.
- **Substitute acquired**: `storm_steppes_rulers/` (APSR 2025 "Storm from the Steppes",
  CC BY 4.0) — ruler-level duration/deposition for European + Islamic + wider Eurasian
  polities 1000–1799, includes the `military_slave_corps` (mamlukism) variable central to
  Blaydes–Chaney. If the exact 700–1500 Blaydes–Chaney series is needed, email the authors
  or hand-code from Bosworth/Morby as they did.

## Kokkonen & Sundell (2014) original APSR replication files
**Status: never publicly deposited** (2014 APSR predates mandatory Dataverse deposits).
Tried: Harvard Dataverse (incl. APSR dataverse), Cambridge Core (PDF appendix only,
downloaded), QoG/University of Gothenburg pages, author sites/GitHub.
**Substitute acquired**: `kokkonen_sundell_monarchs/` — the same team's monarch database
as released with their 2020 JOP paper (monarch×year, 1000–1799, deposition/tenure/
succession/primogeniture), plus the K&S primogeniture country panel redistributed in the
"Tilly Goes to Church" archive. This is a superset of the 2014 variables for practical use.

## De Long & Shleifer (1993) "Princes and Merchants" regime classification
**Status: no machine-readable first-party version exists** (1993 JLE paper; tables only).
Searched NBER w4274, SSRN, Shleifer's Harvard page, DeLong's site, general web.
**Partial coverage**: the Bosker et al. dataset (`bosker_baghdad_london/
bagdad_london_final_restat.dta`) contains `free_prince_dls` — the De Long–Shleifer
free-city/prince classification mapped to the city×century panel. Hand-code from the
paper's tables only if the original region×period version is needed.

## Stasavage "States of Credit" city-state autonomy dataset
**Status: not publicly available.** The book (Princeton UP 2011) has no online replication
archive; nothing on Harvard Dataverse (his 10 deposits there are other papers), nothing on
his archived NYU pages (Wayback) or current sites. The city autonomy dates (used also in
"When Distance Mattered", APSR 2010) would have to be requested from the author or
hand-coded from the book's appendix.

## Bairoch, Batou & Chèvre city populations
**Status: deliberately skipped.** The Bosker et al. .dta already contains the city
populations (`citypop_le10`/`citypop_le5`) for Europe + MENA, and the repo already has
machine-readable Bairoch 1988 data at `docs/bairoch_pop_data/bairoch-1988.csv` and
`bairoch-1988-tidy.csv`.

## Buringh (2021) European urban population database 700–2000
**Status: not missing — already in the repo** at
`docs/European_Population_data_Buringh/` (xlsx/ods/txt + Annex A/B PDFs + MANIFEST.TXT,
an IISH/DANS-style deposit). Not re-downloaded.
