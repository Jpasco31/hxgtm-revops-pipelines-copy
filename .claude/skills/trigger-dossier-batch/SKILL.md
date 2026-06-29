---
name: trigger-dossier-batch
argument-hint: "\"Account A\" \"Account B\" ... [--waves N]"
description: >
  Fire the Account Dossier batch cloud routine from a Claude session — the
  Claude-native replacement for the old n8n form. Collects an account list,
  builds the routine trigger payload, and POSTs it to the cloud routine's
  /fire endpoint so a batch dossier run starts unattended (outputs to Notion
  + the local hxgtm-mcp-server copy). Use when the user asks to "trigger a
  dossier run", "kick off / start an account dossier batch", "fire the dossier
  routine", "run dossiers in the cloud", or "replace the n8n dossier trigger".
  NOT for generating dossiers in the current session — that is /generate-dossier.
  This skill only fires the remote routine; it does not generate anything itself.
---

# Trigger Dossier Batch

## What this skill does

Fires the **Account Dossier batch cloud routine** by POSTing an account list to its API trigger — the
exact request the retired n8n workflow used to send. The remote routine then runs `/generate-dossier`
in the cloud and publishes one Notion page per account (plus the `hxgtm-mcp-server/context/accounts/`
copy). This skill is **just the trigger**; it does not generate dossiers locally — for that, use
`/generate-dossier`.

It is usable in **Claude Code** (as `/trigger-dossier-batch`) and, once the skill folder is uploaded to
claude.ai, in **Claude chat / cowork** too. The fire itself is an HTTPS POST run by
`scripts/fire.sh`, so it needs a shell with outbound network (Claude Code and cowork have this; for
claude.ai chat, confirm the environment allows egress).

## Usage

```
/trigger-dossier-batch "Zurich North America" "The Hartford" "AXA XL"
/trigger-dossier-batch "Zurich North America, The Hartford, AXA XL"
```

- **Accounts** come from `$ARGUMENTS` — either space-separated quoted names or a single comma-separated
  string (quote any name that itself contains a comma, e.g. `"Everest Re Group, Ltd."`). Both forms
  normalize to the same payload.
- **`--waves N`** is accepted for parity with the old n8n form but **currently has no effect**: the
  `generate-dossier` skill hardcodes its wave size to 3 and ignores this value. Omit it unless you have a
  reason; it defaults to `3`.
- **Comma-in-name limitation:** the payload joins accounts into one comma-separated string (n8n parity),
  so a comma is always read as a separator downstream. Pass multiple accounts as **separate quoted args**
  (a single arg with a comma is split). Account names that themselves contain a comma — e.g.
  `"Everest Re Group, Ltd."` — can't be represented unambiguously in this format (same limitation the old
  n8n form had); use the comma-free form of the name if the routine mis-splits it.

## Requirements (hard stops)

Both environment variables must be set before firing (the script exits non-zero with a clear message if
either is missing):

| Variable | Value |
| --- | --- |
| `DOSSIER_ROUTINE_TOKEN` | The routine API token (`sk-ant-oat01-…`) from the routine's API trigger. **Secret — never hardcode it in this skill or commit it.** |
| `DOSSIER_ROUTINE_ID` | The trigger id (`trig_…`) from the routine's trigger URL. Point this at your **test** routine while testing, then at the prod routine to cut over. |

There is **no baked-in routine id** on purpose: you must consciously choose which routine you fire.

**Where to set them:** the recommended home is this repo's **gitignored** `.claude/settings.local.json`
under an `env` block — Claude Code injects it into every Bash call, so the values are available with no
per-session export and are never committed:

```jsonc
{ "env": { "DOSSIER_ROUTINE_TOKEN": "sk-ant-oat01-…", "DOSSIER_ROUTINE_ID": "trig_…" } }
```

(A plain `export` in your shell also works for a one-off; it just doesn't persist across sessions.)

## How to run it

1. Parse the account names and any flags from `$ARGUMENTS`.
2. Run the fire script, passing **each account as its own quoted argument** plus any flags (do not pass
   `$ARGUMENTS` as a single blob — the script needs the accounts separated so it can build the payload):

   ```bash
   bash .claude/skills/trigger-dossier-batch/scripts/fire.sh "Zurich North America" "The Hartford"
   ```

   A single comma-separated string also works (the script splits and trims it):

   ```bash
   bash .claude/skills/trigger-dossier-batch/scripts/fire.sh "Zurich North America, The Hartford"
   ```

   (When this skill runs as an uploaded claude.ai skill, call `scripts/fire.sh` relative to the skill
   folder instead of the repo path.)
3. Show the user the parsed account list, then fire. The script prints the payload it sends, so the user
   can confirm it after the fact.
4. Report the routine's response and point the user to `claude.ai/code/routines` to watch the run.

## The request it sends (for reference)

```
POST https://api.anthropic.com/v1/claude_code/routines/<DOSSIER_ROUTINE_ID>/fire
Authorization: Bearer <DOSSIER_ROUTINE_TOKEN>
anthropic-beta: experimental-cc-routine-2026-04-01
anthropic-version: 2023-06-01
Content-Type: application/json

{"text": "{\"accounts\": \"Zurich North America,The Hartford,AXA XL\", \"waves\": 3}"}
```

The body's `text` is itself a JSON string (`{"accounts": "...", "waves": N}`) — the routine prompt parses
it into the `/generate-dossier` account list. This payload is byte-identical to what the n8n workflow
produced, so the same routine accepts it unchanged.
