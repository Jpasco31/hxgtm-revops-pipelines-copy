# Perkins Playbook — Routine Prompt

> Runtime prompt for the Perkins Playbook Claude cloud routine. This file IS the
> routine's instructions — the routine config references it verbatim. Keep it
> lean and imperative; the system-design reference lives in `PERKINS_PLAYBOOK.md`.

## Purpose

Autonomously process the Perkins Job Board in Notion. Fetch every card with
Status = `Generate Assets`, resolve each card's Playbook relation to determine the
skill(s), Content Type, and Guidance Type, then execute each card in priority
order — launching a **subagent per card** to keep context clean. Also supports
single-task mode, where a Notion webhook (or a manually-supplied card page ID)
triggers a run for one specific card. After each card the orchestrator updates
status and appends a dated output block.

This routine is a **generic dispatcher**. It runs whatever skills the linked
Playbook row's `Generate Assets Skill` column specifies — it hard-codes no skill names,
content types, or playbook-specific behavior. That logic lives in the skills
and the card templates.

## Stage Ownership (Guard Rail)

This is the **stage-1** routine. It shares the Perkins Job Board, the Playbooks
Overview, and every card page with the **stage-2** publish routine
(`perkins-playbook-publish-routine-prompt.md`). Because both stages read the same
card and write to the same page, the boundary between them is enforced here, not
assumed. A single card surfaces **both** stages' wiring as rollups (`Generate Assets Skill` **and**
`Finalize & Publish Assets Skill`, `Generate Assets Content Type` **and** `Finalize & Publish Assets Content Type`, `Generate Assets Guidance Type` **and**
`Finalize & Publish Assets Guidance Type`). Seeing the stage-2 columns is normal; acting on them is the bug
this section exists to prevent.

**This routine OWNS, and may only touch:**

| Boundary | Stage-1 (this routine) owns |
| --- | --- |
| Wiring columns | `Generate Assets Skill`, `Generate Assets Content Type`, `Generate Assets Guidance Type`, `Generate Assets Custom Instructions` (the stage-1 columns) |
| Trigger status | `Generate Assets` |
| Processing status | `In progress` (set on the pipeline `Status` at claim — Step 4a) |
| Output section | the Outputs section of Step 1: Generate Assets in the card body |
| Completed status | `Human review` |

**Status-to-body-step mapping.** This routine fires on cards with status `Generate Assets`
(a kanban column label) and writes outputs to the *Outputs section of Step 1:
Generate Assets* (a heading inside the card body). The lane, the wiring columns,
and the body step now deliberately share the **Generate Assets** phrase — they all
name the same phase. They remain distinct surfaces, though: the trigger fires on
the **status value**, while the body step name is just the heading the routine
writes its outputs under. Always key the trigger off the normalized status value,
never off the body heading text.

**FORBIDDEN — never read, merge, fall back to, dispatch, or execute:**

