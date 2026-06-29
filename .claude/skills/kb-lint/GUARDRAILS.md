# kb-lint Guardrails

Identified failure modes, implemented protections, and known gaps.

---

## Implemented guardrails

### G1. Subagent finding verification

**Risk:** Orchestrator blindly trusts subagent output. A hallucinated finding
(e.g., false contradiction) could cause unnecessary remediation work.

**Protection:** For every High severity finding, the orchestrator spot-checks
by reading the cited file(s) and confirming the quoted text actually exists.
If the quote doesn't match, the finding is downgraded or removed and noted
as unverified.

**Where:** SKILL.md Step 5a (post-merge verification)

---

### G4. Subagent coverage confirmation

**Risk:** Subagent receives 30+ files but silently skips some due to context
pressure. No way to know what was actually analyzed vs skimmed.

**Protection:** Canon Analyzer must include a "Files read" appendix listing
every file it read in full vs files it only saw metadata for.

**Where:** canon-analyzer.md output format

---

### G6. Finding count sanity check

**Risk:** Subagent reports 0 findings for a large KB (100+ files) — likely
a silent failure, not a perfect KB.

**Protection:** If Canon Analyzer returns 0 findings for a KB with 100+
files, the orchestrator adds a warning note: "No findings reported. This
may indicate the subagent did not complete analysis. Consider re-running."

**Where:** SKILL.md Step 5a

---

### G7. Perplexity cost cap

**Risk:** External Verifier could make hundreds of Perplexity calls per run
if canon contains many verifiable claims, blowing through the API budget.

**Protection:** Hard cap of 30 calls per run. The verifier processes claims
in priority order (competitor → people → market → third-party) and stops
at 30. Claims beyond the cap are reported as "skipped (cap reached)" in
the verifier's statistics block. The orchestrator logs a warning if the
cap is hit and reports how many claims were deferred. If 0 calls are
reported but Phase 3 was enabled, a silent-failure warning is added.

**Where:** external-verifier.md Step 4 (cost cap), SKILL.md Step 5a

---

### G8. Verification source citation required

**Risk:** A Phase 3 finding without a source URL is unverifiable — the
human reviewer has no way to confirm the contradiction is real. Could lead
to canon being changed based on a hallucinated finding.

**Protection:** Every External Verifier finding must include the Perplexity
source URL. During Step 5a synthesis, the orchestrator drops any `E`
finding missing a source URL and logs the drop in the report's Statistics
section.

**Where:** external-verifier.md output format, SKILL.md Step 5a

---

## Known gaps (not yet implemented)

These are documented for future versions. They are real risks but require
more complex solutions than the current design supports.

### Finding persistence between runs

**Risk:** Can't track which findings were fixed vs missed by the LLM across
successive runs. A finding that disappears may have been fixed or may have
been missed non-deterministically.

**Mitigation needed:** A findings database or diff tool that compares
successive lint reports and highlights new/resolved/recurring findings.

---

### Non-determinism

**Risk:** Two runs on the same unchanged KB can produce different findings
because the analysis is LLM-based, not scripted.

**Mitigation needed:** Deterministic checks (scripted, not LLM) for
freshness calculations and cross-reference validation. LLM-based checks
(consistency, coverage) will remain inherently non-deterministic.

---

### File locking during scan

**Risk:** User edits canon files while subagents are reading them,
causing inconsistent state.

**Mitigation needed:** Git stash/worktree isolation before scan, or at
minimum a warning if files changed during execution.

---

### Canon path content validation

**Risk:** The filesystem fallback finds a directory with .md files but it's
not actually the hx KB (e.g., user pointed to wrong path).

**Mitigation needed:** Validate that expected sentinel files exist (e.g.,
`truth/brand/positioning.md`, `truth/audiences/_template-persona.md`).

---

### Reactive (no pre-flight) failure surfacing

**Risk:** kb-lint has no pre-flight validation wall or proceed gate — both
interactive and batch runs proceed optimistically and only surface
misconfiguration (wrong canon path, unreadable MCP) reactively when a step
tries to use it. A wrong/unreadable canon path isn't caught until
Step 3 attempts to read.

**Mitigation needed:** A lightweight, non-blocking startup check that logs
file existence / counts (canon readable) into the run log
without prompting — so a misconfigured run announces the problem up front
instead of part-way through indexing.
