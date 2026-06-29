# kb-update — Publish (Step 6 detail)

## Contents
- When this reference is loaded
- High-level invocation (already in SKILL.md)
- Reactive repair — guiding principle
- Reactive repair §1 — missing SELECT options
- Reactive repair §2 — schema drift (missing column)
- Reactive repair §3 — 404 / object_not_found (DB presence)
- Reactive repair §4 — transient failures (rate-limit, conflict, 5xx)
- Reactive repair §5 — permission / connector (human-halt cases)
- Partial batch failures
- Publisher invariants (Status / Reviewer / Final Updated Text)
- Zero-findings case
- Collecting the published page URL

## When this reference is loaded

Read this reference when the publish step encounters a failure path:
missing SELECT options (Entity / any SELECT), schema
drift (missing column), 404 on a stale DS ID, partial-batch failures,
or the zero-findings short-circuit.

## High-level invocation (already in SKILL.md)

1. Pipe the synthesis output into `publish_to_notion.py`:

   ```bash
   python3 .claude/skills/kb-update/scripts/publish_to_notion.py \
       --group <slug> \
       --run-date <YYYY-MM-DD> \
     < /tmp/kb-update-findings.json \
     > /tmp/kb-update-pages.json
   ```

   The script emits `{parent, pages, batches, stats}`. Log
   `stats.data_source_id` and `stats.warnings`.

2. For each batch in `batches` (each capped at 25 pages, default 10),
   call `mcp__claude_ai_Notion__notion-create-pages` with the batch's
   `parent` and `pages` fields verbatim. Wait for each call to return
   before starting the next.

3. Collect the URL from the first successful batch's response for the
   Step 7 summary.

## Reactive repair — guiding principle

kb-update does no pre-flight schema or health checks against Notion —
database-level problems surface here, at the first batch that fails,
and are healed in place. **The orchestrator heals every failure it
can through MCP tools without user intervention. Hard halts are
reserved for scenarios where the AI genuinely cannot make progress
through available tools** (missing landing page, uninstalled
connector, repeated workspace permission denial).

Retry cap across every reactive-repair path: **3 attempts total per
batch**. Exceeding the cap on a repair path flips to the human-halt
banner documented in §5.

### 1. Missing SELECT options (Entity / any SELECT)

Notion rejects `create-pages` calls that include an unknown SELECT
value on a SELECT that has zero matching options (validation error
`Invalid select value for property "<Name>": "<value>". Value must be
one of the following: .`).

**Detect** on a 400 mentioning `Invalid select value for property`.

**Fix — three steps, no shortcuts:**

1. **Fetch** the column's current option names. `notion-fetch` on the
   data source URL (`collection://<data_source_id>`) returns the schema;
   read `schema.<column>.options[].name`. Alternatively, any
   `notion-update-data-source` call echoes the full schema on success, so
   a recent response may already carry the list.
2. **Build** the DDL via the helper (enforces the two invariants below):

   ```
   python3 .claude/skills/kb-update/scripts/publish_to_notion.py \
       --build-select-ddl "Entity" \
       --existing "Federato,Convr,Kalepa,Send" \
       --values   "Artificial,Coherent,Competitors,Earnix,Federato,Mea,Sixfold"
   # => ALTER COLUMN "Entity" SET SELECT('Artificial', 'Coherent', 'Competitors', 'Convr', 'Earnix', 'Federato', 'Kalepa', 'Mea', 'Send', 'Sixfold')
   ```
3. **Apply** it:

   ```
   mcp__claude_ai_Notion__notion-update-data-source
     data_source_id: <uuid>
     statements: <output from step 2>
   ```

Retry the failed `create-pages` call. Repeat for every SELECT column
that surfaces the same error (a freshly-created DB typically trips at
least `Entity`). Retry cap: 3 total
attempts per batch; on the third attempt flip to §5 with the column
name and the DDL that failed to apply.

**Two invariants this path enforces — both learned the hard way:**

- **Never emit colors.** Notion rejects `SET SELECT` if any named
  option's color differs from what it was provisioned with (error:
  `Cannot update color of select with name: <X>`). The color-less form
  leaves every existing option's color untouched and auto-assigns
  defaults to new options. `setup_notion.py` is the single source of
  color assignment; reactive repair must not re-color.
- **Always union with existing options.** `SET SELECT` has replace-set
  semantics. Passing only the current run's values would drop any
  option a reviewer added directly in Notion since the last run, and
  empty every historical row that referenced it. The helper above
  merges `existing` ∪ `values` and sorts the result.

### 2. Schema drift — missing column

Notion rejects `create-pages` calls that reference a property the
database doesn't have. This happens when `EXPECTED_COLUMNS` in
`publish_to_notion.py` gained new columns since the live DB was last
provisioned (typical error: `property does not exist` /
`Unknown property` / `property "<X>" not found`).

**Detect** on a 400 mentioning `property does not exist` (or the
`Unknown property` / `not found` variants).

**Fix** by adding every missing column via `notion-update-data-source`.
Source the per-column DDL fragments from `COLUMN_DDL` — fetch them
once by running:

