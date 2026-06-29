# Routine integration — webinar-promo-card

> **Migration note:** this skill was migrated from the `hx-plugins` repo. This doc is a historical postmortem of a cloud-routine incident that occurred while the skill lived in `hx-plugins`. It is kept for reference. The Perkins playbook routine prompt it references lives in the `hx-plugins` repo (`plugins/hx-marketing/perkins-playbook-routine-prompt.md`), not in this repo. Paths and hook references below describe the `hx-plugins` setup.

This doc is for the team that owns **marketing-task-board** (the orchestrator) and the **cloud-routine environment**. Repo-side fixes alone cannot make Puppeteer install reliably in routines that clone `hx-plugins` as a secondary repo. This doc spells out the changes that need to land outside this repo.

> Authoritative references:
> - [Routines](https://code.claude.com/docs/en/routines) — overview, environment selection
> - [Claude Code on the web — The cloud environment](https://code.claude.com/docs/en/claude-code-on-the-web#the-cloud-environment) — setup scripts, environment caching, SessionStart hooks in cloud sessions
> - [Setup scripts vs. SessionStart hooks](https://code.claude.com/docs/en/claude-code-on-the-web#setup-scripts-vs-sessionstart-hooks) — when to use which

## Symptom

A cloud-routine run of `webinar-promo-card` produces HTML in `[campaign-folder]/working/` but **no PNG** in `[campaign-folder]/export/`. The run summary contains phrasing like "this requires a local or Cursor environment" or "Puppeteer is not installed in this environment."

## Why our in-repo SessionStart hook does not fire in the routine

The docs explicitly state that only **the cloned repository's** `.claude/settings.json` is loaded by Claude Code in a cloud session. Routines support multiple repositories, but the project-root settings file Claude Code reads is the **primary repo's** — not every cloned repo's.

In the failing run, the marketing-task-board routine has its own primary repo. `hx-plugins` is added as an additional cloned repo. Result: our SessionStart hook at [`.claude/settings.json`](../../../.claude/settings.json) is never loaded, so `scripts/install_webinar_promo_card_deps.sh` never runs.

User-scope `~/.claude/settings.json` is **also** not respected in cloud sessions (per the docs: "user-level settings don't carry over to cloud sessions"). So that escape hatch is closed too.

The auto-install fallback in [`scripts/export_card.js`](scripts/export_card.js) does eventually save the day — but only if the subagent actually runs the export step. In the failing incident, the subagent emitted a hallucinated refusal and skipped step 9 entirely.

## Repo-side fixes already shipped

These reduce the blast radius but cannot replace the routine-side change:

- `SKILL.md` step 9: deps-check is now an explicit, mandatory bash command (step 9a) — not a "verify before exporting" suggestion. The forbidden-phrasing list in the runtime-compatibility section now covers the exact refusals seen in the failing run.
- `export_card.js` auto-install: now detects partial installs (`node_modules/puppeteer/` exists but `require()` throws), wipes the broken dir, reinstalls once, and only throws if the second `require` still fails. Logs to stderr at every step.
- `install_webinar_promo_card_deps.sh`: emits `[install_webinar_promo_card_deps] puppeteer ready at …` on both short-circuit and post-install paths, so any environment that *does* invoke it has positive proof in its log.
- `.claude/settings.json` hook: now falls back to `pwd` when `$CLAUDE_PROJECT_DIR` is unset and is wrapped in `|| true`. (Note: this only matters in environments that load this file at all — not the cloud-routine case described above.)

## Required changes (priority order)

### Preferred — Pass `skills:` on subagent dispatch

The most common failure mode for this skill in cloud routines is **not** missing libraries — the routine env has been correctly configured for months. The failure is the **dispatched subagent** emitting a hallucinated environment refusal because it never received the skill's SKILL.md content.

Per [Anthropic subagent docs](https://code.claude.com/docs/en/sub-agents): subagents do not inherit the orchestrator's loaded skills. The official mechanism to inject skill content into a subagent's startup context is the `skills:` field on the `Task` tool dispatch. Quote: *"`skills` — Skills to preload into the subagent's context at startup. The full skill content is injected, not just the description."*

When the orchestrator dispatches a subagent for a task that runs this skill, pass:

```yaml
subagent_type: general-purpose
skills:
  - webinar-promo-card
  - save-to-notion       # if the task uses save-to-notion
  - upload-to-notion     # webinar-promo-card chains to upload-to-notion in step 11
tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - mcp__claude_ai_Notion__notion-search
  - mcp__claude_ai_Notion__notion-fetch
  - mcp__claude_ai_Notion__notion-create-pages
  - mcp__claude_ai_Notion__notion-update-page
  - mcp__claude_ai_Notion__notion-append-block-children
prompt: <assembled subagent prompt — see perkins-playbook-routine-prompt.md Step 4b>
```

With `skills:` set, the subagent boots with the full SKILL.md text — including the forbidden-phrase list and the step 9a install fallback — already in context. The hallucinated refusal failure mode disappears.

The Perkins playbook routine prompt (`plugins/hx-marketing/perkins-playbook-routine-prompt.md` in the `hx-plugins` repo) Step 4b documents this dispatch contract.

This is the single highest-leverage fix. Options A–D below are belt-and-braces — they harden the env so that *if* the subagent does run step 9a, it succeeds.

---

### A. Add a setup script to the routine's cloud environment (most robust)

Per [Setup scripts](https://code.claude.com/docs/en/claude-code-on-the-web#setup-scripts), each routine's environment can ship a Bash setup script that runs as root **before Claude Code launches** and is cached at the filesystem level for ~7 days. This is the canonical place to install Puppeteer.

The setup script runs before repos are cloned, so it cannot reach `hx-plugins/scripts/`. Install Puppeteer into a known global location and the skill's auto-install will short-circuit on it.

#### Three non-obvious gotchas

All three bit successive versions of this routine's setup script:

1. **`npx puppeteer browsers install chrome` only installs the Chrome binary, not the puppeteer JS package.** `require('puppeteer')` still throws `MODULE_NOT_FOUND` and the export script falls into its local-`npm install` fallback, which redownloads Chrome anyway. The `browsers install` step ends up being wasted work. Fix: install puppeteer as a regular npm package — its postinstall downloads Chrome for free.
2. **Setup scripts run as root, but Claude Code sessions run as the `user` account.** Puppeteer's default cache is `$HOME/.cache/puppeteer/`, so a root-side install lands Chrome in `/root/.cache/puppeteer/` where the session user can't see it. Fix: pin `PUPPETEER_CACHE_DIR` to a shared, world-readable location and export it via `/etc/profile.d/` so both root and the session user agree on the path.
3. **`npm install` fails through the cloud environment's [security proxy](https://code.claude.com/docs/en/claude-code-on-the-web#security-proxy) with `SELF_SIGNED_CERT_IN_CHAIN`.** All outbound traffic is intercepted by a proxy that uses its own CA. `apt-get` succeeds because it uses the system CA bundle (`/etc/ssl/certs/ca-certificates.crt`); `npm` fails because Node ships its own bundled CA list and doesn't trust the system one by default. Fix: set `NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt` so Node trusts the system bundle. Also remember that `sudo` strips the parent shell's env vars unless you pass them inline (`sudo VAR=val cmd`).

#### Paste-ready script

Paste this into the **Setup script** field of the marketing-task-board routine's environment (Edit routine → environment → Setup script):

```bash
#!/bin/bash
set -e

# Chromium runtime libraries.
sudo apt-get update -y
sudo apt-get install -y --no-install-recommends \
  ca-certificates fonts-liberation \
  libasound2t64 libatk-bridge2.0-0t64 libatk1.0-0t64 libc6 libcairo2 \
  libcups2t64 libdbus-1-3 libexpat1 libfontconfig1 libgbm1 libglib2.0-0t64 \
  libgtk-3-0t64 libnspr4 libnss3 libpango-1.0-0 libpangocairo-1.0-0 \
  libstdc++6 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 \
  libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 \
  libxkbcommon0 libdrm2 libxss1 libxtst6 lsb-release wget xdg-utils

# Make Node trust the system CA bundle. Without this, npm fails through the
# security proxy with SELF_SIGNED_CERT_IN_CHAIN because Node ships its own
# bundled CA list, not the system one.
echo 'export NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt' | sudo tee /etc/profile.d/node-ca.sh >/dev/null
sudo chmod +x /etc/profile.d/node-ca.sh
export NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt

# Shared Puppeteer cache so root-installed Chrome is visible to the session user.
sudo mkdir -p /opt/puppeteer-cache
sudo chmod -R 0755 /opt/puppeteer-cache
echo 'export PUPPETEER_CACHE_DIR=/opt/puppeteer-cache' | sudo tee /etc/profile.d/puppeteer-cache.sh >/dev/null
sudo chmod +x /etc/profile.d/puppeteer-cache.sh
export PUPPETEER_CACHE_DIR=/opt/puppeteer-cache

# Install the puppeteer JS package globally. Postinstall downloads Chrome into
# PUPPETEER_CACHE_DIR — no separate `browsers install` step needed.
# Both env vars must be passed through sudo explicitly; sudo strips the parent
# shell's environment by default.
sudo mkdir -p /opt/puppeteer
cd /opt/puppeteer
sudo NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt \
     PUPPETEER_CACHE_DIR=/opt/puppeteer-cache \
     npm init -y >/dev/null
sudo NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt \
     PUPPETEER_CACHE_DIR=/opt/puppeteer-cache \
     npm install --no-audit --no-fund puppeteer@24

# Expose the global install on NODE_PATH so the session can require it.
echo 'export NODE_PATH="/opt/puppeteer/node_modules:${NODE_PATH}"' | sudo tee /etc/profile.d/puppeteer-path.sh >/dev/null
sudo chmod +x /etc/profile.d/puppeteer-path.sh
```

If `NODE_EXTRA_CA_CERTS` alone doesn't unblock npm (rare — would mean the proxy CA isn't in the system bundle), add this fallback right after the CA-trust block:

```bash
sudo npm config set strict-ssl false -g
```

Less secure (skips cert validation entirely) but always works. Try `NODE_EXTRA_CA_CERTS` first.

#### Confirming the session user

The script above assumes the session user is `user`. If that's wrong, the cache permissions need adjustment. Run a one-shot setup script first to confirm:

```bash
whoami; id; ls -la /home; echo "PUPPETEER_CACHE_DIR=${PUPPETEER_CACHE_DIR:-unset}"
```

The output appears in the routine's session log. Adjust `chmod`/paths above if the user differs.

#### Notes

- This works regardless of which repo is the routine's primary, and regardless of whether `hx-plugins` is even cloned.
- The Trusted network access level covers `registry.npmjs.org` and `archive.ubuntu.com` (per the [default allowlist](https://code.claude.com/docs/en/claude-code-on-the-web#default-allowed-domains)) — no custom network config needed.
- The setup script is cached, so the ~60s install only runs on environment changes or the ~7-day cache expiry. Both `/opt/puppeteer/` and `/opt/puppeteer-cache/` end up in the snapshot.
- Pinning `puppeteer@24` matches the version `export_card.js` expects. Bump in lockstep when upgrading.

### B. Add a SessionStart hook to the routine's *primary* repo

If the routine's primary repo is one you control (i.e., the marketing-task-board orchestrator repo), commit a SessionStart hook to its `.claude/settings.json` that runs the install script from the cloned `hx-plugins`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume",
        "hooks": [
          {
            "type": "command",
            "command": "bash -c 'for d in /home/user/hx-plugins ./hx-plugins ../hx-plugins; do if [ -x \"$d/scripts/install_webinar_promo_card_deps.sh\" ]; then \"$d/scripts/install_webinar_promo_card_deps.sh\"; break; fi; done; true'"
          }
        ]
      }
    ]
  }
}
```

This complements (or replaces) option A. Option A is preferred because it doesn't depend on the orchestrator's repo layout.

### C. Tell subagents the runtime files are on local disk

When the orchestrator dispatches a subagent for `webinar-promo-card`, the subagent prompt should include:

> The skill's runtime files (`scripts/`, `templates/`, etc.) are on the local filesystem at the cloned-repo path, not at a GitHub-API URL. Use the local path for any `node` or shell command. If `require('puppeteer')` fails, run `npm install` in the script directory per the skill's own fallback. Do **not** refuse with environment-availability claims like "this requires a local environment" or "node_modules is missing." See `.claude/skills/webinar-promo-card/SKILL.md` step 9 for the authoritative recovery procedure.

This closes Gap 2/3 from the original incident analysis (subagent hallucinated refusal).

### D. Confirm Chromium runtime libs are present

Option A's `apt-get` block handles this. If you implement only option B, add the same `apt-get install` line to a **setup script** anyway — Puppeteer's launch fails on a vanilla Ubuntu 24.04 image without these libs (`libnss3`, `libgbm1`, etc.). Without them you'll see `Failed to launch the browser process` even after Puppeteer installs cleanly.

### E. Add `GEMINI_API_KEY` as a routine secret

Step 6 of the skill (headshot cleanup) calls Google's Gemini Image API directly via `@google/genai` — there is no MCP dependency. The skill reads `GEMINI_API_KEY` from the environment and hard-fails verbatim if it is missing or the API rejects the call. There is no raw-photo fallback.

Add `GEMINI_API_KEY` as a **secret** on the routine's environment (Edit routine → environment → Secrets). The skill itself does not need any setup-script changes for this — `@google/genai` is declared in `scripts/package.json` and installs alongside Puppeteer when the skill's `npm install` runs (step 9a). The only routine-side requirement is the secret.

No other secrets are required by the cleanup step.

## Verifying the fix end-to-end

After Option A (or B) lands, fire a test run of the routine and confirm:

1. The session log shows the setup script (or hook) ran. For Option A, look for `added N packages` from the `npm install puppeteer` line. For Option B, look for `[install_webinar_promo_card_deps] puppeteer ready at …`.
2. The subagent for `webinar-promo-card` runs step 9a (`node -e "require('puppeteer')" …`) without error.
3. The campaign folder contains both `[slug].png` and `[slug]@2x.png` under `export/`.
4. The run summary contains **none** of the forbidden phrasings listed in `SKILL.md`'s "Runtime compatibility" section.

## When to revisit this doc

- If the docs change in a way that allows secondary-repo `.claude/settings.json` hooks to load, option B becomes redundant and we should simplify.
- If Chromium gets pre-installed in the default cloud-environment image, option D's `apt-get` block becomes redundant.
- If the skill stops using Puppeteer (e.g., switches to Playwright or a server-side renderer), the whole install path changes and this doc needs a rewrite.
