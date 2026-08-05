# Kokkonen & Sundell — European monarchs, succession and survival

Target was the replication data for:
Kokkonen, Andrej, and Anders Sundell. 2014. "Delivering Stability—Primogeniture and
Autocratic Survival in European Monarchies 1000–1800." *APSR* 108 (2): 438–453.

**The original 2014 APSR dataset was never publicly deposited** (nothing on Harvard
Dataverse/APSR Dataverse; Cambridge Core only hosts a PDF appendix; nothing on QoG/GU
or author sites). This directory therefore contains the closest public releases of the
same underlying monarch database (same team, extended coverage), plus the 2014 appendix.

## Files

### 1. `bloodisthicker_data.dta` (+ `bloodisthicker_dofile.do`, `data_description.pdf`, `appendix.pdf`)
- Source: Sundell, Anders; Kokkonen, Andrej; Møller, Jørgen; Krishnarajan, Suthan. 2020.
  "Replication Data for: Blood is Thicker than Water: Family Size and Leader Deposition
  in Medieval and Early Modern Europe" (*Journal of Politics*). Harvard Dataverse
  doi:10.7910/DVN/M2E5OI (JOP Dataverse). Downloaded 2026-07-20, `format=original`.
- License: CC0 1.0.
- Structure: **13,823 rows × 462 columns** — monarch × year panel, **1000–1799**,
  **693 monarchs**, **27 countries**. Verified readable with pandas `read_stata`
  (Stata release 118 file).
- Key columns: `id_monarch`, `id_reign`, `country`, `year`, `name`, `monarch_house`,
  `order` (succession order), `primogeniture`, `ascension`, `descension`, `tenure_final`,
  `tenure_rolling`, `deposed_our`, `deposed_dow`, `deposedcat_perp`, `deposedcat_succ`,
  `naturaldeath`, `monarch_queen`, `dum_illegitimate`, family-size variables
  (`children_*`, `family_all`, `son_born`, …), plus controls incl. `zanden_parliaments`.
  Many of the 462 columns are lags/leads and robustness recodes — see `data_description.pdf`.

### 2. `primogenitureKS.dta`
- The Kokkonen–Sundell primogeniture coding (country × 5-year, **1100–1815**, 39 countries;
  2,995 rows × 4 cols: `Name`, `year`, `KS_country`, `KS_primogeniture`), as redistributed
  in the Grzymala-Busse "Tilly Goes to Church" APSR replication archive
  (doi:10.7910/DVN/DWQLIB, CC0, file `primogenitureKS.tab`, original format).

### 3. `kokkonen_sundell_2014_supplementary.pdf`
- The official APSR 2014 supplementary material (country list, coding notes, robustness):
  https://static.cambridge.org/content/id/urn:cambridge.org:id:article:S000305541400015X/resource/name/S000305541400015Xsup001.pdf

## Citation
For any use of the monarch-level data cite Kokkonen & Sundell (2014, APSR) and
Kokkonen, Krishnarajan, Møller & Sundell (2020, JOP, doi:10.7910/DVN/M2E5OI).
