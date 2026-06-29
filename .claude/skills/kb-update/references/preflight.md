# kb-update — Pre-flight (detailed flow)

## Contents
- When this reference is loaded
- Happy-path outline (already in SKILL.md)
- 2a — MCP path resolution
- 2b — Canon access (always filesystem)
- 2c — Notion data source auto-resolution
- Auto-reconcile (cache-miss path)
- Landing-page guardrail

## When this reference is loaded

Read this reference file when the happy path in SKILL.md Step 2 is
insufficient — specifically:

- The Notion data source resolver returns `"source": "missing"`
  (exit 1 from `resolve-notion-id`) and the orchestrator needs the
  detailed auto-reconcile flow (`notion-search` → create-database).

On a healthy happy-path run, SKILL.md Step 2 completes without reading
this file. Database-level health (trashed, wrong-parent, schema drift,
stale ID, missing SELECT options) is **not** checked pre-flight —
those errors surface at publish time in Step 6 where they are healed
reactively. See [publish.md](publish.md) for the reactive repair flows.

## Happy-path outline (already in SKILL.md)

Summarised here for context. The full text lives in SKILL.md Step 2;
this reference only expands the failure paths.

1. Load group config from `config.yaml`; halt on unknown group or
   inactive group without `--force`.
2. 2a: Resolve MCP path via `resolve_mcp_path.py mcp-path`.
3. 2b: Set `canon_access_mode = filesystem`. No MCP probe.
4. 2c: Resolve Notion data source ID via `resolve-notion-id --group <slug>`.
   Cache hit (env / `.kb-local.json` / `config.yaml`) → proceed to Step 3.

No summary table, no Proceed prompt, no schema pre-check.

## 2a — MCP path resolution

```
python3 .claude/skills/kb-update/scripts/resolve_mcp_path.py mcp-path
```

Returns JSON with `path`, `source`, `cached`, `duration_ms`. Surface
stderr verbatim on halt. Record the resolved path as `mcp_root` for
use in 2b and downstream steps.

## 2b — Canon access (always filesystem)

Canon lives in the local `hxgtm-mcp-server` clone on disk — that's
where `kb-integrate` writes, so kb-update reads from the same place.
No `ListMcpResourcesTool` probe, no MCP-vs-filesystem branching.

Set `canon_access_mode = filesystem` and use `<mcp_root>/context/` as
the canon root. Count `.md` files under `<mcp_root>/context/` as
`canon_file_count` for reporting.

## 2c — Notion data source auto-resolution

Run:

```
python3 .claude/skills/kb-update/scripts/resolve_mcp_path.py \
    resolve-notion-id --group <slug>
```

**Exit 0 — use ID directly, no Notion fetch.** Zero Notion calls on
happy path. The cache's job is to avoid a redundant fetch against a
database that's correct >99% of the time; Step 6's publish-time retry
is the safety net for the rare stale-cache case.

**Exit 1 — ID missing from every cache layer.** Enter auto-reconcile.

### Auto-reconcile (cache-miss path)

1. Call `notion-search` for query `"KB - Updates Review"`,
   `query_type: "internal"`, `page_size: 5`. Filter to exact-title
   matches with no `deleted` attribute.

2. **Landing page not found** → halt with the [landing-page banner](#landing-page-guardrail).

3. **Landing page found + group's database exists as a child** (the
   fetched page response carries a `<database data-source-url="collection://UUID">`
   child with the expected title `KB - <Group Label>` and no `deleted`
   attribute) — write the UUID:

   ```
   python3 .claude/skills/kb-update/scripts/resolve_mcp_path.py \
       write-notion-id --group <slug> --id <uuid>
   ```

   Also update `config.yaml` via the Edit tool so shared repo clones
   pick up the canonical value. Record `notion_data_source_id = <uuid>`
   and continue to Step 3.

4. **Landing page found + group's database missing** — auto-create it
   via the single source of truth for the create-database recipe:

   ```bash
   python3 .claude/skills/kb-update/scripts/setup_notion.py \
       --plan --group <slug> --landing-page-id <landing_page_id>
   ```

   The response's `databases[0]` carries `title`, `description`,
   `schema`, and `default_view_config`. Call
   `mcp__claude_ai_Notion__notion-create-database` with `parent =
   {"type": "page_id", "page_id": "<landing_page_id>"}` and the
   first three fields verbatim. Capture the `collection://UUID` from
   the response.

   Configure the database's built-in default view (auto-created by
   `notion-create-database` — no separate view) via a single
   `notion-update-view` call using `databases[0].default_view_config`.
   Pass `filter`, `group_by`, `sort`, `visible_columns`, and
   `hidden_columns` verbatim.

   Write the UUID to both `.kb-local.json` (via `write-notion-id`) and
   `config.yaml` (via Edit tool). Continue to Step 3. SELECT options
   (Entity) are seeded reactively at publish time — see
   [publish.md](publish.md).

**Any failure during auto-reconcile** (notion-search error,
create-database failure) flows through the reactive-repair paths in
[publish.md](publish.md) — specifically §3 for DB-presence issues
and §5 for the genuine human-halt cases (missing landing page,
unauthorized integration, schema repair convergence failure). Do
NOT surface `/kb-update --notion-setup` as a manual recovery path —
the same auto-provisioning flow is invoked inline from §3b / §3c
when the cache miss is reached here at pre-flight.

No partial state: if the DB was created but the cache write failed,
the next run's resolver hits the cache-miss path and re-runs this
flow which writes the cache correctly.

### Landing-page guardrail

```
⚠️  KB - Updates Review landing page not found in Notion.

Create a new page titled exactly:
  KB - Updates Review
at the teamspace where your team should triage findings, then
re-run /kb-update — it will discover the page, create the 11
per-group databases as children, and cache the IDs automatically.
No other manual step required.
```

Exit the skill after printing. Do NOT proceed to Step 3.
