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

---
Attempts made 2026-08-10 (privilege-coverage / plague data sweep for the city-growth paper).

## Jedwab, Johnson & Koyama (2022 JEL) — city-level Black Death mortality (274 cities)
**Status: exists but requires (free) openICPSR account.**
- openICPSR project 120682, DOI 10.3886/E120682V1. The file
  `Replication Files/Figure-1/cities274.xls` is the city-level cumulative
  1347–1352 mortality dataset (digitized from Christakos et al. 2005).
- Anonymous download returns 403; log in with a free ICPSR account and fetch
  https://www.openicpsr.org/openicpsr/project/120682/version/V1/view
- Substitute acquired: `plague_biraben/` (Krauer & Schmid) provides dated
  plague ARRIVAL records; JJK provides mortality INTENSITY — complementary,
  worth getting if the port-entry mechanism test is pursued seriously.

## Stasavage (2014 APSR) "Was Weber Right?" — urban autonomy dates, ~170 cities
**Status: not publicly deposited** (2014 APSR predates mandatory Dataverse).
No Dataverse deposit found; Cambridge Core has appendix PDF only. The autonomy
list draws on Bosker et al.'s `commune` variable (which we hold) — the marginal
value over `commune` is modest. Email author if the exact coding is needed.

## Guiso, Sapienza & Zingales "Long-Term Persistence" (JEEA 2016) — Italian communes
**Status: not verified downloadable.** NBER w14278 / SSRN pages carry no data
file; JEEA supplementary may require subscription. Bosker `commune` covers 57
Italian cities in our matched panel; GSZ would add commune status for smaller
towns. Low priority.

## Not usable as tabular privilege data (checked, flagged)
- Österreichischer Städteatlas: 64 Austrian towns, scanned map folders on
  mapire.eu — no structured charter/privilege table.
- Engel, "Digital Atlas of Medieval Hungary" (Engel2020.zip, abtk.hu): >23,000
  settlements with legal-status TYPE (city/market town) but as a c.1500 static
  cross-section inside a proprietary GIS executable — no dated grants.
- Atlas Fontium (data.atlasfontium.pl, Poland): open GeoNode layer "Miasta,
  AHP XVI w." = static 1550–1600 town gazetteer with locality type; useful as a
  Poland control/gazetteer, NOT dated lokacja/charter events. (A dated Polish
  Magdeburg-law charter dataset was not found in machine-readable form.)
- Geovistory portal: SPARQL-only access, and does NOT host the CoMOR fairs
  data despite citations suggesting it.
- Staple rights south of the Viabundus network: no machine-readable dataset
  found anywhere — the staple analysis remains honestly bounded to the
  Viabundus footprint.
