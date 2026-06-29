# `raw/` — Knowledge Base Staging

This directory is the staging area for raw source material that will be
compiled into the canonical knowledge base at
`../hxgtm-mcp-server/context/`.

Raw files live here temporarily while `/kb-update` diffs them against
canon and stages findings in Notion for team triage. Each file is owned
by a **group** that maps to a specific slice of the canonical KB and a
specific codeowner. (kb-lint does NOT read this directory — it audits
canon only.)

## Groups

| Slug | Label | Codeowner | Active |
|---|---|---|---|
| `competitive` | Competitive Intelligence | Product Marketing | yes |
| `messaging` | Product & Segment Messaging | Product Marketing | yes |
| `audiences` | Audiences & Personas | Product Marketing | yes |
| `company-policies` | Company Policies & Platform Commitments | Product Marketing | yes |
| `company-overview` | Company Overview & Narrative | CMO | yes |
| `marketing-strategy` | Marketing Strategy | CMO | yes |
| `brand-voice` | Brand, Voice & Positioning | CMO | yes |
| `channel-playbooks` | Channel Playbooks | CMO | yes |
| `sales-methodology` | Sales Methodology | Sales Enablement + Product Marketing | yes |
| `accounts` | Account & Opp-level Context | RevOps | yes |
| `rfp` | RFP Responses | Solutions Engineering | yes |

The source of truth for group → canon + raw path mapping is
[.claude/skills/kb-update/config.yaml](../.claude/skills/kb-update/config.yaml)
(its `raw:` staging paths live there; the `canon` globs are mirrored in
[.claude/skills/kb-lint/config.yaml](../.claude/skills/kb-lint/config.yaml)).
All 11 groups are active — any group can be processed directly via
`/kb-update --group <slug>` without the `--force` escape hatch.

## Folder layout

Each group folder has the same 5 source-type subfolders plus an `INDEX.md`:

```
raw/<group>/
├── INDEX.md         # ingest tracking (per-group)
├── notions/         # Notion page exports
├── transcripts/     # Gong / meeting transcripts
├── clippings/       # Web clippings
├── teams-chats/     # Teams / Slack conversations
└── deep-research/   # Perplexity / web research outputs
```

Drop a raw file into the appropriate `raw/<group>/<source-type>/` folder
and add a row for it in `raw/<group>/INDEX.md`.

## What goes into git

**Only the manifest and the folder skeleton. Raw source files stay
local, always.**

| Tracked in git | Never tracked in git |
|---|---|
| `raw/README.md` | `raw/*/notions/**/*.md` |
| `raw/<group>/INDEX.md` | `raw/*/transcripts/**/*.md` |
| `raw/<group>/<source-type>/.gitkeep` | `raw/*/clippings/**/*.md` |
|  | `raw/*/teams-chats/**/*.md` |
|  | `raw/*/deep-research/**/*.md` |

`.gitignore` at the repo root enforces this — every `.md` file under
any group's source-type subfolder is silently ignored. The only raw
file that can be pushed is `INDEX.md`.

### How tracking works

1. A maintainer drops `raw/competitive/notions/acme-pricing.md` onto
   their laptop.
2. They add a row to [raw/competitive/INDEX.md](competitive/INDEX.md):
   `| notions/acme-pricing.md | 2026-04-15 | | yes |`
3. They run `/kb-update --group competitive`. kb-update reads
   `acme-pricing.md` from the local disk, diffs it against canon,
   publishes findings to Notion, and stamps the `Last processed` column.
4. When the maintainer commits + pushes, only the INDEX.md change goes
   to origin. `acme-pricing.md` itself stays on their laptop.
5. If the maintainer later deletes `acme-pricing.md` locally (e.g.
   because they compiled it into canon), the INDEX row stays as the
   historical record "this file was ingested on 2026-04-15 and last
   processed on 2026-04-15". kb-update does NOT remove historical rows.

The net effect: master git has a permanent audit trail of every raw
file that was ever ingested, per group, without any of the private
source content. Exactly what the original brief asked for.

## Per-group visibility (sparse-checkout)

Each codeowner should only see their own group's `raw/` folder in their
working tree — it keeps the IDE uncluttered and prevents accidental
cross-group commits. After cloning the repo, run the setup script once:

```bash
scripts/kb-group-init.sh competitive   # replace with your group slug
```

The script configures [git sparse-checkout](https://git-scm.com/docs/git-sparse-checkout)
in cone mode so only `raw/<your-group>/` is materialized on disk. The
other 10 group folders disappear from your working tree (but remain in
git history, so `git log`/`git show` still work).

**Switching groups later:** re-run the script with a different slug.
**Undoing entirely:** `git sparse-checkout disable` restores the full tree.

### Caveats

- **Convention, not access control.** Sparse-checkout is a local view
  filter. Anyone can run `git sparse-checkout disable` to see
  everything. Use GitHub team permissions on a separate repo if you
  need real access control.
- **Fresh clones default to full checkout.** Each codeowner must run
  the script manually after their first clone.
- **History is preserved.** Files that are already in commits remain
  accessible via `git log` / `git show` regardless of sparse-checkout.
  Sparse-checkout only controls what's materialized on disk, not what
  lives in `.git/`.

## Running kb-update against a group

Raw sources in this directory are processed by `/kb-update`, which
requires an explicit `--group` flag:

```
/kb-update --group competitive
/kb-update --list-groups
```

See [.claude/skills/kb-update/README.md](../.claude/skills/kb-update/README.md) for full usage.

For a read-only health audit of canon itself (no raw sources), use
`/kb-lint --group <slug>` — see
[.claude/skills/kb-lint/README.md](../.claude/skills/kb-lint/README.md).