```
python3 .claude/skills/kb-update/scripts/publish_to_notion.py \
    --check-schema --group <slug>
```

The JSON response includes `column_ddl` (keyed by column name).
Compose one `ADD COLUMN "<Name>" <ddl>` per missing column,
semicolon-separated:

```
mcp__claude_ai_Notion__notion-update-data-source
  data_source_id: <uuid>
  statements: ADD COLUMN "Target Line Start" NUMBER; ADD COLUMN "Target Line End" NUMBER; ADD COLUMN "Closes Open Question" RICH_TEXT
```

Retry the failed `create-pages` call. If the same 400 fires again
(second attempt), **do NOT halt** — the first `ADD COLUMN` may have
partially applied or raced with a concurrent schema write. Recover
automatically:

1. Re-fetch live schema via `notion-fetch collection://<ds>`.
2. Diff the returned schema against `EXPECTED_COLUMNS` (from
   `publish_to_notion.py --check-schema`).
3. Compose a fresh `ADD COLUMN` batch for any column still missing
   and call `notion-update-data-source` once more.
4. Retry `create-pages` one final time.

If the third attempt still reports the same missing column, flip to
§5 and surface the exact DDL the user can run by hand — this
indicates a Notion API inconsistency the MCP tool cannot resolve in
this session, not a user configuration issue.

### 3. 404 / object_not_found (DB presence)

The cached / configured data source ID points at a database that no
longer exists, was trashed, or moved out from under us since the last
successful run. kb-update **auto-heals this in place — the orchestrator
never asks the user to re-run `/kb-update --notion-setup`.**

**Detect** on a batch call returning 404 or `object_not_found`.
(`unauthorized` flows through §5 instead — it's a permission issue,
not a presence issue.)

**Recover** — three sub-cases dispatched by the state of
`KB - Updates Review` in Notion:

#### 3a. Cache-stale, but the group's DB exists

The DB is alive under `KB - Updates Review` but the cached UUID is
wrong (rare; happens after manual Notion admin work).

1. `notion-search` with `query: "KB - Updates Review", query_type:
   "internal"`.  Landing page missing → §5 (human halt).
2. `notion-fetch <landing_page_id>`. Enumerate `<data-source
   url="collection://UUID">` children. Match on exact title
   `KB - <Group Label>` with no `deleted` attribute.
3. Match found →
   `python3 .claude/skills/kb-update/scripts/resolve_mcp_path.py write-notion-id
   --group <slug> --id <uuid>` and Edit `config.yaml` to set
   `groups.<slug>.notion_data_source_id`.
4. Retry the failed batch against the new DS ID.

#### 3b. Group's DB is missing under the landing page

Landing page exists and has *some* children but not this group's DB —
for example, one DB was trashed while the other 10 are healthy.

1. Discover the landing page ID as in 3a.
2. Emit a single-group plan:
   ```
   python3 .claude/skills/kb-update/scripts/setup_notion.py \
       --plan --group <slug> --landing-page-id <landing_page_id>
   ```
   The returned `databases[0]` spec carries `title`, `description`,
   `schema`, and `default_view_config`. This is the CLI hook added for
   reactive repair — `--group` forces planning even if `config.yaml`
   already has a (stale) UUID.
3. `notion-create-database` with `parent={"type": "page_id",
   "page_id": <landing_page_id>}`, `title`, `description`, and
   `schema` from the spec. Capture the new `collection://UUID`.
4. Configure the database's built-in default view (auto-created by
   `notion-create-database` — no separate view) via a single
   `notion-update-view` call using `databases[0].default_view_config`.
   Pass `filter`, `group_by`, `sort`, `visible_columns`, and
   `hidden_columns` verbatim.
5. `write-notion-id --group <slug> --id <uuid>` + Edit `config.yaml`.
6. Retry the failed batch against the new DS ID.

#### 3c. Landing page is blank (zero child DBs)

Landing page exists but has been fully emptied — every per-group DB
has been trashed. Semantically identical to "all 11 groups missing",
which is what `--notion-setup` was designed to fix. Re-provision the
full set inline:

1. Discover the landing page ID as in 3a. Call `notion-fetch` and
   confirm zero `<data-source>` children (or strictly fewer than the
   count of configured groups).
2. Emit the full bulk plan (no `--group` filter):
   ```
   python3 .claude/skills/kb-update/scripts/setup_notion.py \
       --plan --landing-page-id <landing_page_id>
   ```
   `databases` contains one entry per group whose `config.yaml`
   `notion_data_source_id` is blank. If every group still has an ID
   in `config.yaml` (typical — config out of sync with Notion), rerun
   the command once per group with `--group <slug>`, unioning the
   resulting `databases[0]` specs.
3. For each spec: `notion-create-database` + `notion-update-view`
   on the default view using `default_view_config` + `write-notion-id`
   + Edit `config.yaml` (same loop as 3b). Process groups serially to
   keep error attribution clean.
4. Retry the failed batch for the active group against its new DS ID.
   Other groups now have fresh UUIDs cached and will hit the
   fast-path on their next run.

