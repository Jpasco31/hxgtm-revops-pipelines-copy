# Competitive Intelligence — Raw Source Index

Ingest tracking for the **Competitive Intelligence** group. Owned by
**Competitive Intelligence**.

Each row represents a raw source file staged under `raw/competitive/`. This
index tracks when files arrived, when kb-update last processed them, and whether
kb-update should process them at all. It does **not** track review status — use
`Process? = no` to exclude a file from processing without removing it.

## Columns

| Column             | Meaning                                                                                     |
| ------------------ | ------------------------------------------------------------------------------------------- |
| **File**           | Path relative to `raw/competitive/` (e.g. `notions/foo.md`)                                 |
| **Added**          | ISO date (YYYY-MM-DD) the file was dropped into this folder                                 |
| **Last processed** | ISO date kb-update last included this file in a raw→canon comparison. Blank = never processed |
| **Process?**       | `yes` = kb-update considers this file. `no` = reference only, skip during comparison          |

## Index

| File                                                      | Added      | Last processed | Process? |
| --------------------------------------------------------- | ---------- | -------------- | -------- |
| teams-chats/market-insights-competitor-scan-2026-04-09.md | 2026-04-09 | 2026-04-15     | yes      |