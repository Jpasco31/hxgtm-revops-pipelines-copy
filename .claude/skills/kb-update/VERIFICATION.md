# kb-update / kb-integrate — Verification & Live Testing

Single source of truth for testing the skill. Two halves:

1. **Verification matrix** — 17 named checks, 14 automated, 3
   live-run. Keep the runner green before merging any change.
2. **Live testing walkthrough** — step-by-step exercises for the
   behaviours that can't be exercised offline (comparator quality,
   Notion MCP, real workspace flows).

**Automated runner:**
[`.claude/skills/kb-update/tests/run_checks.py`](tests/run_checks.py). Exits 0
on green, non-zero on any regression. Run it before merging any change
to the kb-update / kb-integrate scripts.

```
$ python3 .claude/skills/kb-update/tests/run_checks.py
=== automated verification ===

[PASS] D1 · publish EXPECTED_COLUMNS include new columns
[PASS] D2 · build_page skips Confidence + no [R{n}] re-wrap
[PASS] D3 · publish BATCH_SIZE == 50
[PASS] D4 · apply _infer_action produces expected action
[PASS] D5 · apply plan/apply stats expose needs_restage
[PASS] D6 · bottom-up replace handles two rows in one file
[PASS] D7 · post-apply readback catches failed write
[PASS] D8 · config.yaml loads with source_tiers + global + schema
[PASS] 10 · Final Updated Text wins via effective_text()
[PASS] 11 · Long-text replace via line+hash
[PASS] 12 · escape / unescape round-trip
[PASS] 13 · Drifted canon → needs_restage
[PASS] 15 · First-run path discovery writes .kb-local.json cache
[PASS] 16 · Zip-not-git precondition halts

Summary: 14 passed, 0 failed (of 14)
```

---

## Status legend

- ✅ **Automated** — verified by `run_checks.py`, runs on every
  invocation of the script. Script-level; no LLM or Notion needed.
- 🟡 **Live-run required** — behaviour depends on either an LLM
  subagent (comparator quality) or the Notion MCP / real workspace.
  Cannot be exercised offline. Use the live testing walkthrough
  below.
- 🔵 **Deferred** — feature not yet implemented. Revisit when the
  gated work lands.

## 17-check matrix