**Retry cap:** at most 3 total `create-pages` attempts per batch
across all three sub-cases. On the third 404/object_not_found, flip
to §5.

### 4. Transient failures (rate-limit, conflict, 5xx)

Notion occasionally returns `rate_limited` (429), `conflict_error`
(409 — usually racing schema writes), or 5xx. These are not
state-level issues; the batch payload is valid.

**Detect** on HTTP 429, 409, 500, 502, 503, or 504, or `code`
values `rate_limited`, `conflict_error`, `internal_server_error`,
`service_unavailable`.

**Recover** by auto-retrying the batch up to 3 times with 2s / 4s /
8s backoff. Log each attempt:
`[publish_retry] batch=<N> attempt=<K> code=<code> delay_ms=<ms>`.

If all 3 attempts fail, record the batch as failed and continue with
remaining batches — the overall run is not aborted by a single stuck
batch. The Step 7 report surfaces the transient error code so the
user can retry the whole skill if they want.

### 5. Permission / connector (human-halt cases)

The genuine human-action scenarios. Each emits a specific banner so
the user knows exactly what to do; none redirects to
`/kb-update --notion-setup`.

**Landing page `KB - Updates Review` not found in workspace**
(triggered from 3a/3b/3c when `notion-search` returns no exact-title
match):

> ⚠️  Landing page `KB - Updates Review` not found in this Notion
> workspace. The Notion MCP can only create pages in Private
> workspace, which is almost never where team databases belong.
>
> Create a page titled exactly `KB - Updates Review` at the
> teamspace where findings should live, then re-run `/kb-update`.
> The skill will discover the page, provision the 11 per-group
> databases as children automatically, and retry this run.

**Persistent `unauthorized` / 403 after DS re-discovery**
(any call returning `unauthorized` or 403, even after 3a succeeded
in finding the DB):

> ⚠️  Notion returned `unauthorized` for data source
> `<ds_id>` under integration `<integration_id>` (from the error
> body's `additional_data.integration_id`).
>
> Share the `KB - Updates Review` landing page (and all its child
> databases) with this integration, then re-run `/kb-update`. No
> other change needed.

**SELECT or schema repair failed 3 consecutive times**
(triggered from §1 or §2 after the third attempt still fails):

> ⚠️  Schema repair did not converge after 3 attempts. Last DDL:
>
>     notion-update-data-source
>       data_source_id: <ds_id>
>       statements: <verbatim DDL>
>
> Run this manually in Notion admin (Settings → Connections →
> `<integration_name>` → Open API), then re-run `/kb-update`.
> This is typically a Notion API consistency glitch, not a user
> config issue.

**Notion MCP connector missing in session** (triggered at pre-flight
Step 2d, before any comparators run):

> ⚠️  Notion MCP connector is not available in this Claude Code
> session — kb-update cannot publish findings without it.
>
> Install the Notion connector (Claude Code → Connectors → Notion)
> and re-run `/kb-update`. The file you uploaded will need to be
> re-attached since uploads are ephemeral.

## Partial batch failures

If a batch call fails with anything OTHER than the shapes covered in
§§ 1–4:

- Capture the error and `request_id` for Step 7.
- Continue with the remaining batches — a single weird 400 should
  not abort the whole run.
- Record the count of failed batches for Step 7.

Do not retry these non-classified errors — the user inspects the
Step 7 report and re-runs after resolving the root cause.

## Publisher invariants

The following invariants are structurally enforced by
`publish_to_notion.py`. The orchestrator MUST NOT override any of
them.

- **Status**: publisher writes `Pending Review` on new rows and never
  updates the column on existing rows. Humans transition through
  Approved / Rejected / Integrated during triage. `Needs Restage` is
  set by `kb-integrate` when canon has drifted since publish.

- **Reviewer**: publisher NEVER writes this column — humans tag
  themselves via the Notion UI during triage.

- **Final Updated Text**: publisher NEVER writes this column —
  reviewers type partial-approval tweaks here in the Notion UI.
  `kb-integrate` reads
  `effective_text = Final Updated Text or Proposed Updated Text` at
  apply time. If the publisher wrote to this column, it would
  silently overwrite reviewer edits on any republish.

## Zero-findings case

If Step 5 produced no findings, skip Step 6 entirely and report
"Upload matches canon — no conflicts to publish" in Step 7. Do not
create an empty Notion row.

## Collecting the published page URL

Each `notion-create-pages` response returns the created pages with
`id` and `url` fields. For the Step 7 summary:

- `View` URL — take the URL of the database itself (the parent of the
  rows). Format: `https://www.notion.so/<database_id_without_dashes>`
  where `database_id` is the database UUID (not the data source UUID).
  The orchestrator may need to call `notion-fetch` on the data source
  once to pull the database URL, or may already have it from the
  auto-reconcile step.

- `Data source` — print the data source UUID from
  `stats.data_source_id` for the operator's debugging.

- `Landing page` — the `KB - Updates Review` page URL, recovered from
  `.kb-local.json.notion_landing_page_id` or from the cache populated
  during auto-reconcile.
