# Sales Methodology — Raw Source Index

Ingest tracking for the **Sales Methodology** group. Owned by
**Sales Methodology**.

Each row represents a raw source file staged under `raw/sales-methodology/`.
This index tracks when files arrived, when kb-update last processed them, and
whether kb-update should process them at all. It does **not** track review
status — use `Process? = no` to exclude a file from processing without removing it.

## Columns

| Column | Meaning |
|---|---|
| **File** | Path relative to `raw/sales-methodology/` (e.g. `notions/foo.md`) |
| **Added** | ISO date (YYYY-MM-DD) the file was dropped into this folder |
| **Last processed** | ISO date kb-update last included this file in a raw→canon comparison. Blank = never processed |
| **Process?** | `yes` = kb-update considers this file. `no` = reference only, skip during comparison |

## Index

| File | Added | Last processed | Process? |
|---|---|---|---|
| *(none yet)* | | | |
