# Sound Toll Registers data

This directory holds the Sound Toll Registers Online (STRO) dataset used by
the analysis scripts in this repository.

## Source

Sound Toll Registers Online — a joint project of the University of Groningen
and the Tresoar archive (Leeuwarden, NL):

- Project website: https://www.soundtoll.nl/
- The full STRO dataset is distributed by the project; access typically
  requires (free) registration on the project site.

If you are an academic reviewer and have trouble obtaining the bulk CSVs
through the project, contact the repository owner and we can arrange a
copy for review purposes.

## Files

Three of the bulk CSVs exceed GitHub's 100 MB file size limit and are
**not committed to this repository**. To reproduce the analysis, download
them from STRO and place them in this directory:

| File              | Size   | Tracked in git? |
| ----------------- | ------ | --------------- |
| `belastingen.csv` | ~152 MB | no  — download separately |
| `doorvaarten.csv` | ~379 MB | no  — download separately |
| `ladingen.csv`    | ~419 MB | no  — download separately |
| `currency.csv`           | 2.9 KB  | yes |
| `maten.csv`              | 332 KB  | yes |
| `registers_totaal.csv`   | 94 KB   | yes |
| `secties_totaal.csv`     | 449 KB  | yes |
| `stro_tables.pdf`        | 489 KB  | yes — schema reference |

`stro_tables.pdf` documents the table/column schema for all of the above.

## Citation

When using this data in academic work, cite STRO per the project's guidance
on https://www.soundtoll.nl/. A standard form is:

> Sound Toll Registers Online (STRO), University of Groningen / Tresoar,
> https://www.soundtoll.nl/, accessed [date].