| # | Check | Status | Where verified |
|---|-------|--------|----------------|
| 1 | Perf: `/kb-update --group competitive` on Federato source <2min | 🟡 Live-run | Needs a real 2000-word raw source and Opus orchestrator. Observe the Timings block printed in the Step 7 summary (`parallel_comparators_ms`, `scope_narrowing_ms`, `publish_ms`). |
| 2 | Tier gating — vendor blog → tier_5, routed to Notes with "Vendor claim (unverified):" prefix | 🟡 Live-run | Comparator behaviour — needs a Sonnet subagent run. Verify in Notion DB: every row from the vendor source has `Source Tier = Tier 5`; zero rows target Strengths / Weaknesses / hx positioning; Notes rows' `Proposed Updated Text` starts with `Vendor claim (unverified):`. |
| 3 | Tier gating — LinkedIn/Teams → tier_4, route to Notes with `Informal (unverified):` prefix, `informal-unverified` tag, and significance-gate filtering | 🟡 Live-run | Upload a LinkedIn-sourced `.md` with `source_type: linkedin_post`. Run `/kb-update --group competitive` — expect findings that clear the significance gate to publish to Notion with `Target = Notes / open questions`, `Source Tier = Tier 4`, `Proposed Updated Text` starting with `Informal (unverified):`. Low-signal candidates counted as `dropped_tier4_low_signal` in Step 7 stats. No halt. |
| 4 | Core products scope gate — file WITH section: niche demoted to Notes, structural flows normally | 🟡 Live-run | Comparator gate — needs Sonnet run against a canon file carrying `## Core products`. Inspect Step 7 stats: `scope_gate_miss: N` for niche findings; structural findings land in their target section. |
| 5 | Core products scope gate — file WITHOUT section: graceful degradation, all findings flow normally | 🟡 Live-run | Run against a canon file with no `## Core products` section. Expect `scope_gate_skipped: N` in stats and every row routed by tier without gating. |
| 6 | Quote paraphrase — `internal-only` refuses ≥5-word verbatim, named carriers replaced with tier descriptors | 🟡 Live-run | Upload a Gong transcript with `confidentiality: internal-only`. Spot-check 5 rows' `Proposed Updated Text` against the source — no 5+ word verbatim matches, no named carriers. `dropped_quote_verbatim: N` in stats. |
| 7 | Replace-at-cap — Strengths at 6 bullets + new tier_1 finding emits `action: replace` with eviction candidate | 🟡 Live-run | Point the comparator at a canon file whose Strengths already has 6 bullets. Expect a published row with `Current Text` = weakest existing bullet, `Proposed Updated Text` = the new claim. `replace_at_cap: N` in stats. |
| 8 | Dedup — overlapping findings across parallel subagents collapse to single Notion rows | 🟡 Live-run | Orchestrator Step 4.5 (AI dedup). Run against a source the comparator would legitimately surface from multiple entities. Inspect Step 7 report's dedup section — `[orchestrator_dedup] input=N output=M dropped=K`. Notion should show only the canonical version per claim. |
| 9 | Input routing — URL paste → silent fetch, Teams → Glean, PDF/DOCX → auto-convert and proceed, image/binary → clean refusal | 🟡 Live-run | Implemented in SKILL.md Step 1b (URL fetch via `WebFetch`, Teams auto-route to Glean, PDF/DOCX auto-conversion via `scripts/convert_to_markdown.py`, image/archive clean refusal, inline-paste path). Live-run only because behaviour is orchestrator-driven (not a script). Exercise via `/kb-update --group competitive <url>`, attaching a `.pdf`, attaching a `.png` (refusal), etc. See §8 of the live walkthrough below. |
| 10 | Partial approval — `Final Updated Text` wins over `Proposed Updated Text` | ✅ Automated | `run_checks.py` check 10. End-to-end: builds a row with both fields set and verifies canon receives Final Updated Text, not Proposed. |
| 11 | Long-text replace (>2000 chars) succeeds via line+hash | ✅ Automated | `run_checks.py` check 11. Replaces a 3-line canon span with a ~4000-char block; asserts success + canon contains the full block. |
| 12 | Round-trip fidelity — `*italic*` / `**bold**` markers intact after apply | ✅ Automated | `run_checks.py` check 12. Escapes all five markdown characters (`*`, `_`, `#`, `` ` ``, `~`), round-trips through publisher → apply → canon, asserts markers are restored and placeholders don't leak. |
| 13 | Drifted canon → `Needs Restage` in <1s, no multi-minute hang | ✅ Automated | `run_checks.py` check 13. Corrupts canon between hash-capture and apply; asserts the row lands as `needs_restage`, proposed text doesn't leak. |
| 14 | One-flow `/kb-integrate --group competitive` — plan → summary → single prompt → edits land | 🟡 Live-run | Requires a real Notion workspace with Approved rows. Run without flags; verify AskUserQuestion appears with three options (`[a]pply / [p]review full / [c]ancel`); pick `apply`; inspect `git diff` in hxgtm-mcp-server. |
| 15 | First-run path discovery via `.kb-local.json` scan of dev roots | ✅ Automated | `run_checks.py` check 15. Deletes `.kb-local.json`, invokes the shared resolver at `.claude/skills/kb-update/scripts/resolve_mcp_path.py`, verifies a first-run miss locates the adjacent clone AND writes cache, and a second run hits the cache (`source: cache`). Resolver also handles `$HXGTM_MCP_SERVER_PATH` env var and a dev-root scan across `~/Desktop`, `~/dev`, `~/code`, `~/Projects`. The resolver lives at `.claude/skills/kb-update/scripts/resolve_mcp_path.py`. |
| 16 | Zip-not-git precondition halts with `git clone` instruction | ✅ Automated | `run_checks.py` check 16. Points `--mcp-server-path` at a directory with `context/` but no `.git/`; asserts exit code ≠ 0 and the halt message carries both `not a git clone` and the `git clone` command. |
| 17 | Readback retry — after `--apply`, one `notion-fetch` per integrated row confirms `Status = Integrated` | 🟡 Live-run | Orchestrator-level (SKILL.md Step 7, RC 7e). Verify by scanning the kb-integrate run log for one `notion-fetch` per `status == "success"` row. One retry on mismatch; persistent mismatch logs to the Step 8 error list and leaves the row at `Approved`. Needs Notion MCP to exercise. |

## Derived invariants (script-level)

Eight extra invariants the runner enforces automatically — they're not
in the numbered list above but guard against regressions introduced
during future edits:

| ID | Invariant | Rationale |
|----|-----------|-----------|
| D1 | `publish_to_notion.EXPECTED_COLUMNS` carries every new column | `--check-schema` is the only pre-flight guard before publish; if this drifts, schema mismatches go silent. |
| D2 | `publish_to_notion.build_page` does NOT write `Confidence` and does NOT re-wrap `Name` with `[R{n}]` | Both were behaviour changes baked in earlier. Regression here would double-prefix titles and pollute the deprecated Confidence column. |
| D3 | `publish_to_notion.BATCH_SIZE == 50` | Performance budget. Higher values risk Notion rate limits on large runs. |
| D4 | `apply_integrations._infer_action` returns `append` for empty `current_text` and `replace` otherwise (explicit `action` overrides) | The action field isn't a Notion column; all downstream behaviour hinges on this inference. |
| D5 | `_plan_stats` and `_apply_stats` both surface `needs_restage` | Stats feed the Step 8 report; missing this counter hides drift from the user. |
| D6 | Bottom-up replace handles two rows targeting different spans in the same file without anchor drift | The bottom-up ordering is the whole point of the apply rewrite. End-to-end harness verifies both rows succeed. |
| D7 | `_verify_post_apply` downgrades `success → failure` when `effective_text` isn't present in the re-read file | Unit-tests the readback directly. Catches silent-write bugs that would otherwise flip the Notion row to `Integrated` despite unchanged canon. |
| D8 | `config.yaml` parses with pyyaml and carries `source_tiers`, `global`, and the full competitive `section_schema` | Schema is the foundation for everything downstream. |

### U1 — Union honoured (orchestrator-level)

If the Step 1b `[inputs] … total=<S>` log line reports `total ≥ 2`,
the Step 7 report's `Inputs:` line MUST account for every surface
counted (attachments + url + inline + raw_eligible = total) and the
run MUST have executed batch mode. Any deviation is a skill violation
and must be called out in the Step 7 report preamble with an explicit
reason (e.g. "operator cancelled via AskUserQuestion", "--batch
override narrowed to <path>"). Silent narrowing — the orchestrator
dropping a surface because it "looks unrelated" to another surface —
is never acceptable. Enforced by the SKILL.md Step 1b "CRITICAL — union
is non-negotiable" banner; audited by reviewers by diffing the Step
1b log line against the Step 7 `Inputs:` line.

## Regression policy

1. Any change to [publish_to_notion.py](scripts/publish_to_notion.py),
   [synthesize_findings.py](scripts/synthesize_findings.py),
   [apply_integrations.py](../kb-integrate/scripts/apply_integrations.py),
   or [config.yaml](config.yaml) must leave `run_checks.py` green.
2. Any change to the EXPECTED_COLUMNS / REQUIRED_FINDING_FIELDS /
   validation sets in `publish_to_notion.py` must be accompanied by a
   matching D1 / D2 update in the runner.
3. When new numbered checks come off the deferred list, add matching
   cases to `run_checks.py` and update this matrix.

---

# Live testing walkthrough

Action-oriented guide for exercising every implemented behaviour
end-to-end. Expect **45–60 min** if every step lands cleanly. Most of
it is waiting on Sonnet subagents for the comparator checks.

## 0 · Automated suite — run first, before anything else

```bash
python3 .claude/skills/kb-update/tests/run_checks.py
```

Expect `14 passed, 0 failed`. If anything is red, stop — the live
tests below will compound the failure.

## 1 · First-time setup (~5 min)

### 1.1 Path discovery

```bash
# Wipe any existing cache so you see the discovery happen.
rm -f .kb-local.json

# Run the resolver directly.
python3 .claude/skills/kb-update/scripts/resolve_mcp_path.py mcp-path
```

Expected: JSON with `"source": "adjacent"` (or `"scan"` if you keep
the repo under a non-adjacent dev root) and `"cached": false`.
Inspect `.kb-local.json` — should carry the resolved absolute path.

```bash
# Second invocation — confirm the cache hit.
python3 .claude/skills/kb-update/scripts/resolve_mcp_path.py mcp-path
```

Expected: `"source": "cache"`, `"cached": true`, `duration_ms` in
single digits.

### 1.2 Zip-download guard

```bash
mkdir -p /tmp/fake-zip/context
HXGTM_MCP_SERVER_PATH=/tmp/fake-zip python3 .claude/skills/kb-update/scripts/resolve_mcp_path.py mcp-path
# Expect: "ERROR: hxgtm-mcp-server at /tmp/fake-zip is not a git clone …"
# Exit code 1.
rm -rf /tmp/fake-zip
```

### 1.3 Notion provisioning (skip if already done)

```bash
# One-time — create the "KB - Updates Review" landing page manually in
# Notion (see .claude/skills/kb-update/README.md §Notion database setup), then:
/kb-update --notion-setup
```

Expect either "All 11 groups already provisioned" (if you've run this
before) or a summary of databases created. Either is fine.

## 2 · Single-source happy path (~3 min)

**Setup:** grab a recent Gong call transcript or analyst brief on a
competitor that has a canon file (e.g. Akur8, Earnix, Artificial).
Save as `/tmp/sample-brief.md` with frontmatter:

```yaml
---
source_type: gong_call
source_title: "Carrier X vs <competitor> — 2026-04-15"
confidentiality: internal-only
---
```

(Content below — 500–2000 words.)

**Run:** attach the file to the Claude Code desktop chat and type:

```
/kb-update --group competitive
```

**What to watch:**
- Step 2 pre-flight — MCP server path row shows `source: cache` on
  the second run.
- Step 4 — the fan-out log shows
  `[parallel_comparators] entities=N duration_ms=…`. N should match
  the number of competitor entities detected in the brief.
- Step 4.5 — orchestrator dedup log:
  `[orchestrator_dedup] input=X output=Y dropped=Z`.
- Step 7 summary — look for `By tier`, `By scope`, and the timings
  block:
  ```
  Timings (ms):
    scope_narrowing:      <5000
    parallel_comparators: <60000
    publish:              <15000
    total:                <120000
  ```
  That satisfies **Check 1 (perf)** — p50 budget <2 min.

**In Notion:** open `KB - Competitive Intelligence`, switch to the
`Triage` view. Every new row should carry `Entity`,
`Source Tier = Tier 1`, `Claim Scope ∈ {Structural, Niche, Unscoped}`,
a populated `Target Line Start / End / Content Hash`, and a body with
the Landing preview code block.

## 3 · Tier gating (~5 min) — Checks 2, 3

### 3.1 Vendor (tier_5) — Check 2

Download a vendor marketing blog post as markdown, add:

```yaml
---
source_type: vendor_blog
source_url: "https://<competitor>.com/blog/<post>"
---
```

Run `/kb-update --group competitive`. Expected:
- Step 7 `By tier` line shows all findings under `tier_5`.
- Every published row's `Target file` references a competitor canon
  file, the `Target` section is `Notes / open questions`.
- Every row's `Proposed Updated Text` starts with
  `Vendor claim (unverified):`.

### 3.2 Informal external (tier_4) — Check 3

Create a file with just:

```yaml
---
source_type: linkedin_post
source_url: "https://www.linkedin.com/feed/update/<id>"
---

(body text from the post — include at least one item that clears the
significance gate, e.g. a specific dated product launch or named
customer win, plus some generic filler that should get dropped)
```

Run `/kb-update --group competitive`. Expected: **no halt**. Comparators
run against the competitor's canon and emit only findings that clear
the tier 4 significance gate. In Notion:

- Every published row's `Target` is `Notes / open questions`.
- Every published row's `Source Tier` is `Tier 4`.
- Every row's `Proposed Updated Text` starts with
  `Informal (unverified):`.
- Rows carry the `informal-unverified` tag in rationale.

In the Step 7 stats:

- `dropped_tier4_low_signal: N` — count of candidates filtered by the
  significance gate.
- `By tier: tier_4 [M]` — count of rows that made it through.

Pick one published row, flip to `Approved` in Notion, run
`/kb-integrate --group competitive --apply`. Verify the Notes bullet
lands in the target canon file's `Notes / open questions` section.

## 4 · Core products scope gate (~5 min) — Checks 4, 5

### 4.1 File WITH Core products — Check 4

Pick a competitor file that already has a `## Core products` section
authored (or author one as a one-off). Upload a tier_1 brief that
mentions both a legitimate Core-products-tied feature AND a niche
one-off integration.

Expected:
- Findings tied to a listed product → internal `claim_scope =
  structural`, `core_product` set. (Both fields are internal to the
  finding JSON — they drive routing but are not published to
  Notion.)
- Niche findings → demoted to `Notes / open questions`, internal
  `claim_scope = niche`.
- Step 7 stats: non-zero `scope_gate_miss`.

### 4.2 File WITHOUT Core products — Check 5

Pick a competitor file that does NOT yet have `## Core products`.
Upload a tier_1 brief. Expected:
- Every finding carries internal `claim_scope = unscoped`.
- Step 7 stats: non-zero `scope_gate_skipped`, zero `scope_gate_miss`.
- No rows demoted to Notes on the basis of the gate.

## 5 · Quote paraphrase (~5 min) — Check 6

Take a Gong transcript with direct customer quotes (≥20 words
verbatim). Confirm the frontmatter has
`confidentiality: internal-only`. Run `/kb-update --group
competitive`.

For 5 published rows, diff the source file's quote text against the
row's `Proposed Updated Text`:

```bash
# Spot-check — no 5-consecutive-word verbatim matches.
python3 - <<'PY'
import re
src = open("/tmp/gong-transcript.md").read().lower()
proposed = "<paste Proposed Updated Text here>".lower()
src_words = re.findall(r"\w+", src)
prop_words = re.findall(r"\w+", proposed)
for i in range(len(prop_words) - 4):
    needle = " ".join(prop_words[i:i+5])
    src_concat = " ".join(src_words)
    if needle in src_concat:
        print("VERBATIM LEAK:", needle)
PY
```

Expected: nothing prints. Named carriers referenced in the source
should appear as tier descriptors (`"a named tier_1 carrier"`, `"a
top-5 UK insurer"`) in `Proposed Updated Text`; raw quotes stay in
`Rationale` only. Step 7 may report `dropped_quote_verbatim: N > 0`
if the comparator had to drop any findings that couldn't be
paraphrased cleanly.

## 6 · Replace-at-cap (~3 min) — Check 7

Find a canon file whose `## Strengths` section has **exactly 6
bullets**. Upload a tier_1 brief with a single genuinely new strength
tied to one of the file's Core products.

Expected: one Notion row with `Action: replace`:
- `Current Text` = the weakest existing Strengths bullet (the one
  the comparator proposes to evict).
- `Proposed Updated Text` = the new bullet.
- Internal `claim_scope = structural`, `core_product` set (visible
  in the synthesis JSON, not in Notion).

Step 7: `replace_at_cap: 1`. Approve it in Notion → §10 below shows
what happens next.

## 7 · Dedup (~5 min) — Check 8

Upload a brief that discusses a claim appearing in BOTH a specific
competitor file AND `truth/market/competitors.md` (e.g. "Akur8's new
Pricing module" — Akur8's own file and the cross-competitor summary
both care).

Expected: Step 7 summary shows the orchestrator dedup log
`[orchestrator_dedup] input=X output=Y dropped=Z` with non-zero
`dropped`. In Notion, no two rows share identical `Proposed Updated
Text` on different `Target file` values — dedup kept the canonical
version.

## 8 · Input routing (~5 min) — Check 9

### 8.1 URL argument

```
/kb-update --group competitive https://www.gartner.com/en/some-piece-attributing-a-competitor
```

Expected: silent fetch, no "what's the source type?" prompt.
`source_type` inferred from the domain → `tier_1`. Findings land
under the normal flow.

### 8.2 Teams link

```
/kb-update --group competitive https://teams.microsoft.com/l/message/<id>
```

Expected: auto-routes to Glean if available. If Glean isn't
connected, you'll get a single AskUserQuestion with two options
(paste inline / cancel). No silent fetch attempt.

### 8.3 PDF / DOCX auto-conversion

Attach a PDF (or DOCX) file with extractable text to the chat. Type
`/kb-update --group competitive`.

Expected: no halt. Step 1b log line shows the attachment count, the
ephemeral tempfile under `/tmp/kb-update-raw/<run-id>/<stem>.md`
contains a `<!-- kb-update conversion · ... -->` provenance comment,
and the comparator pipeline runs as if a `.md` was attached.

For a scanned/image-only PDF, the converter exits 5 with the
"OCR required" message and the run halts cleanly — no synthesis
attempt, no partial publish.

### 8.4 Image / unsupported binary refusal

Attach a `.png` (or `.zip`, etc.) to the chat. Type `/kb-update
--group competitive`.

Expected: single clean halt with the unsupported-attachment banner:

```
/kb-update only handles markdown (.md), PDF, or DOCX attachments,
inline-pasted markdown, or HTTP(S) URLs. <filename> isn't supported.
Excerpt the relevant content and paste it inline, or attach a
supported format.
```

No detour questions, no partial publish.

### 8.5 Inline paste

Type (all in one message):

```
/kb-update --group competitive

# Competitor X Q2 summary
- New integration with Salesforce announced.
- Pricing module launch slipped to Q4.
```

Expected: one AskUserQuestion for optional `source_title` / `url` /
`type`. Fill them in (or skip); flow proceeds. Filename in the Notion
rows: `inline-paste-<today>.md`.

## 9 · Auto-batch mode (~10 min)

Auto-batch fires on **any plural input**. You don't need `--batch
<path>` — the skill detects the shape and routes itself.

### 9.1 Multiple chat attachments → auto-batch

Drag 3 `.md` files into the Claude Code desktop chat in the same
message, type:

```
/kb-update --group competitive
```

Expected:
- Step 1b decision log: `shape=chat-attachments count=3 → auto-batch`.
- No prompt, no halt — plural attachments are unambiguous intent.
- Step 1c fires a single wave (3 raw files × ~N entities detected per
  file ≈ 9–15 Sonnet subagents in one Agent message).
- Wave-level log:
  `[batch_wave] wave=1 files=3 subagents=M duration_ms=T`.
- Step 4.5 orchestrator dedup; Step 6 single batched publish.

### 9.2 `raw/<slug>/` auto-detection → auto-batch

Drop files into the group's raw folder (recursive — any subfolder
works) and run the command with **zero attachments** and no flag:

```bash
# Drop files wherever it's convenient — the entire raw/<slug>/ tree
# (loose top-level + typed subfolders) is gitignored except INDEX.md.
cp /tmp/akur8-brief.md raw/competitive/deep-research/
cp /tmp/earnix-news.md raw/competitive/clippings/
cp /tmp/quick-note.md raw/competitive/         # loose — also ignored

ls -R raw/competitive/ | head -20
```

Then:

```
/kb-update --group competitive
```

(Note: no files attached to the chat, no flag.)

Expected:
- Step 1b decision log:
  `shape=raw-group-dir path=raw/competitive/ count=N → auto-batch`.
- Scan is **recursive** and excludes any `INDEX.md` files.
- Same wave fan-out as 9.1; same publish path.
- **Everything stays local** — `git status` should show no new
  untracked files. Verify with:

  ```bash
  git check-ignore raw/competitive/quick-note.md \
                   raw/competitive/deep-research/akur8-brief.md
  ```

  Both should print (meaning ignored).

### 9.3 Explicit `--batch <path>` override

If you want to batch from a non-default directory:

```
/kb-update --group competitive --batch /path/to/custom/dir
```

Expected: bypasses auto-detection; runs on `<path>` directly.

### 9.4 Single-attachment fallback (regression check)

Drop ONE `.md` in the chat, run `/kb-update --group competitive`.

Expected: `shape=single-attachment → single-source mode`. No wave,
no cross-file dedup. Single-source flow behaves exactly as before
the auto-batch feature landed.

### Common to all three batch triggers

- **Parallelism is nested** — one wave spans multiple raw files, and
  within each file there's one subagent per detected entity. Total
  concurrency per wave:
  `min(batch_wave_size, file_count) × avg_entities_per_file`.
- Step 4.5 orchestrator dedup runs across **every** finding in the
  batch.
- Step 6 publishes once, not per file.
- Step 7 summary lists per-file finding counts + dedup counts + total
  wall time.

## 10 · kb-integrate end-to-end (~5 min) — Checks 10, 14, 17

Pre-condition: approve 3–5 rows in Notion (mix replace + append).

### 10.1 One-flow interactive (Check 14)

```
/kb-integrate --group competitive
```

Expected: plan computes, compact summary prints, prompt:

```
Apply <N> edits to canon?
(<R> replace / <A> append · <S> needs restage · <K> skipped)

  [a]pply · [p]review full · [c]ancel
```

Pick `[p]review full` → see the full Step 5 preview, re-prompt.
Pick `[a]pply` → disk writes + Notion Status flips.

### 10.2 Partial approval (Check 10)

On one Approved row, fill in `Final Updated Text` with a reviewer tweak.
Re-run `/kb-integrate --group competitive --apply`.

Expected: canon file receives the `Final Updated Text` content, NOT the
`Proposed Updated Text`. Verify:

```bash
cd $HXGTM_MCP_SERVER_PATH
git diff context/ | grep -A2 "<your edited text snippet>"
```

### 10.3 Readback retry (Check 17)

Watch the kb-integrate orchestrator output during `--apply`. For
each `status = success` row, you should see:
- A `notion-update-page` tool call setting `Status = Integrated`.
- A matching `notion-fetch` readback confirming it landed.
- On a transient mismatch, one retry; persistent mismatch logs to
  the Step 8 error list and leaves the row at `Approved`.

## 11 · Drifted canon (~3 min) — Check 13

Set up deliberate drift:

```bash
# Approve a row in Notion, but DON'T run kb-integrate yet.
# Hand-edit the target line in canon between publish and integrate:
cd $HXGTM_MCP_SERVER_PATH
sed -i.bak '117s/.*/HAND EDITED LINE/' context/guidance/competitive/competitors/<target>.md

# Now integrate.
cd -
/kb-integrate --group competitive --apply
```

Expected: that row lands as `NEEDS RESTAGE` in the plan preview +
apply results. No disk touch. Notion row flips to `Needs Restage`.
Step 8 summary tells you to re-run `/kb-update` on the drifted
source.

Cleanup:

```bash
cd $HXGTM_MCP_SERVER_PATH
mv context/guidance/competitive/competitors/<target>.md.bak \
   context/guidance/competitive/competitors/<target>.md
cd -
```

## 12 · Long-text replace (~2 min) — Check 11

Already verified in `run_checks.py` automatically. If you want to
eyeball it live, approve a row whose `Proposed Updated Text` exceeds
2000 chars (e.g. a full paragraph rewrite). Run `/kb-integrate
--apply` — expect `status: success`, no `"text not found"` message,
and canon receives the full ~4000-char block.

## 13 · Round-trip fidelity (~2 min) — Check 12

Upload a source containing `*italic*` and `**bold**` markers that the
comparator will echo into `proposed_text`. Run `/kb-update`, then
`/kb-integrate --apply`.

Inspect canon after integrate:

```bash
cd $HXGTM_MCP_SERVER_PATH
grep -n "<your marker text>" context/guidance/competitive/…/*.md
```

Expected: `*italic*` and `**bold**` are intact. No `⟪ast⟫` / `⟪us⟫`
placeholders leak into canon.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| "could not locate hxgtm-mcp-server" | Clone isn't under `~/Desktop`, `~/dev`, `~/code`, `~/Projects`, and no `HXGTM_MCP_SERVER_PATH` set | Set the env var, or `git clone` adjacent to this repo |
| "not a git clone" | Zip-download, not a proper clone | `git clone git@github.com:hx-gtm/hxgtm-mcp-server.git` |
| Row status doesn't flip to Integrated | Notion MCP readback retry logged a failure — check the Step 8 error list; manually flip if needed |
| `run_checks.py` exits 1 on a re-run | `.kb-local.json` was left from a partial test — `rm .kb-local.json` and re-run |
| Comparator emits zero findings | Source body didn't match any canon stem + no aliases configured — check the `[scope_narrowing] FALLBACK` log line |

## Deferred (not implemented, not testable)

These were explicitly scoped out; attempting to test them will fail.

- **Inline confidential markers** — the paraphrase rule + frontmatter
  `confidentiality: internal-only` cover the common path; revisit
  only if a leak incident forces it.
- **Batch resumability** (`_batch-state.json`) — add when someone
  actually Ctrl+Cs a real batch and loses work.
- **Structured telemetry (6 named log events)** — simple phase timers
  already cover the common bottleneck cases.
- **Section schemas for the other 10 groups** (messaging, audiences,
  channel-playbooks, …) — only `competitive` has one today. Port the
  pattern after competitive validates in production.
- **File-level size caps** — per-section caps cover most bloat.
- **Automated replace-at-cap eviction ranker** — reviewer decides
  today; add a ranker only if reviewers consistently disagree.