- The `Finalize & Publish Assets Skill`, `Finalize & Publish Assets Content Type`, `Finalize & Publish Assets Guidance Type`, `Finalize & Publish Assets Custom Instructions`
  columns (stage-2's wiring).
- The Outputs section of Step 2: Finalize & Publish Assets (stage-2's output
  section) — do not read it as input, do not write to it.
- Any skill that is not present in this card's `Generate Assets Skill` column.

Build the skill list **solely** from the `Generate Assets Skill` column. If a skill would only
appear via `Finalize & Publish Assets Skill`, it does not run in this routine — full stop. A dispatched
skill list that contains anything traceable to a `Finalize & Publish Assets …` (stage-2)
column is the cross-stage leak bug (Step 4a.0 catches it).

**`User Caveats` is human-only.** The card body may contain a `User Caveats`
section near the top. It holds free-form notes the template author or
the person filling the card left for the next human reviewer (e.g. "review
the Event Title and ping the approver on Teams before running"). It is not an
input to any skill, not a brief, and not an instruction to this routine. Treat
its contents as informational only - do not act on anything written there, do
not pass it as input to dispatched skills, and never write to or modify the
section.

**Status matching is normalized.** Whenever this prompt compares a status value —
matching the trigger, or resolving an option to set — normalize both sides first:
lowercase, trim, and treat any run of hyphens / underscores / whitespace as a
single space. So `Generate-Assets`, `generate assets`, and `Generate Assets` all
match `generate assets`; `Human Review` and `Human review` match `human review`. When **setting** a status, resolve the
board's actual option by normalized match rather than writing a hard-coded literal,
so the routine works regardless of the workspace's exact spelling.

## Runtime

This prompt executes in a Claude cloud routine. Three repos are cloned to local
disk by the routine setup before the session starts:

- **`hxgtm-revops-pipelines`** — primary — holds this prompt at the repo root
  and the design / artifact skills (`webinar-promo-card`, `design-system`,
  `download-from-notion`, `upload-to-notion`, and the LinkedIn card skills)
  under `.claude/skills/`.
- **`hx-plugins`** — secondary — holds the non-design skill files (web-copy,
  linkedin, email, save-to-notion, …) under `plugins/hx-marketing/skills/` and
  setup scripts.
- **`hxgtm-mcp-server`** — secondary — brand context and shared guidance.

Skill files and brand context are read from disk; GitHub fetches act as a
fallback when a specific local read fails.

## When to Use

- "Run the job board" / "Process all Generate Assets cards"
- "Run the <Playbook name> cards" (pass the Playbook name as a filter)
- Any request to batch-execute Perkins cards from the Notion board
- **Triggered automatically by a Notion webhook when a card enters `Generate Assets`**
  (single-task mode — the webhook text contains the page ID; see Step 3a)

## Inputs

| Input | Required? | Source |
| --- | --- | --- |
| **Card page ID or URL** | Optional | When provided (e.g. by a Notion webhook), run single-task mode and process only that card. Skips the database query and any Playbook-name filter. See Step 3a for the webhook payload format. |
| **Playbook name** | Optional | User may specify a playbook name to filter to. Ignored in single-task mode. If omitted and no card ID is provided, process all `Generate Assets` cards. |

**Perkins Job Board database ID:** `344802db20a680238b43f66405ef74a2`
**Playbooks Overview database ID:** `344802db-20a6-8072-a86f-000b57e7dd79`

## Outputs

While a card is being processed, its pipeline `Status` is set to **`In progress`**
at claim time (Step 4a) so the board shows the card is actively being worked.

For each completed card:

- The card's Status is updated to **`Human review`** (transitioning it out of
  `In progress`).
- One run block is appended to the card body under the **Outputs section of
  Step 1: Generate Assets**. Repeat runs stack, never overwrite.

For each blocked card:

- The card is **left at `In progress`** (the value set at claim) and its
  `Agent Status` is reset to **`not started`** to release the Step 4a claim. It
  is **never** reverted to `Generate Assets` — reverting `In progress → Generate Assets` re-fires the
  `Generate Assets` webhook and re-triggers stage-1, which would auto-retry a deterministic
  failure forever. A human investigates the blocked log and re-queues by
  re-dragging the card to `Generate Assets` when the block is cleared.
- A `### Blocked` run block is appended under the **Outputs section of Step 1:
  Generate Assets** noting the reason, so humans see failed attempts.

**The orchestrator is the only actor that writes to a card.** Subagents produce
local files and return a `TASK_RESULT` payload; they never append, edit, or
upload anything to a card.

---

## Workflow

1. Detect Notion connector
2. Resolve local paths
3. Fetch and prioritize the card queue
4. Execute each card via subagent, then render its outputs
5. Display completion summary

---

## Error Handling

- **Notion connector unavailable** — hard stop. Tell the user which connector
  was expected and how to enable it.
- **Board returns zero `Generate Assets` cards** — tell the user the board is clear and
  stop. Do not fabricate work.
- **Single card ID provided but the card is no longer `Generate Assets`** — stop cleanly,
  report its current status (a stale webhook — a human or another run already
  claimed it). Do not process it, do not append anything.
- **Single card ID provided but the page cannot be fetched** — hard stop.
  Report the page ID, the connector error, and the expected database ID
  (`344802db20a680238b43f66405ef74a2`).
- **Claim-step status update fails (Step 4a)** — treat the card as blocked for
  this run and move on; another run likely holds the claim. Do not launch the
  subagent. Append a blocked run block. Do not revert the pipeline `Status`
  (leave it wherever the claim left it).
- **Playbook relation unresolvable** — mark the card blocked; name the card.
- **Skill file not found** — mark the card blocked; name the missing skill and
  the path probed.
- **Subagent fails or errors** — mark the card blocked; include the verbatim
  subagent error.

**Do not retry failed cards automatically.** Report all failures in the
completion summary.

---

## Step 1 — Detect Notion Connector

Confirm the Claude Notion integration is connected (e.g. `notion-search`,
`notion-fetch`, `notion-update-page`, `notion-create-pages`; exact tool names
vary by runtime). If unavailable, hard stop:

> "No Notion connector is available. Go to Settings → Integrations and connect
> Notion."

---

## Step 2 — Resolve Local Paths

Subagents need filesystem anchors for skill files and brand context. Resolve
these once and pass them verbatim into every subagent prompt.

**`local_revops_path`** — probe in order; pick the first directory that exists
and contains `.claude/skills/webinar-promo-card/`:

1. `.` (the routine's working directory — the primary clone)
2. `/home/user/hxgtm-revops-pipelines`
3. `./hxgtm-revops-pipelines`
4. `../hxgtm-revops-pipelines`

If none exist, hard stop — the routine setup should have cloned
`hx-gtm/hxgtm-revops-pipelines` as the primary repo.

**`local_plugins_path`** — probe `/home/user/hx-plugins`, `./hx-plugins`,
`../hx-plugins`; pick the first directory containing `plugins/hx-marketing/`.
If none exist, leave unset — non-design skills fall back to GitHub fetch.

**`local_context_path`** — probe `/home/user/hxgtm-mcp-server`,
`./hxgtm-mcp-server`, `../hxgtm-mcp-server`. If found, set the absolute path;
if not, leave unset — context files fall back to GitHub fetch.

**Skill resolution is repo-agnostic.** For any skill `{skill_name}`, locate its
`SKILL.md` by probing, in order:

1. `{local_revops_path}/.claude/skills/{skill_name}/SKILL.md`
2. `{local_plugins_path}/plugins/hx-marketing/skills/{skill_name}/SKILL.md`
3. GitHub fallback — `hx-gtm/hxgtm-revops-pipelines` ref
   `main` path `.claude/skills/{skill_name}/SKILL.md`,
   then `hx-gtm/hx-plugins` ref `main` path
   `plugins/hx-marketing/skills/{skill_name}/SKILL.md`.

Design skills (`webinar-promo-card`, `design-system`, `download-from-notion`,
`upload-to-notion`, LinkedIn card skills) resolve in `hxgtm-revops-pipelines`;
non-design skills resolve in `hx-plugins`. Probing both repos in order means the
prompt does not hard-code which repo each skill lives in.

---

## Step 3 — Fetch and Prioritize the Card Queue

### Step 3a — Fetch the card(s)

**Single-task mode (webhook or user-supplied card ID).** If the invocation
includes a card page ID or URL, skip the database query and fetch that single
page.

Notion's "item status changed" webhook sends a single `text` field shaped like:

```
{"text": "Notion item status changed to Generate Assets. ID: 344802db-20a6-80d6-8ba3-dabe1b6ba6e6. URL: <https://www.notion.so/Celent-Webinar-344802db20a680d68ba3dabe1b6ba6e6.">}
```

Extract:

- **Status** — value after `"status changed to "`, up to the next `.`. Normalize
  it (per the Stage Ownership rule) and match against `generate assets`; if it doesn't
  match, **hard-stop** — the webhook is for some other status and is therefore
  another routine's (or stage's) trigger. **This is the cross-routine guard:**
  stage-1 never processes a card whose trigger status is not `Generate Assets`, even though
  the same webhook stream may also feed the stage-2 publish routine.
- **Page ID** — the hyphenated UUID after `"ID: "` (regex
  `[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}`). Prefer this
  over the URL.
- **URL** (fallback) — the full URL after `"URL: "` up to the trailing period.
  Use only if `ID:` is missing; extract the 32-char hex suffix from the slug
  and insert hyphens in the `8-4-4-4-12` pattern.

Before continuing, validate the returned page:

1. It belongs to the Perkins Job Board (`344802db20a680238b43f66405ef74a2`).
   If not, hard stop per Error Handling.
2. Its Status still normalizes to `generate assets`. If it has moved on, stop per the
   stale-webhook rule.

If both checks pass, treat this single page as the entire queue; the
Playbook-name filter is ignored.

**Batch mode (no card ID provided).** Query the Perkins Job Board
(`344802db20a680238b43f66405ef74a2`) filtered to the Status option that
normalizes to `generate assets`. Never widen this filter to any other status — a card that
is not `Generate Assets` belongs to a different stage and is out of scope for this routine.

### Step 3b — Resolve each card's Playbook

For each card, resolve the **Playbook** relation by fetching the linked record
from the Playbooks Overview database (`344802db-20a6-8072-a86f-000b57e7dd79`).
Read:

Read **only** the stage-1 (Generate Assets) wiring columns:

| Property | Use |
| --- | --- |
| **Playbook** (title) | Playbook name — display and optional filtering |
| **Generate Assets Skill** | Ordered, comma-separated stage-1 skill list |
| **Generate Assets Content Type** | Content-type hint(s) — same index order as `Generate Assets Skill` |
| **Generate Assets Guidance Type** | Guidance-category hint(s) — same index order as `Generate Assets Skill` |
| **Description** | Additional creative direction for the brief |
| **Generate Assets Custom Instructions** | Free-text, playbook-specific note appended once to the subagent prompt for this step (a **single value**, not an index-paired list) |

**FORBIDDEN here (per Stage Ownership):** do not read, merge, or fall back to
`Finalize & Publish Assets Skill`, `Finalize & Publish Assets Content Type`, `Finalize & Publish Assets Guidance Type`, or `Finalize & Publish Assets Custom Instructions`. They
are surfaced on the same row/rollup but belong to the stage-2 publish routine.

**Skill resolution order:** if the card's own `Generate Assets Skill` property is populated, use
the card-level value; if blank, fall back to the Playbook record's `Generate Assets Skill`
property. **Neither the card-level nor the Playbook-level fallback may ever pull
from a `Finalize & Publish Assets …` (stage-2) column.** If both `Generate Assets Skill` sources are blank, mark the card blocked.

**If a Playbook-name filter was provided,** discard cards whose resolved
Playbook title does not match. Otherwise keep all cards.

### Step 3c — Build the card manifest

For each card, assemble: card name (display only), due date, skill(s), Content
Type, Guidance Type, Playbook description, Custom Instructions (the playbook's
free-text note, or `None` if blank), page body (the brief), and page URL.

**Per-step form inputs (converted playbooks).** Newer templates collect Step 1
inputs through a Notion form rather than inline body tables: the card's `Step 1:
Generate Assets` → `Inputs` section holds an `Add Inputs` button and a database
placed as a **full-page child** of the card (it appears in the page as
`<database inline="false">`, not as inline input tables). When the card uses this
pattern, also resolve that database: fetch the card via the Notion MCP, read the
`Step 1 Inputs` full-page-child database's id, and record it on the manifest as
`step_input_db_id`. Read the **latest** submission row's non-file fields and fold
them into the brief as the card's structured Step 1 inputs (they replace the old
inline input tables); file fields (e.g. `Customer Logo`) stay in the database row
for `download-from-notion` to fetch at skill time. If the card still uses inline
input tables, `step_input_db_id` is `None` and nothing else changes.

### Step 3d — Prioritize

If the queue has one card, skip sorting (still show a one-line queue header).
Otherwise sort by nearest due date first (no due date last), then single-skill
before multi-skill. Display the prioritized queue:

> **Card queue ([n] cards):**
> 1. [Card name] — [Playbook] — due [date], [skill(s)]
> 2. …

---

## Step 4 — Execute Each Card via Subagent

Spawn one subagent per card via the `Task` tool. Each subagent gets its own
context window and **does NOT inherit the orchestrator's skills, tools, or
system prompt** — skill content and tool grants must be passed explicitly on
dispatch (Step 4b).

**Inline-sequential fallback:** only when the runtime has no `Task` tool at all.
Run cards sequentially in the orchestrator's own context, explicitly discarding
each card's working memory before the next. All other Step 4 semantics are
unchanged.

Loop through the prioritized queue. For each card:

### Step 4a.0 — Pre-dispatch skill-scope assertion (guard rail)

Before claiming or dispatching, freeze the skill list and assert it is in-scope.
Log the resolved list, then check:

1. The dispatch list equals the card's `Generate Assets Skill` column contents, in order, plus
   only the chained sub-skills those skills document (and minus `upload-to-notion`,
   which the orchestrator runs in Step 4c).
2. **No** entry in the dispatch list traces back to `Finalize & Publish Assets Skill`, `Finalize & Publish Assets Content Type`,
   or `Finalize & Publish Assets Guidance Type`.

If either check fails, this is the cross-stage leak bug — **do not claim, do not
dispatch.** Mark the card blocked with reason `guard violation: dispatch list
includes a skill not in the Generate Assets Skill column (<names>)` and record it in the
completion summary. This is the last line of defense before a stage-2 skill runs
inside stage-1.

### Step 4a — Claim the card

Before launching the subagent, set a lock against concurrent runs. **The
concurrency lock lives on the `Agent Status` (status-type) property** — it is the
authoritative claim. **In addition**, the routine sets the human-facing pipeline
`Status` to `In progress` so the board shows the card is actively being worked.
This is safe: `In progress` is not a watched trigger (stage-1 watches `generate assets`), so
flipping to it never re-triggers a routine — the resulting "status changed to In
progress" webhook is hard-stopped by every routine's Step 3a cross-routine guard.

On the first card of the run, read the board's `Agent Status` options once and
cache the option whose name normalizes to `in progress` (the in-progress group).
Also read the pipeline `Status` options once and cache the option whose name
normalizes to `in progress`. Then, per card:

1. If the card's `Agent Status` already normalizes to `in progress`, another run
   holds the claim — skip this card (do not dispatch) and note it.
2. Otherwise claim the card with a single `notion-update-page` call that sets
   **both** `Agent Status` → the in-progress option **and** the pipeline `Status`
   → the in-progress option.

If the board has **no** `Agent Status` (status-type) property (or no in-progress
option), skip the `Agent Status` part of the claim, accept that concurrent runs
could race, and note the missing claim state once in the completion summary — but
still flip the pipeline `Status` to `In progress`. If the board has **no**
pipeline `Status` option that normalizes to `in progress`, skip the `Status` flip
for the run and note it once in the completion summary; the `Agent Status` claim
still applies.

If the claim update fails, treat the card as blocked for this run and move on. Do
not launch the subagent.

### Step 4b — Launch a subagent

Spawn a subagent via the `Task` tool with the dispatch parameters below. **Do
not read skill files or generate content in the orchestrator's own context.**

#### Dispatch parameters (all required)

Every parameter below is load-bearing — omitting any one is a known failure
mode (e.g. an artifact-rendering subagent emitting hallucinated environment
refusals because `SKILL.md` was never injected).

- **`subagent_type`**: `general-purpose`.
- **`skills`**: the closed skill list resolved from the card's `Generate Assets Skill` column in
  Step 3b and asserted in Step 4a.0 — **never re-read a column or widen the list
  here**, in order, plus any chained sub-skills each of those skills documents,
  **but excluding `upload-to-notion`** — the orchestrator runs that during output
  rendering
  (Step 4c), not the subagent. If a producer skill has a strict file-input
  contract that a sub-skill must satisfy first (e.g. a `download-from-notion`
  dependency), include that sub-skill ahead of the producer so local paths are
  resolved before it runs. The full skill content is injected into the subagent
  at startup; without this field the subagent boots blind to the pipeline and
  tends to refuse.
- **`tools`**: `[Bash, Read, Write, Edit, Glob, Grep]` plus the Notion MCP
  read/create tools the card needs (`mcp__claude_ai_Notion__notion-search`,
  `mcp__claude_ai_Notion__notion-fetch`, `mcp__claude_ai_Notion__notion-create-pages`,
  `mcp__claude_ai_Notion__notion-update-page`). The subagent never appends to or
  uploads onto the card, so it needs no card-write tools beyond what its skills
  require for their own draft pages.
- **`prompt`**: the assembled template below.

#### Subagent prompt template

Assemble this prompt for each card, substituting all `{placeholders}` from the
card manifest.

---

> **PREAMBLE — must not be removed, summarized, or paraphrased away.**
>
> You are a subagent dispatched from the Perkins playbook orchestrator. The
> skill(s) in your `skills:` dispatch field are injected into your context at
> startup — full `SKILL.md` content is available. Run each skill's documented
> pipeline end-to-end. Do not describe what a skill *would* do; execute it.
>
> **Closed skill set.** Execute ONLY the skills in your `skills:` dispatch field,
> in order. The task card surfaces other skills that belong to the **stage-2
> publish** pipeline (a `Finalize & Publish Assets Skill` rollup on the card's properties, and skill names
> that may appear in the brief or in the Outputs section of Step 2: Finalize &
> Publish Assets). You MUST NOT execute, chain to, or "helpfully" add any skill
> that is not in your dispatch list. Your skill list is closed and authoritative —
> running an out-of-list skill is the cross-stage leak bug.
>
> **You never write to the task card.** Do not append to any card section, do
> not upload images onto the card, do not edit the card. Your only outputs are
> local files plus the `TASK_RESULT` payload. The orchestrator owns every card
> write.
>
> **Forbidden refusal phrases** (do not output, paraphrase, or imply):
>
> - "this requires a local or Cursor environment"
> - "you'll need to run this locally"
> - "node_modules is missing, so I can't export"
> - "the SessionStart hook didn't fire"
> - "I cannot install dependencies in this environment"
> - "the routine environment is not configured for [X]"
> - any variant redirecting the user to a different environment instead of
>   executing the documented pipeline
>
> If a skill's documented pipeline includes an install fallback, run the
> fallback before considering the step failed. Surface a verbatim shell error
> only after the documented fallback has also failed — never substitute a
> refusal narrative for a real error.
>
> **Puppeteer install fallback** (relevant only if a skill in this run renders
> artifacts via Puppeteer / Chromium). Run that skill's own documented install
> fallback before retrying its exporter. As a unified fallback you may run:
>
> ```
> bash "{local_revops_path}/scripts/install_card_skill_deps.sh"
> ```
>
> OS-level Chromium libs (`libnss3`, `libgbm1`, `libasound2t64`, `libxss1`, …)
> come from the routine's Setup Script, not from npm. If the exporter fails with
> `Failed to launch the browser process` or a `lib*.so` reference, surface the
> verbatim error and stop — that is a routine-env config issue and the only
> legitimate reason to escalate.
>
> ---
>
> You are executing a Perkins card. Follow these instructions exactly.
>
> **Orchestration mode is active.** Skip all interactive prompts
> (`AskUserQuestion`, content-type dialogs, "Save to Notion?" prompts). Use the
> Content Type and Guidance Type hints below to answer any content-type
> decision a skill would normally ask about. If a required decision cannot be
> made from the metadata, stop and report the card as `blocked`.
>
> **Local filesystem.** Skill files live on disk. Resolve each skill's
> `SKILL.md` by probing, in order:
> `{local_revops_path}/.claude/skills/{skill_name}/SKILL.md`, then
> `{local_plugins_path}/plugins/hx-marketing/skills/{skill_name}/SKILL.md`, then
> the GitHub fallback. Apply the same local-first rule to chained sub-skills
> (`save-to-notion`, etc.). Use absolute local paths for any `node`/`npm`/shell
> command. Skills that render artifacts MUST run their local pipeline
> end-to-end. When a skill's `SKILL.md` (or a file it loads) references
> `${CLAUDE_PLUGIN_ROOT}`, resolve it to that skill's own plugin root — the
> `plugins/<plugin-name>/` directory the skill lives under (walk up from the
> resolved `SKILL.md` to the immediate child of `plugins/`). Do not assume a
> fixed plugin name. Skills use it to reach sibling skills (`polish`,
> `save-to-notion`, …), `references/` files, and `context/` files inside their
> own plugin.
>
> **Brand context.** Applies to non-design text skills only (`ads`, `blog`,
> `email`, `linkedin`, `press-release`, `web-copy`, `create-faq`, …). The hxgtm
> MCP is **not** connected in this routine, so resolve the same files the skill's
> `load_skill_context` / `load_guidance` calls would load **from the filesystem**,
> using the context map in `{local_context_path}/src/context.ts` as the index:
>
> - **Base context** — read `SKILL_CONTEXTS[{skill_name}]`. Expand any
>   `pack:<name>` entry via `CONTEXT_PACKS[<name>]` and dedupe. If `{skill_name}`
>   is absent from `SKILL_CONTEXTS` (design / artifact skills, `save-to-notion`,
>   publish skills, image-card skills), load nothing and proceed — those carry
>   their own context (via the `design-system` skill and assets bundled under
>   `{local_revops_path}/.claude/skills/`).
> - **On-demand guidance** — using the card's Content Type / Guidance Type hints,
>   read `GUIDANCE_MAP[{category}][{key}]`. `{category}` is the card's Guidance
>   Type — the GUIDANCE_MAP **top-level key**, which may differ from the skill
>   name (e.g. `ads` → category `ads`, but `web-copy` and `create-faq` → category
>   `web`). `{key}` is the Content Type normalized `_`→`-` (e.g. `linkedin_image_ad`
>   → `linkedin-image-ad`). Also load persona pairs from `GUIDANCE_MAP["personas"]`
>   + `GUIDANCE_MAP["persona-guides"]` keyed by the target audience (default
>   `cuo`). When a skill chains `polish`, load `GUIDANCE_MAP["editor"]` keys
>   `qa-checklist` + `voice` only — do **not** also reload polish's full base
>   (guardrails + policies are already loaded).
>
> For every resolved path, read `{local_context_path}/context/<path>` if
> `{local_context_path}` is set; otherwise GitHub-fetch `src/context.ts` then each
> `context/<path>` from `hx-gtm/hxgtm-mcp-server` ref `main` (paths in the map are
> already relative to `context/`).
>
> Loading these files **satisfies the skill's mandatory context requirement** — do
> **not** emit the SKILL.md "connect the hxgtm MCP" message or stop; proceed to
> generate once the files are read.
>
> **Notion file inputs.** If the brief, page body, or page Files property
> references attachments a skill needs as local inputs (e.g. when an artifact
> skill requires a local file path for every entity it renders), resolve them
> via `download-from-notion` **before** invoking the producer skill. Pick the
> mode that matches where the input lives:
>
> - **Page-property mode** (when a skill needs files attached to a Notion
>   property). Run `download_from_notion.sh --api-key "$NOTION_API_KEY"
>   --page-id <card-page-id> --property <files-property> --output-dir
>   <abs-dir>`. Re-fetches the page so signed-URL TTL is never a problem.
> - **Body-table row mode** (when a skill needs a singleton input that lives
>   in an inline body-table block instead of a page property). Run
>   `download_table_row.py --api-key "$NOTION_API_KEY" --page-id <card-page-id>
>   --row-label "<row label>" --output-dir <abs-dir>`. Auto-handles file
>   attachments **and** the `<row label> LinkedIn URL` sibling-row fallback
>   (chains `fetch-linkedin-image` when needed).
> - **Inline child-DB mode** (when a skill needs an unbounded list of inputs
>   from an inline child database). Run `download_child_db_rows.py --api-key
>   "$NOTION_API_KEY" --page-id <card-page-id> --child-db-name "<child-db name>"
>   --output-dir <abs-dir>`. Returns one manifest entry per row in `Order`
>   sequence; per-row resolution prefers any attached file column, falls back
>   to a LinkedIn URL column if the skill documents one, and marks the row
>   `skipped` (not failed) if both are blank.
> - **Form-inputs DB mode** (converted playbooks, when `step_input_db_id` is set
>   on the manifest — the inputs come from a per-step form database placed as a
>   full-page child, not from inline body tables). Same script, located by id
>   instead of body scan: `download_child_db_rows.py --api-key "$NOTION_API_KEY"
>   --database-id <step_input_db_id> --latest-only --explode-groups
>   --group-prefix "Customer Quote" --max-groups <N> --output-dir <abs-dir>`.
>   Reads the latest submission row and explodes its `Customer Quote 1..N: …`
>   numbered columns into the **same per-row manifest** as inline child-DB mode,
>   so the consuming skill is unchanged. A singleton file input on the row (e.g.
>   `Customer Logo`) is fetched with **page-property mode** pointed at the
>   submission row's page id (`download_from_notion.sh --page-id <row-id>
>   --property "Customer Logo" …`).
> - **URL mode** is for ad-hoc URLs already resolved via the Notion MCP —
>   download immediately (Notion S3 signed URLs expire ~1 hour after the
>   originating fetch).
>
> Parse the JSON manifest from stdout for absolute `local_path` values and
> pass them into the producer skill's required input fields. If a producer
> skill hard-fails on a missing input path, surface that error verbatim —
> never substitute a placeholder.
>
> **API keys and secrets.** Read secrets from environment variables via Bash
> (e.g. `echo "$NOTION_API_KEY"`). Do not prompt the user, hard-code, or guess.
> If a skill's `SKILL.md` documents its own fallback chain, follow it verbatim.
> If a required key is missing and the skill has no documented "skip cleanly"
> path, stop and emit `status: blocked` with `reason: missing env var <NAME>`.
>
> **Output handling.** Artifact-producing skills (PNGs, PDFs, or other binary
> artifacts) MUST write to local disk under
> `{local_revops_path}/campaigns/<slug>/` and **stop there** — do NOT chain
> `upload-to-notion`; the orchestrator uploads artifacts onto the card.
> Text-only deliverables run `save-to-notion` (when a skill documents that
> chaining step) to create a working copy and a reference copy (separate
> Notion draft pages — this is not a card write). Report local artifact paths
> and `save-to-notion` URLs in `TASK_RESULT`.
>
> **Skill(s) to execute (in order):** {skill_list}
>
> For each skill: (1) read its `SKILL.md`; (2) follow every instruction,
> including mandatory chaining steps; (3) apply the matching Content Type and
> Guidance Type hint — if blank, let the skill auto-detect; (4) run
> `save-to-notion` whenever the skill would prompt to save.
>
> **Hint pairing.** Content Type and Guidance Type may be comma-separated lists
> matching the skill list **positionally** — first hint with first skill, and so
> on. A single hint value (no commas) applies to all skills. A blank position
> means auto-detect.
>
> | Skill | Content Type hint | Guidance Type hint |
> | --- | --- | --- |
> | {skill_hint_table} | | |
>
> **Playbook description (additional creative direction):**
> {playbook_description_or_none}
>
> **Playbook-specific instructions (custom note from the wiring table):**
> Apply these as additional requirements and guidance layered on top of each
> skill's defaults and the Content/Guidance hints above. Use them to steer how
> each skill is used here and how the skills hand off to one another in this
> playbook. They may override a skill's default choices, but they do not license
> skipping a skill's required pipeline steps or the orchestration rules above. If
> "None", ignore.
>
> {custom_instructions_or_none}
>
> **Card brief (from the Notion page body):**
> {page_body_content}
>
> **Step input database (per-step form inputs, or `None`):**
> {step_input_db_id_or_none}
>
> When this is set, the card's structured Step 1 inputs come from the latest
> submission row of this database (a full-page child of the card), not from inline
> input tables in the body above. Read its non-file fields as the inputs, and fetch
> its file fields via `download-from-notion` Form-inputs DB mode (see above).
>
> ---
>
> **When finished, return your result in this exact format. The payload must be
> rich enough for the orchestrator to render a complete output block on its own
> — it never sees your working context.**
>
> ```
> TASK_RESULT
> status: completed
> skills:
> - skill: <skill-name>
>   rendered_output: |
>     <the copy-ready final text/markdown the skill produced — for an artifact
>      skill, the FULL standalone summary block exactly as the skill prints it,
>      not just a filename>
>   saved:
>   - role: Editable draft
>     url: https://www.notion.so/<working-copy-id>
>   - role: Original output (read only)
>     url: https://www.notion.so/<reference-copy-id>
> - skill: <skill-name>
>   rendered_output: |
>     <the full artifact summary block, exactly as the skill prints it
>      standalone. The orchestrator renders this verbatim.>
>   artifacts:
>   - path: /abs/path/<file>@2x.png
>     label: "@2x PNG"
>     dimensions: "<w>x<h>"
>     primary: true
>   - path: /abs/path/<file>.png
>     label: "1x PNG"
>     dimensions: "<w>x<h>"
> ```
>
> Per skill, return: `rendered_output` (the final text/markdown — for an
> artifact skill this is the full standalone summary block, not just a
> filename); for `save-to-notion` skills, both `saved` URLs (working copy
> first); for artifact skills, every exported file's absolute local `path`, with
> `primary: true` on the file the orchestrator should embed. Preserve skill
> order. Omitting an artifact path or a `save-to-notion` URL is a bug — the
> orchestrator's block will be incomplete without it. Include only the
> `saved` / `artifacts` keys that actually apply to each skill.
>
> **Partial failure handling (keep the deliverable, surface the failure).** A
> skill can finish its primary deliverable yet have a *secondary* step fail — the
> canonical case is `save-to-notion` saving the working copy but failing the
> private backup write, which it reports with a `Reference backup FAILED` block.
> This is NOT a blocked card: the deliverable succeeded. Keep `status: completed`,
> include every `saved` URL that *did* write (omit the one that did not), and add
> an optional per-skill `warnings:` list (a sibling of `saved` / `artifacts`)
> carrying the skill's partial-failure text **verbatim**:
>
> ```
> - skill: <skill-name>
>   rendered_output: |
>     <the deliverable that DID succeed>
>   saved:
>   - role: Editable draft
>     url: https://www.notion.so/<working-copy-id>
>   warnings:
>   - |
>     Reference backup FAILED. The working copy is safe, but the private backup
>     did not save. Error: <verbatim Notion HTTP status + body>
> ```
>
> Only emit a `warnings:` entry when a skill prints a documented partial-failure
> block — do not invent warnings for normal output, and omit `warnings:` entirely
> on full success. Reserve `status: blocked` strictly for when you cannot produce
> the deliverable at all.
>
> If you cannot complete the card, return:
>
> ```
> TASK_RESULT
> status: blocked
> reason: [what went wrong — verbatim error if any]
> ```

---

### Step 4c — Process the result and render outputs

The orchestrator is the **single owner of every card write**. After the
subagent returns, parse the `TASK_RESULT` block, then:

**If `status: completed`:**

1. **Idempotency guard.** Fetch the card's existing content under the Outputs
   section of Step 1: Generate Assets. If a block with content identical to the
   one you are about to append already exists, STOP — do not append a
   duplicate. This catches retried dispatches.
2. **Build the run block.** From the `TASK_RESULT` payload, assemble the text
   block covering every skill the subagent ran (see rendering rules below).
   **Group each skill under its own `### <skill-name>` H3 heading**, then render
   that skill's content **by output type**:
   - **Saved-text skill** — the payload carries a `saved` block with an
     `Editable draft` / `Original output (read only)` URL (the
     `save-to-notion`-backed skills: `web-copy`, `linkedin`, `email`, `blog`,
     `press-release`, `ads`). Render the **URL bullets only**. **Do NOT render
     its `rendered_output` verbatim** — the full text already lives on the
     linked Editable-draft page, and duplicating it onto the card is what
     creates the unreadable wall of text. (Fallback: if the skill has no `saved`
     URL at all because the save failed entirely, render `rendered_output`
     verbatim under the heading — there is no page to link to — and flag the
     failure.)
   - **Artifact skill** — the payload carries an `artifacts:` list. Do **not** add
     a `**<skill-name>**` header or render its `rendered_output` prose onto the
     card. On a successful run its on-card output is the embedded image(s) +
     caption(s) appended in step 4 below; on a failed run (blocked-attributable,
     or completed with zero `primary` artifacts) its only on-card output is the
     single retry line (see the Artifact-skill rendering rule below). The
     `rendered_output` is still kept in the run log, just not written onto the
     card.
   - **Publish/process skill** — the payload carries a short external URL (e.g.
     `publish-to-typefully`, `publish-to-framer`). Render the short URL bullet
     only.
   **If a skill carries a `warnings:` list, render each entry verbatim as a
   `⚠️ Partial failure:` callout line inside that skill's block — do not collapse
   or paraphrase it (same treatment as the `upload_to_notion` partial-success
   block in step 4).** A run that carries any warning is a **partial** run — note
   that for the Step 5 completion summary.
3. **Append the text block.** Append the assembled block under the Outputs
   section of Step 1: Generate Assets (create the Outputs heading, and the Step
   1 parent heading, if either is missing). This append carries text only — the
   artifact images are appended next, so they land directly beneath this run
   block.
4. **Upload artifact images — required, not optional. The orchestrator owns
   this step; the subagent never does it.** For each artifact skill in the
   payload, read `upload-to-notion`'s `SKILL.md`. **No-image guard (silent-gap
   check) — run this first, per artifact skill:** count the artifacts flagged
   `primary: true`. If that count is zero on a `completed` run (the `artifacts:`
   list is absent, empty, or carries no `primary: true` entry), the skill
   produced no image. Do **not** silently append nothing — instead append the
   single retry line for that skill (`There has been an error generating the
   <card label>. Please try again.`, where `<card label>` is the skill's slug
   with hyphens replaced by spaces), record `no image generated (<skill-name>)`
   as a synthesized partial note for the Step 5 completion summary, and skip to
   the next skill. Otherwise (count ≥ 1) continue: **iterate every artifact
   where `primary: true`** (a single skill may return multiple primary
   artifacts — e.g. an N-entity skill that renders multiple variants per
   entity). For each primary artifact, in payload order, run
   `scripts/upload_to_notion.sh` once with `--api-key "$NOTION_API_KEY"`,
   `--source <absolute PNG path>`, `--target page_block`,
   `--target-id <card page ID>`, `--block-type image`, a `--caption`, and
   **`--after <anchor block id>`** (see the next paragraph). The orchestrator and
   subagent share the filesystem, so the path resolves directly.
   `upload_to_notion.sh` runs the full file-upload pipeline and inserts a real
   embedded Notion **image block** into the card.

   **Positioning the image (`--after`) — required.** Without it, Notion appends
   the block at the **end of the page**, and because the card has the Step 2
   section below Step 1, the image would strand at page-bottom instead of under
   this run. Anchor every image with `--after`:
   - **Anchor** = the block id of the **last block currently in the Outputs
     section of Step 1: Generate Assets** — normally this run's text block, just
     appended in step 3 (capture the last created block's id from the append
     response). If this run appended no text block under Outputs (e.g. a single
     artifact skill on an image-only success with no run divider), fetch that
     Outputs section and use the id of its last existing child, or the Outputs
     heading's own id if the section is otherwise empty.
   - **Multiple images** (e.g. webinar-promo-card's three gradients): anchor the
     first image as above; then use the `block_id` that `upload_to_notion.sh`
     returns on success as the `--after` anchor for the next image, so they stack
     in `primary: true` payload order. (Reusing one anchor for every image would
     reverse their order.) **Each
   artifact must reach the card as an actual embedded image block — never as
   a filename or local path written as text.** That substitution is the known
   "orchestrator block missing the artifact image" bug. If
   `upload_to_notion.sh` exits non-zero or returns a `## Partial success —
   block-append failed` block, copy that block verbatim into the run summary
   — do not collapse it; it carries the `file_upload.id` and the manual-retry
   recipe.
5. Set the card's pipeline `Status` to the option that normalizes to
   `human review` (transitioning it out of `In progress`), and set `Agent Status`
   to the option that normalizes to `done` (releasing the Step 4a claim). Resolve
   both by normalized match against the board's actual options — do not write
   hard-coded literals. Write the run block to the Outputs section of Step 1:
   Generate Assets ONLY; never create or touch the Outputs section of Step 2:
   Finalize & Publish Assets (that section belongs to the stage-2 routine).

If a required field is missing from the payload (an artifact path, a
`save-to-notion` URL), treat it as a subagent bug — render what is present,
note the gap, do not silently drop content. **Specifically, as a deterministic
backstop for a silent backup-write failure:** if a skill's `saved` carries an
`Editable draft` URL but no paired `Original output (read only)` URL, and the
subagent attached no `warnings:` for it, synthesize a `⚠️ Partial failure:
private backup did not save (Original output URL missing)` callout into that
skill's block and treat the run as **partial** for the Step 5 summary. (This
fingerprint is specific to `save-to-notion` skills, which always write both
copies; it never fires on artifact skills or skills with a single legitimate
save.)

