# Perkins Playbook — Architecture

End-to-end reference for the Perkins Playbook system: how a Notion card becomes a multi-skill, multi-output run inside a Claude Code routine, and how to wire a new playbook without breaking production.

---

## 1. Goals

Perkins Playbooks turn Notion into the front-end for marketing skills in `hx-plugins` and `hxgtm-revops-pipelines`. Instead of picking the right skill, content type, and guidance type themselves, users pick a **Playbook** (e.g. *hx Sessions Promo Pack* bundles web copy, LinkedIn, email, promo card, and Notion upload), fill a template card on the Perkins Job Board, and drag it across columns. A Claude Code routine handles dispatch, context loading, and output rendering.

The principle is: **users pick a Playbook, not a skill.** Skills, content types, and guidance types are an implementation detail managed by the admin Playbooks Overview table.

---

## 2. Repo architecture

- **`hx-plugins`** — skill definitions for the non-design marketing skills (web-copy, linkedin, email, save-to-notion, and so on), the Perkins routine prompt, and setup scripts. Sub-areas: [`hx-core`](https://www.notion.so/hx-core/), [`hx-marketing`](https://www.notion.so/), [`hx-sales`](https://www.notion.so/hx-sales/), [`hx-sdr`](https://www.notion.so/hx-sdr/).
- **`hxgtm-revops-pipelines`** — canonical home of the design / artifact skills `webinar-promo-card`, `design-system`, `download-from-notion`, `upload-to-notion`, the LinkedIn card skills (`linkedin-partnership-card`, `linkedin-customer-quote-card`, `linkedin-case-study-promo`, `linkedin-image-ad-text-only`) and the `fetch-linkedin-image` helper, under `.claude/skills/`, plus the Perkins routine prompts at the repo root.
- **`hxgtm-mcp-server`** *(secondary)* — brand truth, shared guidance, content-type playbooks. Served via `load_skill_context` and `load_guidance` MCP tools.

When wiring a Claude Code routine, attach **`hxgtm-revops-pipelines`** as primary (it holds the routine prompt and the design skills) and **`hx-plugins`** alongside it for the non-design skill files; **`hxgtm-mcp-server`** is added as a secondary attachment so context-path resolution works inside cloud routines.

For generic plugin internals (skill frontmatter, plugin layout) see [plugins/ARCHITECTURE.md](https://www.notion.so/ARCHITECTURE.md). This document focuses on the Perkins flow.

### Active branches

The design / artifact skills live in **`hxgtm-revops-pipelines`** on **`main`** (merged via PR #30 — formerly the `feat/migrate-hx-marketing-skills` feature branch). The non-design skills live in `hx-plugins` on **`feature/hx-marketing-design-skills`**.

In `hxgtm-revops-pipelines` (`.claude/skills/`):

- [`webinar-promo-card/`](https://github.com/hx-gtm/hxgtm-revops-pipelines/tree/main/.claude/skills/webinar-promo-card) — LinkedIn webinar promo card generator (Puppeteer-rendered).
- [`design-system/`](https://github.com/hx-gtm/hxgtm-revops-pipelines/tree/main/.claude/skills/design-system) — brand tokens, gradients, typography source for downstream design skills.
- [`download-from-notion/`](https://github.com/hx-gtm/hxgtm-revops-pipelines/tree/main/.claude/skills/download-from-notion) — downloads Notion-attached files to disk; chained by `webinar-promo-card`.
- [`upload-to-notion/`](https://github.com/hx-gtm/hxgtm-revops-pipelines/tree/main/.claude/skills/upload-to-notion) — file/image upload to Notion via direct REST API (see §9).
- [`linkedin-partnership-card/`](https://github.com/hx-gtm/hxgtm-revops-pipelines/tree/main/.claude/skills/linkedin-partnership-card), [`linkedin-customer-quote-card/`](https://github.com/hx-gtm/hxgtm-revops-pipelines/tree/main/.claude/skills/linkedin-customer-quote-card), [`linkedin-case-study-promo/`](https://github.com/hx-gtm/hxgtm-revops-pipelines/tree/main/.claude/skills/linkedin-case-study-promo), [`linkedin-image-ad-text-only/`](https://github.com/hx-gtm/hxgtm-revops-pipelines/tree/main/.claude/skills/linkedin-image-ad-text-only) — LinkedIn artifact card generators (Puppeteer-rendered; Gemini Image API for logo/headshot cleanup).
- [`fetch-linkedin-image/`](https://github.com/hx-gtm/hxgtm-revops-pipelines/tree/main/.claude/skills/fetch-linkedin-image) — resolves a LinkedIn profile/company URL to a local image; chained fallback for the card skills.
- `publish-to-typefully/` — creates LinkedIn drafts in Typefully from a card's approved LinkedIn output at the Finalize & Publish Assets step; MCP-I/O only, draft-only (never schedules or auto-posts).

Also in `hxgtm-revops-pipelines` (repo root):

- [`perkins-playbook-routine-prompt.md`](https://github.com/hx-gtm/hxgtm-revops-pipelines/blob/main/perkins-playbook-routine-prompt.md) — canonical **stage-1** (Generate Assets) routine prompt.
- [`perkins-playbook-publish-routine-prompt.md`](https://github.com/hx-gtm/hxgtm-revops-pipelines/blob/main/perkins-playbook-publish-routine-prompt.md) — canonical **stage-2** (Finalize & Publish Assets) routine prompt.

---

## 3. Notion surfaces

Two Notion tables form the front-end.

### Admin — Playbooks Overview

[https://www.notion.so/hyperexponential/Perkins-Playbooks-Admin-Console-343802db20a680329d59c5ecbff1f726?source=copy_link#344802db20a680e081b6d0bd38bd2a1a](https://www.notion.so/Perkins-Playbooks-Admin-Console-343802db20a680329d59c5ecbff1f726?pvs=21)

| Column | Meaning |
| --- | --- |
| Playbook name | e.g. *hx Sessions Promo Pack* |
| Generate Assets Skill | comma-separated, **ordered** |
| Generate Assets Content Type | comma-separated, **same index order as Generate Assets Skill** |
| Generate Assets Guidance Type | comma-separated, **same index order as Generate Assets Skill** |
| Status | `Wired` (usable) or `Roadmap` (in development) |
| Job Board template | relation/link to the user-facing template |

Wired playbooks must have a matching template on the Job Board.

### User — Perkins Job Board

[https://www.notion.so/hyperexponential/Perkins-Playbooks-Admin-Console-343802db20a680329d59c5ecbff1f726?source=copy_link#344802db20a6808c9797f65e41861a17](https://www.notion.so/Perkins-Playbooks-Admin-Console-343802db20a680329d59c5ecbff1f726?pvs=21)

Pipeline columns: `Planning → Generate Assets → In progress → Human review → Done`, with `Blocked` available for failure cases. (Two-trigger playbooks add a `Finalize & Publish Assets` lane — see §5a.) Each card represents one task using exactly one Playbook template.

---

## 4. Trigger flow

### Pipeline diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│  NOTION (front-end)                                                     │
│                                                                         │
│   ┌──────────────────────┐      ┌──────────────────────────────────┐    │
│   │ Admin: Playbooks     │      │ User: Perkins Job Board          │    │
│   │ Overview (table)     │◄────►│ Planning │ Generate Assets │ In progress │
│   │  • Generate Assets Skill[i]   │ rel  │ Human review │ Done │ Blocked    │    │
│   │  • Generate Assets Content Type[i]   │      │                                  │    │
│   │  • Generate Assets Guidance Type[i]   │      │  card = one task, one playbook   │    │
│   │  • Status (Wired)    │      │  template (metadata + inputs)    │    │
│   └──────────────────────┘      └──────────────┬───────────────────┘    │
│                                                │ user drags             │
│                                                │ Planning → Generate Assets       │
│                                                ▼                        │
│                                   ┌────────────────────────┐            │
│                                   │ Notion Automation      │            │
│                                   │ (event-driven webhook) │            │
│                                   └──────────┬─────────────┘            │
└──────────────────────────────────────────────┼──────────────────────────┘
                                               │ webhook
                                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  CLAUDE CODE ROUTINE                                                     │
│  (config references VCS prompt — no body pasted into Notion)             │
│                                                                          │
│   ┌─────────────────────────────────────────────────────────────┐        │
│   │ Routine prompt (VCS):                                       │        │
│   │ perkins-playbook-routine-prompt.md                          │        │
│   └────────────────────────┬────────────────────────────────────┘        │
│                            │ load + read card                            │
│                            ▼                                             │
│   ┌─────────────────────────────────────────────────────────────┐        │
│   │ Resolve Playbook row →                                      │        │
│   │   expand Generate Assets (Skill, Content Type, Guidance Type) by index     │        │
│   │   load_skill_context / load_guidance via MCP                │        │
│   │   (hxgtm-mcp-server)                                        │        │
│   └────────────────────────┬────────────────────────────────────┘        │
│                            ▼                                             │
│   ┌─────────────────────────────────────────────────────────────┐        │
│   │ Dispatcher: 1 subagent per CARD                             │        │
│   │   ┌──────────┐  ┌──────────┐         ┌──────────┐           │        │
│   │   │ subagent │  │ subagent │   ...   │ subagent │  (N=cards)│        │
│   │   │   #1     │  │   #2     │         │   #N     │           │        │
│   │   └────┬─────┘  └──────────┘         └──────────┘           │        │
│   │        │  skills run SEQUENTIALLY in playbook order         │        │
│   │        ▼                                                    │        │
│   │   skill 1 → skill 2 → skill 3 → … → upload-to-notion        │        │
│   │       (each skill produces output appended to the card)     │        │
│   └────────────────────────┬────────────────────────────────────┘        │
│                            │ TASK_RESULT: completed | blocked            │
└────────────────────────────┼─────────────────────────────────────────────┘
                             │
        ┌────────────────────┴────────────────────┐
        ▼                                         ▼
┌────────────────────┐                 ┌──────────────────────┐
│ completed          │                 │ blocked              │
│ status →           │                 │ stays at In progress │
│  Human review      │                 │ Agent Status →       │
│ Agent Status → done│                 │  Not started         │
│ append output      │                 │ append a Blocked     │
│ block under Step 1:│                 │ reason block under   │
│ Generate Assets    │                 │ Step 1: Generate     │
│ Outputs            │                 │ Assets Outputs       │
└────────────────────┘                 └──────────────────────┘

  Topology: 5 cards × 3 skills = 5 subagents, not 15.
  Skills inside a subagent run sequentially; subagents across cards may run in parallel.
```

### Walkthrough

1. User picks a wired playbook's template, fills metadata + agent inputs, drags the card **Planning → Generate Assets**.
2. Notion automation fires a webhook (event-driven, not scheduled).
3. The Claude Code routine receives the webhook and loads the routine prompt from VCS (see §6).
4. The routine reads the card, resolves the Playbook row, expands `(Generate Assets Skill, Generate Assets Content Type, Generate Assets Guidance Type)` index-paired triples, and pulls context via MCP (`load_skill_context`, `load_guidance`).
5. The dispatcher launches **one subagent per task/card**. Skills run **sequentially in playbook order** inside that subagent.
6. Each skill output is appended under the **Outputs section of Step 1: Generate Assets** on the card. Artifact-producing skills (e.g. `webinar-promo-card`) write files locally; the orchestrator uploads them to the Notion page via `upload-to-notion` (see §9).
7. While the card is being processed its pipeline `Status` is set to **In progress** (at claim — see §5a). On success, status flips to **Human review**. On failure the card is **left at In progress** (its `Agent Status` released to `Not started`) with a `### Blocked` block — it is *not* reverted to Generate Assets, which would re-fire the webhook and auto-retry (see §7).

> Topology: 5 cards × 3 skills = 5 subagents, not 15.
> 

---

## 5. Wiring conventions

### Scope of `scaffold-skill`

`scaffold-skill` creates skill files and skill-level documentation only. **Wiring is always manual** — you fill the admin Playbook row in Notion yourself. Scaffolding produces the [SKILL.md](http://skill.md/) and stub docs; it does not register the skill into a playbook.

https://github.com/hx-gtm/hxgtm-revops-pipelines/tree/main/.claude/skills/scaffold-skill

### Six required wiring points per skill

Missing any one of these silently breaks the skill in production:

1. `SKILL.md` (in `hx-plugins`)
2. Content-type playbook (in `hxgtm-mcp-server`)
3. `SKILL_CONTEXTS` entry in `context.ts` (MCP)
4. `GUIDANCE_MAP` entry per content type (MCP)
5. Command wrapper(s) (Plugins)
6. `mcp-fallback.md` section with accurate file counts (Plugins)

Plus README index, `save-to-Notion` routing, and Notion "Agents & Skills" docs.

### Index-position contract

Inside a Playbook row, the three list columns pair **by index**:

```
Generate Assets Skill[i]   ↔   Generate Assets Content Type[i]   ↔   Generate Assets Guidance Type[i]
```

Reordering one list without reordering the others silently breaks wiring with no error. This is the most common wiring failure — **always edit the three columns together** and visually verify alignment after any change.

### Per new wired playbook

A matching Job Board template must exist before status can flip from `Roadmap` to `Wired`. Document the template fields (required vs optional) inline in the playbook row description so users know what to fill.

---

## 5a. Two-stage pipeline & stage-ownership guard rails

The pipeline runs as **two separate Claude cloud routines** over **one shared Notion board and one shared card page**:

| | Stage-1 | Stage-2 |
| --- | --- | --- |
| Prompt | `perkins-playbook-routine-prompt.md` | `perkins-playbook-publish-routine-prompt.md` |
| Trigger status | `Generate Assets` | `Finalize & Publish Assets` |
| Wiring columns (OWNED) | `Generate Assets Skill`, `Generate Assets Content Type`, `Generate Assets Guidance Type` | `Finalize & Publish Assets Skill`, `Finalize & Publish Assets Content Type`, `Finalize & Publish Assets Guidance Type` |
| Output section (OWNED) | Outputs section of Step 1: Generate Assets | Outputs section of Step 2: Finalize & Publish Assets |
| Completed status | `Human review` | `Completed` |

A single card surfaces **both** column sets as rollups (`Generate Assets Skill` *and* `Finalize & Publish Assets Skill`, etc.) and both routines write to the same page. Nothing in the data model keeps them apart — the boundary is enforced in the prompts. Each routine obeys four hard invariants:

1. **Column ownership** — read only the owned wiring columns; never read, merge, or fall back to the other stage's columns.
2. **Closed skill set** — dispatch and execute only the skills in the owned column (+ documented chained sub-skills). Seeing the other stage's skills on the card is expected and is **not** permission to run them.
3. **Output-section ownership** — write only to the owned section. (Stage-2 *reads* the Outputs section of Step 1: Generate Assets as input context but never writes to it, and never executes the `Generate Assets Skill`-column skills that produced it.)
4. **Status (trigger) ownership** — act only when the card's pipeline `Status` matches the owned trigger; otherwise hard-stop, since the same webhook stream feeds both routines.

Each prompt carries a `## Stage Ownership (Guard Rail)` section stating its owned vs forbidden columns, a Step 4a.0 **pre-dispatch assertion** that aborts a card if the dispatch list contains anything traceable to the other stage's columns, and a **Closed skill set** clause in the subagent preamble.

> **Motivating incident.** On the *Customer Press Release* playbook (`Generate Assets Skill = web-copy, linkedin, linkedin-partnership-card`; `Finalize & Publish Assets Skill = linkedin-customer-quote-card`), the stage-1 routine ran all four skills — executing the stage-2 `linkedin-customer-quote-card` inside the Outputs section of Step 1: Generate Assets (and logging a false `— blocked`) before stage-2 ran it again. The guard rails above exist to make that impossible.

### Status matching & the claim lock

- **Tolerant status matching.** Status comparisons normalize both sides (lowercase, trim, collapse hyphens/underscores/whitespace) so `Generate-Assets` ≈ `Generate Assets` and `Human Review` ≈ `Human review`. When *setting* a status, the routine resolves the board's actual option by normalized match rather than writing a literal — workspace-agnostic across spellings.
- **The concurrency lock lives on `Agent Status`; the human-facing `Status` shows `In progress`.** The board carries a separate `Agent Status` (status-type) property (`Not started` / `In progress` / `Done`) that is the authoritative agent-run lock. In addition, at claim time the routine sets the pipeline `Status` (select) to **In progress** so the board reflects that the card is actively being worked. This is safe because `In progress` is **not** a watched trigger — flipping to it only emits a "status changed to In progress" webhook that both routines hard-stop on (Step 3a cross-routine guard), so it never re-triggers a run. Completed transitions (`In progress → Human review` / `In progress → Completed`) are likewise unwatched. A **blocked** run leaves the card at `In progress` (releasing `Agent Status` to `Not started`) rather than reverting to the trigger status — reverting would re-fire the webhook and auto-retry a deterministic failure forever (§7). If the board has no `Agent Status` property, the lock cleanly degrades to "skip + warn" (no concurrency guard, but no regression); if it has no `In progress` `Status` option, the `Status` flip is skipped and noted.

---

## 6. Routine prompt in VCS

The canonical routine prompt lives at [`perkins-playbook-routine-prompt.md`](https://github.com/hx-gtm/hxgtm-revops-pipelines/blob/main/perkins-playbook-routine-prompt.md). The Claude Code routine config **references this file directly** — do **not** paste the prompt body into Notion routine config or the routine UI. Single source of truth, change-tracked in git.

### Creating a new routine — required setup

**1. Routine instruction body (paste verbatim):**

```
For the instructions please refer to hxgtm/hxgtm-revops-pipelines/perkins-playbook-routine-prompt.md
```

That single line is the entire prompt. The routine resolves the path against the attached repo on each run, so prompt updates ship via `git push` — no Notion edit needed.

**2. Attached repos (all three required):**

- `hxgtm/hxgtm-revops-pipelines` — **primary** — branch `main` (the stage-1 routine prompt and skills merged via PR #30). Holds both Perkins routine prompts at the repo root and the design / artifact skill files (`webinar-promo-card`, `design-system`, `download-from-notion`, `upload-to-notion`, the LinkedIn card skills `linkedin-partnership-card` / `linkedin-customer-quote-card` / `linkedin-case-study-promo` / `linkedin-image-ad-text-only`, and `fetch-linkedin-image`) under `.claude/skills/`.
- `hxgtm/hx-plugins` — **secondary** — branch `feature/hx-marketing-design-skills` until merged to `main`. Provides the non-design skill files and setup scripts.
- `hxgtm/hxgtm-mcp-server` — **secondary** — provides brand context and shared guidance via MCP. Required for `load_skill_context` / `load_guidance` to resolve.

**3. Secrets required on the routine:**

- `NOTION_API_KEY` — passed to `upload-to-notion` at dispatch time (see §9).
- Any MCP credentials needed by `hxgtm-mcp-server`.

**4. Environment variables (paste verbatim into the Claude Code routine env config):**

```
CLAUDE_CODE_REMOTE=true
NOTION_API_KEY=ntn_34978507943aBWc....
PUPPETEER_CACHE_DIR=/opt/puppeteer-cache
```

Fill the real `NOTION_API_KEY` value from 1Password — the one above is a truncated placeholder. `CLAUDE_CODE_REMOTE=true` flags this as a cloud-routine run; `PUPPETEER_CACHE_DIR` must match the path used by the setup script below so root-installed Chrome is visible to the session user.

**5. Setup script (paste verbatim into the routine's setup script field):**

```
#!/bin/bash
set -e

# Chromium runtime libraries.
sudo apt-get update -y
sudo apt-get install -y --no-install-recommends \\
  ca-certificates fonts-liberation \\
  libasound2t64 libatk-bridge2.0-0t64 libatk1.0-0t64 libc6 libcairo2 \\
  libcups2t64 libdbus-1-3 libexpat1 libfontconfig1 libgbm1 libglib2.0-0t64 \\
  libgtk-3-0t64 libnspr4 libnss3 libpango-1.0-0 libpangocairo-1.0-0 \\
  libstdc++6 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 \\
  libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 \\
  libxkbcommon0 libdrm2 libxss1 libxtst6 lsb-release wget xdg-utils

# Make Node trust the system CA bundle. Without this, npm fails through
# the cloud environment's security proxy with SELF_SIGNED_CERT_IN_CHAIN
# because Node uses its own bundled CA list, not the system one.
echo 'export NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt' | sudo tee /etc/profile.d/node-ca.sh >/dev/null
sudo chmod +x /etc/profile.d/node-ca.sh
export NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt

# Shared Puppeteer cache so root-installed Chrome is visible to the session user.
sudo mkdir -p /opt/puppeteer-cache
sudo chmod -R 0755 /opt/puppeteer-cache
echo 'export PUPPETEER_CACHE_DIR=/opt/puppeteer-cache' | sudo tee /etc/profile.d/puppeteer-cache.sh >/dev/null
sudo chmod +x /etc/profile.d/puppeteer-cache.sh
export PUPPETEER_CACHE_DIR=/opt/puppeteer-cache

# Install puppeteer JS package globally. Postinstall downloads Chrome into
# PUPPETEER_CACHE_DIR. Both env vars must be passed through sudo explicitly
# since sudo strips the parent shell's environment by default.
sudo mkdir -p /opt/puppeteer
cd /opt/puppeteer
sudo NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt \\
     PUPPETEER_CACHE_DIR=/opt/puppeteer-cache \\
     npm init -y >/dev/null
sudo NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt \\
     PUPPETEER_CACHE_DIR=/opt/puppeteer-cache \\
     npm install --no-audit --no-fund puppeteer@24

# Expose the global install on NODE_PATH so the session can require it.
echo 'export NODE_PATH="/opt/puppeteer/node_modules:${NODE_PATH}"' | sudo tee /etc/profile.d/puppeteer-path.sh >/dev/null
sudo chmod +x /etc/profile.d/puppeteer-path.sh
```

This script installs the Chromium OS libraries `webinar-promo-card` needs (per §8), wires `NODE_EXTRA_CA_CERTS` so npm works through the cloud proxy, and installs `puppeteer@24` into a shared cache at `/opt/puppeteer-cache` that matches `PUPPETEER_CACHE_DIR` above. `webinar-promo-card`'s `SKILL.md` step 9a short-circuits if `puppeteer` is already present, so re-runs are cheap. `hxgtm-revops-pipelines` also ships a `SessionStart` hook (`.claude/settings.json`) that runs `scripts/install_card_skill_deps.sh` to pre-install Puppeteer for all five card skills (`webinar-promo-card`, `linkedin-case-study-promo`, `linkedin-image-ad-text-only`, `linkedin-customer-quote-card`, `linkedin-partnership-card`). That hook covers the npm package only; the cloud routine's setup script above is still required for the OS-level Chromium libs.

**6. Routine instructions field — refer to the VCS prompt:**

The instructions field on the routine should contain only this single line, exactly as in step 1 above:

```
For the instructions please refer to hxgtm/hxgtm-revops-pipelines/perkins-playbook-routine-prompt.md
```

This pulls the latest playbook routine prompt directly from the attached repo on every run, so updates ship via `git push` with no Notion edit needed.

---

## 7. Failure handling

The `TASK_RESULT` contract is binary: `completed` or `blocked`.

Three failure paths produce a `blocked` result:

- **Skill file missing** — reason names the missing skill and the expected path.
- **Subagent execution error** — reason includes the verbatim error text.
- **Broken playbook relation / unresolvable skill** — reason names the affected task.

A blocked task is **left at `In progress`** (the pipeline `Status` set at claim), with its `Agent Status` released to **Not started**. It is *not* reverted to the trigger status (`Generate Assets` / `Finalize & Publish Assets`) — that would re-fire the webhook and auto-retry a deterministic failure forever, which the routines forbid. A `### Blocked` block is appended under the routine's output section (Outputs section of Step 1: Generate Assets for stage-1, Outputs section of Step 2: Finalize & Publish Assets for stage-2). The card stays visibly `In progress` until a human reads the blocked log and re-queues it by re-dragging it to the trigger status. Failed runs stay visible alongside successful ones — the logbook is append-only.

### Partial failure caveat

If 2 of 3 skills succeed inside a task, current behavior reports `completed` with the missing skill silently absent. This is a known gap — there is no per-skill `blocked` partial result yet.

---

## 8. Environment setup for skills with dependencies

Some skills require binary or runtime dependencies that are not bundled with Claude Code:

- **`webinar-promo-card`** → `puppeteer` (npm) plus Chromium OS libraries (`libnss3`, `libgbm1`, `libasound2`, etc.).
- **`upload-to-notion`** → `bash`, `curl`, `jq`, `python3` (standard) **plus a Notion API key passed at invocation time**.

Setup is layered:

- **npm-level** — `webinar-promo-card`'s `SKILL.md` step 9a runs `node -e "require('puppeteer')" || npm install` in the skill's `scripts/` folder before the exporter, so Puppeteer self-installs on first use. `hxgtm-revops-pipelines` also ships `scripts/install_card_skill_deps.sh` — an idempotent installer covering all five card skills — wired to a `SessionStart` hook in `.claude/settings.json`, so a fresh local session pre-installs Puppeteer without waiting for first use.
- **Cloud-routine OS libs** — belong in the routine's setup script; documented in [`.claude/skills/webinar-promo-card/ROUTINE_INTEGRATION.md`](https://github.com/hx-gtm/hxgtm-revops-pipelines/blob/main/.claude/skills/webinar-promo-card/ROUTINE_INTEGRATION.md).
- **Cloud-routine gotcha** — `SessionStart` hooks load only from the **primary** repo, which is now `hxgtm-revops-pipelines` (which ships one — `scripts/install_card_skill_deps.sh`, run by a `SessionStart` hook in `.claude/settings.json`). `hx-plugins` is now a **secondary** repo, so its `SessionStart` hooks do not fire — the dispatcher must inject each `hx-plugins` skill via the `skills:` field so [SKILL.md](http://skill.md/) content reaches the subagent.

When introducing a new skill with binary deps, follow the same pattern: ship an idempotent install script under `scripts/`, gate it on a presence check, and document any OS-level libs in a `ROUTINE_INTEGRATION.md` next to the skill.

---

## 9. Notion API key caveat (`upload-to-notion`)

The MCP server (`hxgtm-mcp-server`) exposes Notion **read** context but does **not** support file uploads. Skills that write images or files into Notion (e.g. `webinar-promo-card` → `upload-to-notion`) bypass MCP and call the **Notion REST API directly** via `scripts/upload_to_notion.sh`. The skill requires a Notion API key passed as `notion_api_key` at invocation time — it reads no environment variable on its own.

Implications:

- The routine config must hold the Notion API key as a secret and inject it on dispatch.
- Skills that upload should declare this contract in their [SKILL.md](http://skill.md/) (`upload-to-notion` already does).
- Until MCP supports uploads, every new artifact-producing skill follows the same pattern: produce locally → chain to `upload-to-notion`.

---

## 10. *hx Sessions Promo Pack* — worked example

The first playbook to combine artifact generation, Notion upload, and a multi-skill bundle.

- **Skills (in playbook order):** `web-copy, linkedin, email, webinar-promo-card, save-to-notion, upload-to-notion`.
- **Card template — required fields:** Date, Time & Timezone, 2–3 Key Takeaways, and per-speaker paired fields `Speaker N: Name` / `Speaker N: Title` / `Speaker N: Headshot` (Speaker 1 required; Speakers 2–4 optional). The name+title and headshot are paired by the speaker number so each headshot is unambiguously tied to its speaker.
- **Card template — optional fields:** Target audience, Registration URL, Event name.
- **Dependencies:** Notion API key (per §9), Puppeteer + Chromium OS libs (per §8).

Cross-references:

- [`.claude/skills/webinar-promo-card/README.md`](https://github.com/hx-gtm/hxgtm-revops-pipelines/blob/main/.claude/skills/webinar-promo-card/README.md) — canvas spec, gradient picker, type specs, per-variant layouts.
- [`.claude/skills/upload-to-notion/SKILL.md`](https://github.com/hx-gtm/hxgtm-revops-pipelines/blob/main/.claude/skills/upload-to-notion/SKILL.md) — upload API, exit codes, retry behavior.
- [`.claude/skills/webinar-promo-card/ROUTINE_INTEGRATION.md`](https://github.com/hx-gtm/hxgtm-revops-pipelines/blob/main/.claude/skills/webinar-promo-card/ROUTINE_INTEGRATION.md) — env-side fixes for cloud routines.

---

## 11. Output rendering

Append-only logbook under the **Outputs section of Step 1: Generate Assets** on the card (stage-2 writes under the **Outputs section of Step 2: Finalize & Publish Assets**). Runs carry no timestamp and are separated by a `---` divider. Four layouts:

- **Single skill** — one block per run.
- **Multiple skills** — grouped by bold skill labels (`linkedin**`, `email**`, …).
- **Artifact skill** (image cards) — on success the card shows the embedded image(s) + caption(s) only, with **no** bold skill-name header and **no** run-summary prose. On a failed run (blocked, or `completed` with no image generated) the image is replaced by a single plain-text retry line — `There has been an error generating the <card label>. Please try again.` — never prose or a broken image.
- **Blocked** — a `### Blocked` heading with the reason text.

Editable drafts pair with read-only originals (draft first, original second). Both stay visible across runs.

---

## 12. Gotchas (consolidated)

- **Partial failure is undefined.** If 2 of 3 skills succeed inside a task, the run reports `completed` with the missing skill silently absent — see section 7. (**Artifact image skills are now guarded in both stages** for the no-image sub-case: a `completed` artifact run with zero primary images surfaces the retry line + `⚠ partial` instead of an empty output — see section 11.)
- **Positional pairing is fragile.** Reordering Skills without reordering Content Type / Guidance Type breaks wiring with no error — see section 5.
- **Shared card surfaces both stages' wiring.** A card exposes `Generate Assets Skill` *and* `Finalize & Publish Assets Skill` (plus the paired Content/Guidance columns) as rollups, and both routines write to the same page. A routine must execute only its owned column's skills (closed skill set) and write only to its owned output section, or stage-1 will run stage-2 skills (and vice versa) — see section 5a.
- **The concurrency lock is `Agent Status`; `Status` shows `In progress`.** The concurrency lock lives on the separate `Agent Status` (status-type) property; in addition, the routine sets the pipeline `Status` to `In progress` at claim so the board shows active work. `In progress` is not a watched trigger, so the flip never re-triggers a run. A blocked run leaves the card at `In progress` (never reverting to the trigger status, which would loop) — see sections 5a and 7.
- **`SessionStart` hooks don't fire in secondary repos.** `hx-plugins` is now the secondary clone, so dispatch must inject its (non-design) skills via the `skills:` field — see section 8.
- **MCP cannot upload files.** Notion file uploads bypass MCP and require a Notion API key passed at dispatch — see section 9.
- **Routine prompt must reference the VCS file**, not be pasted into Notion config — see section 6.

[Perkins Playbook Docs v1](https://www.notion.so/Perkins-Playbook-Docs-v1-35a824e1aca7800ca6aac2b88a552da8?pvs=21)

[Perkins Playbook Doc v2](https://www.notion.so/Perkins-Playbook-Doc-v2-365824e1aca7805a8ae3e97df8a44b3e?pvs=21)

[Perkins Playbooks Doc v3 vs v2](https://www.notion.so/Perkins-Playbooks-Doc-v3-vs-v2-365824e1aca780c58e67f048a16a60b5?pvs=21)