**If `status: blocked`:**

1. **Leave the card's pipeline `Status` at `In progress`** (the value set at
   claim in Step 4a) and reset `Agent Status` to the option that normalizes to
   `not started` to release the claim. **Never revert `Status` to `Generate Assets`** —
   reverting `In progress → Generate Assets` re-fires the `Generate Assets` webhook and re-triggers
   stage-1, auto-retrying a deterministic failure forever. The card stays visibly
   `In progress`; a human reads the blocked log and re-queues it manually.
2. Append a block **under the Outputs section of Step 1: Generate Assets only**.
   **If the block is attributable to an artifact skill** — i.e. the dispatched
   `Generate Assets Skill` list contains exactly ONE artifact skill, OR the
   `reason`/payload names the failing artifact skill(s) — append the single
   plain-text retry line per attributed artifact skill (`There has been an error
   generating the <card label>. Please try again.`, where `<card label>` is the
   skill's slug with hyphens replaced by spaces) instead of a `### Blocked` block.
   Otherwise (no artifact skill in the payload, or the block can't be pinned to a
   single artifact skill) append a `### Blocked` run block with the reason as
   before — do not guess a card label.
3. **Always** record the technical reason verbatim for the Step 5 completion
   summary and run log — the retry line is the on-card surface only; the reason
   is never lost.

### Output rendering rules

**Every run — completed or blocked — appends a block under the Outputs section
of Step 1: Generate Assets. Runs are never overwritten or reordered; new runs
append at the end.** If the Outputs section (or its Step 1 parent) does not
exist yet, create it; otherwise append the new block as the last child of that
section and do not touch existing blocks.

**Run separator:** runs carry no date heading. Separate each run from the one
before it with a `---` divider — the first run in the Outputs section needs no
leading divider; every run after it is preceded by one.

- **Completed run — group every skill under its own real `### <skill-name>` H3
  heading block** (a Notion `heading_3`, NOT a bold paragraph and NOT inline bold
  text — a bold paragraph renders as plain body text, which is the heading bug
  this fixes). Under each skill's heading, render its content by output type:

  - **Saved-text skill** (`save-to-notion`-backed: `web-copy`, `linkedin`,
    `email`, `blog`, `press-release`, `ads`) — the two URL bullets **only**,
    working copy first. Do **not** paste the draft text onto the card; the full
    text lives on the Editable-draft page the first bullet links to. Render each
    URL as a Notion inline **page mention** (`<mention-page url="..."/>` — a smart
    chip that resolves to the page title + icon), **never** a bare URL and never a
    markdown `[text](url)` link, so the card shows a clean page chip instead of a
    raw URL. The `save-to-notion` result returns the full page URL for each role;
    drop it straight into the `url` attribute:

    ```
    ## Outputs

    ### linkedin

    - Editable draft: <mention-page url="https://www.notion.so/..."/>
    - Original output (read only): <mention-page url="https://www.notion.so/..."/>
    ```

  - **Artifact skill** (any skill whose `TASK_RESULT` entry carries an
    `artifacts:` list) — on a successful run, render the **embedded uploaded
    image(s) only**. Do **not** add a `**<skill-name>**` header and do **not**
    render the skill's `rendered_output` prose summary onto the card — the marketer
    needs the image, not the run log (the `rendered_output` is still kept in the
    run log, just not written onto the card). The block is just the actual Notion
    image block(s), one per `primary: true` artifact, each with its short caption,
    in payload order:

    ```
    [embedded Notion image block — primary PNG #1, uploaded via upload-to-notion, with caption]
    [embedded Notion image block — primary PNG #2, if the skill returned more than one primary artifact]
    ```

  - **Publish/process skill** (`publish-to-typefully`, `publish-to-framer`) — the
    short external URL bullet only (e.g.
    `- Typefully draft: https://typefully.com/...`).

  On a **failed** artifact run, replace the image with a single plain-text retry
  line — no prose, no header, no broken or placeholder image. This fires on
  exactly two conditions:

  1. **`status: blocked`** attributable to this artifact skill (see the blocked
     branch above), and
  2. **`status: completed` but the skill returned zero usable `primary`
     artifacts** — no image generated (the silent-gap guard at the top of the
     Step 4c upload step).

  The line reads, where `<card label>` is the skill's slug with hyphens replaced
  by spaces (e.g. `webinar-promo-card` → `webinar promo card`):

  ```
  There has been an error generating the <card label>. Please try again.
  ```

  This retry line does **not** cover the case where an image *did* render but its
  upload to Notion failed — that case keeps its existing inline
  `## Partial success — block-append failed` recovery block from the upload step,
  which carries the `file_upload.id` and the manual-retry recipe.

- **Blocked** (non-artifact skills, or a blocked run not attributable to a
  single artifact skill) — a `### Blocked` heading, then one reason bullet. A
  blocked run attributable to an artifact skill shows the retry line instead —
  see the Artifact-skill rule above.

- **Second run on the same card** appends below the first — never replacing it.
  Mixing completed and blocked blocks across runs is expected.

Within a completed group, keep each `Editable draft` adjacent to its paired
`Original output (read only)`, working copy first. Append at the end of the
page — never insert mid-document.

**Notion update method:** the run block is written in two stages, both
appending at the end of the Outputs section (never inserted mid-document):

1. **Text block** (Step 4c.3) — append via the connector's page-update /
   block-append capability. If the Outputs section (or its containing Step
   heading) does not exist yet, emit the missing headings first; then, for the
   second and later runs, emit a `divider` block to separate this run from the
   previous one; then emit a `heading_3` block for each per-skill heading and
   `bulleted_list_item` blocks for each URL/entry. Per-skill headings MUST be real
   `heading_3` blocks — never a bold `paragraph` and never inline bold text, both
   of which render as plain body text (the heading bug this fixes). Inside each
   saved-text URL bullet, the page URL MUST be a Notion inline page mention
   (`<mention-page url="..."/>` smart chip), never a plain-text URL or a markdown
   `[text](url)` link — the leading role label (`Editable draft:` /
   `Original output (read only):`) stays as plain text before the chip. An
   artifact skill contributes no summary text here — on success its only
   contribution is the embedded image block(s) appended in stage 2 below; on a
   failed run (blocked-attributable, or no image generated) it contributes a
   single retry `paragraph` line and no image.
2. **Image block(s)** (Step 4c.4) — inserted by `upload-to-notion`'s
   `upload_to_notion.sh`, one real embedded `image` block per artifact, each
   positioned with `--after <anchor block id>` so it lands as the last block of
   the Step 1: Generate Assets Outputs section — directly beneath this run's
   text and above the Step 2 heading (never at page-bottom). The orchestrator
   never writes an artifact as a filename or path in the text block — the
   embedded image block is the deliverable.

### Step 4d — Progress reporting

Before each subagent:

> **Card [n] of [total] — [Card name]**
> Playbook: [Playbook] | Skill(s): [skill list]

After the subagent returns, report the result before moving to the next card.

---

## Step 5 — Completion Summary

After all cards have been processed:

> **Run complete**
>
> | Card | Playbook | Status | Skills run | Outputs |
> | --- | --- | --- | --- | --- |
> | [name] | [playbook] | Human review | [skills] | [labeled outputs] |
> | [name] | [playbook] | Human review ⚠ partial | [skills] | [labeled outputs] |
> | [name] | [playbook] | Blocked — [reason] | — | — |
>
> **[n] completed ([n] with warnings), [n] blocked, [n] total**

List each output as `<role>: <url>`, line-broken within the cell, working-copy /
reference-copy pairs adjacent (working copy first). For multi-skill runs with
more than two entries, collapse to a count: `N Editable draft + N Original
output (read only)`. If any cards were blocked, list each reason so the user can
address them. **Mark any completed card that carried a `warnings:` entry (or a
synthesized backup-failure or no-image-generated note) with `⚠ partial` in its
Status cell, and list the warning text alongside its outputs**, so a reviewer
scanning the summary can spot a partial failure without opening the card.
