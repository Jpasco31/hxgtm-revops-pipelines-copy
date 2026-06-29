---
name: publish-to-framer
description: Push a Framer Publish Bundle to the Framer CMS via the official Framer Agent CLI (`npx @framer/agent@latest`). Use after format-for-framer has produced a validated bundle. Handles primary + linked sub-collection items, slug + action confirmation, image re-hosting via `framer.uploadImage`, and the `framer.agent.applyChanges` write. Stops at applyChanges + reviewChanges — never calls `framer.agent.publish`; the user goes live manually in Framer. Does not do mapping, page-type routing, or reverse pulls — those are owned by format-for-framer.
---

# Publish to Framer

## Purpose

Take a validated **Framer Publish Bundle** (produced by `format-for-framer`) and write it to the Framer CMS via the **official Framer Agent CLI** (`npx @framer/agent@latest`), creating or updating items as staged canvas changes that the human can review and publish manually from Framer.

This skill owns Framer write I/O only. It does not load CMS reference files, route by page type, derive field IDs, or pull pages for editing — all of that is `format-for-framer`'s job. The split exists so mapping can run *after* human review of the final copy, keeping the staged item in sync with what the human actually approved.

## When to Use

- Immediately after `format-for-framer` has produced a Framer Publish Bundle and the user wants to push to Framer
- When a user says "publish this to Framer," "push to Framer," "create this in Framer," or "update the Framer page" *and* a valid bundle exists in the conversation
- Usable standalone only when the user supplies a hand-crafted Framer Publish Bundle (very rare — the normal flow is via `format-for-framer`)

**Do not use if:**

- No Framer Publish Bundle exists in the conversation — run `format-for-framer` first
- The user wants to draft new copy or pull an existing page for editing — those are `web-copy` / `press-release` / `format-for-framer` (reverse mode)

## Step 0 — Confirm the Framer Agent session

This skill relies on the **official Framer Agent CLI**. The `framer` skill at `~/.claude/skills/framer/SKILL.md` is the canonical source for setup and session conventions — load it (and the project-scoped `framer-project-<projectId>` skill) before this one when the agent isn't already wired up for the hx Framer project.

Verify connectivity:

```bash
npx @framer/agent@latest session list
```

If a session for the hx Framer project already exists, capture its session id and reuse it as `-s <id>` for every subsequent call. If no session exists, stop and say:

> The Framer Agent CLI isn't connected to a session for the hx Framer site. Run `npx @framer/agent@latest setup`, then `npx @framer/agent@latest session new "<hx project url or id>"`, then re-run this skill. The `framer` skill at `~/.claude/skills/framer/SKILL.md` covers the full bootstrap.

Do not attempt manual workarounds or output copy for manual paste as a substitute.

## Step 1 — Locate the Framer Publish Bundle

Find the most recent `Framer Publish Bundle` block in the conversation (verbatim header — emitted by `format-for-framer`).

If no bundle is present, stop and say:

> No Framer Publish Bundle found. Run `format-for-framer` on the current copy first.

If the bundle's last line is `Validation: FAILED`, stop and surface the validation failures. Do not attempt to publish a failed bundle — re-run `format-for-framer` after fixing the issues.

## Step 2 — Confirm slug and action

Read the bundle's `Slug` and `Action` lines.

- If both are present and explicit (`Action: create` or `Action: update` with a slug), proceed.
- If either is blank or `Action: unspecified`, ask the user once:

  *"What slug should this page use? And what would you like to do: create a new page or update an existing page?"*

Never infer or default the slug from the page title or context — require explicit input.

For `Action: update`, the bundle should include `Item ID: <id>` (carried over from a prior Reverse Mode pull). If missing, look up the item ID at runtime: read all items in the primary collection and find the one whose slug attribute matches. Example exec script:

```js
// /var/folders/9r/6bc9bw3d48z3clhmgmnwry2w0000gn/T/framer/<session>-lookup-item-by-slug.js
const collectionId = "<primary-collection-id>";
const slug = "<user-slug>";
const items = await framer.agent.getNodesOfTypes({ types: ["CollectionItemNode"] });
const match = items.find(
  (i) => i.$parentId === collectionId && i.attributes?.$control__slug === slug,
);
state.itemId = match?.id ?? null;
console.log({ itemId: state.itemId });
```

If no item is found for an `update`, stop and ask the user to confirm whether to switch to `create`.

## Step 3 — Resolve linked sub-collection item IDs

If the bundle contains a `Linked sub-collection items` section, process each linked collection in order before touching the primary record.

For each linked item:

1. **Check for an existing match.** Read items in the sub-collection via `framer.agent.getNodesOfTypes({ types: ["CollectionItemNode"] })` filtered by `$parentId === <sub-collection-id>`, then match by the natural-key attribute (e.g. `attributes.$control__<speaker-name-field-id>`). Compare case-insensitively + trim whitespace. If a match is found, record its existing item id and skip creation. (Getting this wrong creates **duplicate** speakers.)
2. **Re-host any `(re-host via publisher)` image fields.** See Step 3.5 below — resolve each annotated image to a durable Framer asset URL **before** building the applyChanges command. If re-hosting fails, drop that image field and add a manual-upload flag for it (don't fail the whole item).
3. **Create if missing.** Build an `applyChanges` DSL fragment that adds a `+CollectionItemNode` under the sub-collection and `SET`s each `$control__<fieldId>` to the encoded value. Use a temporary id (e.g. `newSpeaker0`) — `applyChanges` returns a `renamedIds` map you use to convert the temp id into the canonical Framer item id. Append every sub-item creation into a single `applyChanges` call per sub-collection for atomicity, e.g.:

   ```js
   const dsl = [
     `+CollectionItemNode newSpeaker0 parent="${subCollectionId}";`,
     `SET newSpeaker0 $control__${nameFieldId}="Jane Doe" $control__${titleFieldId}="CEO" ${enumFieldKey}="Conference";`,
   ].join("\n");
   const { status, errors, renamedIds } = await framer.agent.applyChanges(dsl);
   ```

   Map every returned `renamedIds["newSpeaker0"]` → canonical id and record it.
4. **Collect IDs in order.** Preserve the order in which they appear in the bundle — some page types (e.g., customer-story quotes) use an `Index` field to control display order; the bundle is the source of truth for ordering.

If any sub-item creation fails (`status` is `failed` or `errors` contains entries for that item) because of missing required fields, do not abort. Surface the linked item in the confirmation's manual-actions list and continue without that reference.

> **Why we use `applyChanges` for CMS work (not the lower-level `Collection` API):** the project-scoped Framer skill explicitly prefers `framer.agent.applyChanges` over the `Collection.addItems` / `Item.setAttributes` plugin APIs for CMS writes, because items created via the low-level APIs can misbehave when later referenced from canvas designs that use applyChanges. Single write path = consistent behavior.
>
> **Exception — ad-hoc field corrections on existing items:** `applyChanges` silently no-ops when setting a field to an empty string (`""`). It returns `status: applied` with no errors but does not write the value. For operations that clear or bulk-correct existing item fields (not creating items or linking canvas references), use `collection.addItems()` instead:
>
> ```js
> const collection = await framer.getCollection("<collectionId>");
> await collection.addItems([{
>   id: "<existingItemId>",
>   slug: "<existing-slug>",
>   fieldData: {
>     ["<fieldId>"]: { type: "string", value: "" },
>   },
> }]);
> ```
>
> The `addItems` / `applyChanges` misbehavior concern applies to *newly created* items that will be referenced from canvas via `multiCollectionReference` or `collectionReference` controls. It does not apply to in-place field corrections on items that already exist on canvas.

## Step 3.5 — Re-host `(re-host via publisher)` images

The bundle marks some image fields `(re-host via publisher)` — typically speaker headshots whose source is a Notion presigned S3 URL that expires (~1h) and would 404 if stored as-is. For each such field (on a linked sub-item or the primary record), re-host the bytes so Framer stores a durable Framer asset URL rather than the expiring source.

**Use `framer.uploadImage` — do NOT pass the raw expiring URL to `applyChanges`.** The Framer Agent supports uploading directly from a remote URL and returns a durable asset URL you can write into `$control__<imageFieldId>`:

```js
// /var/folders/9r/6bc9bw3d48z3clhmgmnwry2w0000gn/T/framer/<session>-rehost-headshot.js
const source = "<notion-presigned-s3-url>";
try {
  const uploaded = await framer.uploadImage({
    image: source,
    altText: "Jane Doe headshot",
  });
  state.rehosted = state.rehosted ?? {};
  state.rehosted[source] = uploaded.url;
  console.log({ ok: true, url: uploaded.url });
} catch (err) {
  console.log({ ok: false, error: String(err) });
}
```

If `framer.uploadImage` fails (already expired / 404 / unsupported type), drop the field for that record and add a manual-upload flag in the confirmation — do not pass the dead source URL through to `applyChanges`. The new API doesn't have the old MCP's 30-second synchronous-fetch failure mode, but a broken source still produces a broken item.

> Migration note: the old MCP flow needed an external host (uguu.se) plus a content-type/latency precheck because the Framer MCP fetched the URL synchronously inside `upsertCMSItem` and dropped the whole call on slow hosts. The new Agent path uses `framer.uploadImage`, which uploads bytes server-side and gives you back a permanent Framer asset URL up front — no precheck and no third-party hops required.

After re-hosting, store the durable Framer asset URL keyed by source URL in `state.rehosted` so the same source isn't re-uploaded across linked items. When emitting the primary or sub-item DSL, use the re-hosted URL as the `$control__<imageFieldId>` value.

After all linked sub-items are created, you have a map `linkedIds: { <primary-reference-fieldId>: [<itemId>, <itemId>, ...] }`. Inject these into the primary item's `applyChanges` command — see Step 4.

## Step 4 — Pre-publish structural check

Build the primary item's `applyChanges` DSL command and confirm:

- No field ID appears more than once in the primary `SET` line.
- Every value is encoded per the new-API conventions:
  - `$control__<fieldId>="<escaped-string>"` for `string`, `formattedText`, `link`, `file`, `image`, `date`
  - `$control__<fieldId>="<true|false>"` for `boolean`
  - `$control__<fieldId>=<number>` (unquoted) for `number`
  - `$control__<fieldId>="<case-name>"` for `enum` — **case name as it appears on the live collection's `variables[].cases`**, never a case ID
  - `$control__<fieldId>="<itemId1>,<itemId2>,…"` for `multiCollectionReference` — comma-separated list of live item IDs (or the encoding the live schema reports, confirmed via `framer.agent.getNodesOfTypes({types:["CollectionNode"]})`)
  - `$control__<fieldId>="<itemId>"` for `collectionReference`
- Required image / file fields with no value are absent from the `SET` line and reflected in the bundle's manual-actions list.
- Quotes inside string values are escaped: `"` → `\"`.

Content-aware validation (duplicate FAQ questions, default toggle values, mutually-exclusive fields, etc.) is `format-for-framer`'s responsibility and was applied before the bundle was emitted. Do not re-run it here.

If a structural check fails, stop and surface the issue with the offending field IDs. Re-run `format-for-framer` to regenerate the bundle.

## Step 5 — Apply the write

Build a single applyChanges DSL string covering the primary item:

- **Create** (`Action: create`):

  ```
  +CollectionItemNode <tempId> parent="<primary-collection-id>";
  SET <tempId> $control__slug="<slug>" $control__<field1>=... $control__<field2>=...;
  ```

- **Update** (`Action: update`, with a known `<itemId>`):

  ```
  SET <itemId> $control__<field1>=... $control__<field2>=...;
  ```

Then call:

```js
const { status, errors, renamedIds } = await framer.agent.applyChanges(dsl);
```

Capture:

- `status` — `applied`, `partially-applied`, or `failed`
- `errors` — per-command errors (handle in Step 6)
- `renamedIds[<tempId>]` — the canonical item id Framer assigned (for `create`)

**Important — this skill does NOT call `framer.agent.publish`.** Items created via `applyChanges` are staged canvas changes, not live pages. The "always draft" guarantee in the old MCP path translated to a `draft: true` parameter on `upsertCMSItem`. In the new API, the equivalent guarantee is **never call publish from this skill** — the human reviews staged changes in Framer and runs publish themselves (or asks another skill to do it explicitly).

### Update path (no more enum/reference round-trip workaround)

On `Action: update`, the bundle no longer needs to re-send every enum and reference field. The old workaround was driven by a Framer MCP round-trip bug where `upsertCMSItem` round-tripped enum values as display labels and reference values as slugs — neither of which it accepted back as input — so a partial update failed on fields the agent never touched.

The Framer Agent CLI's `applyChanges` doesn't have that bug: a `SET` on an existing `CollectionItemNode` only touches the `$control__` keys you mention. Unmentioned fields are left untouched server-side. **Therefore: send only the fields you actually want to change** (plus the slug if it's changing). `format-for-framer` knows about this and emits thin update bundles by default.

### Schema-drift errors

`framer.agent.applyChanges` returns `errors` per failed `SET`. The most common drift signals from old-MCP-era bundles:

| Error substring (illustrative) | Meaning | Fix |
|---|---|---|
| `unknown attribute $control__<id>` | the field ID does not exist on the live collection (stale/renamed field) | re-run format-for-framer preflight; the Step 1.5 reconciliation should map to the live field ID |
| `unknown enum case <name>` | the case **name** does not exist on the live field (stale enum) | re-run format-for-framer preflight; use the live case name |
| `unknown item id <id>` | a `multiCollectionReference`/`collectionReference` value does not resolve to a live item | re-resolve sub-item IDs (see Step 3) |

Treat any non-`applied` status as a drift signal. Route to Failure handling and recommend re-running `format-for-framer` so its Step 1.5 reconciles IDs against the live schema.

## Step 5.5 — Review changes

After the primary `applyChanges` call (and any preceding sub-item applyChanges), finalize with `framer.agent.reviewChanges()` per the project-scoped skill's mandatory review rule. Read the entire response and resolve any errors or deferred commands before proceeding to confirmation. If the review surfaces problems related to your write (e.g., a deferred command for a still-missing sub-item), fix the underlying cause via another applyChanges and review again.

```js
const review = await framer.agent.reviewChanges();
console.log(review);
```

## Step 6 — Confirmation

Construct the preview URL. Two options:

1. **Cheap:** if the site's base URL is already known (cached in `state` from a prior session or hardcoded for the hx project), assemble `<site-url>` + the bundle's `Preview URL pattern` (substituting the slug).
2. **Authoritative:** call `framer.agent.publish({ action: "preview" })` once to fetch the current staging / production URLs. **This does not publish** — the docs explicitly note it only returns readiness diagnostics, URLs, and a `confirmationHash`. Discard the `confirmationHash`; we are not calling `confirm_publish`.

   ```js
   const { staging, production } = await framer.agent.publish({ action: "preview" });
   state.previewBase = staging || production;
   ```

Then output:

```
Staged in Framer (canvas only — not live).

Page type: <page type>
Action: <create | update>
Slug: <slug>
Item ID: <itemId>
Preview: <full draft preview URL>

Primary fields written: <count>
Linked items written: <count per sub-collection, e.g. "Speakers: 3 created, 1 reused">

Images re-hosted:
- <one bullet per (re-host via publisher) image: field + record → Framer asset URL, or "None">

Manual actions:
- <one bullet per manual upload or external step from the bundle, plus any sub-item failures and any re-host fallbacks>
- <or "None" if the manual-actions list was empty>

To go live: open the Framer project, review the staged changes on canvas, then publish from Framer (or ask explicitly: "publish the Framer site"). This skill intentionally never calls `framer.agent.publish`.
```

A "Staged in Framer (canvas only — not live)" confirmation only appears when **every** `applyChanges` call returned `status: "applied"` and `reviewChanges` came back clean. A `partially-applied` or `failed` status routes to Failure handling and never produces a falsely-green confirmation.

## Failure handling

If `applyChanges` fails (`status: "failed"`) or partially fails (`status: "partially-applied"`) for the primary record:

**"Content permission" errors — retry once automatically.** If the sole error is `"Cannot change CMS item content because the current user does not have Content permission"`, this is frequently a transient session-idle state, not a real permissions problem. **Retry the identical `applyChanges` call once** (without rebuilding the DSL or re-reporting the error). If the retry succeeds, continue to Step 5.5 as normal. If it fails a second time with the same error, then treat it as a real failure: tell the user to run `npx @framer/agent@latest setup && npx @framer/agent@latest session new` to reconnect, and check that their account has the **Editor** role in Framer (Settings → Members).

For all other failure types:

- Stop. Do not retry silently.
- Report the full `errors` array from `applyChanges` and the diagnostics from `reviewChanges`.
- Echo the assembled DSL string (or a pointer to a temp file containing it if it's large) so the user can debug or hand-publish.
- If linked sub-items were already created in Step 3, list their IDs and natural keys so the user can decide whether to clean them up (`DEL <itemId>` via a follow-up applyChanges) or reuse them on retry.

If `applyChanges` fails for a single linked sub-item:

- Continue with the remaining sub-items.
- Omit the failed sub-item's ID from the primary record's `multiCollectionReference` field.
- Surface the failure in the confirmation's manual-actions list with the sub-collection name and the natural key.

If `reviewChanges` surfaces errors:

- Resolve each item before declaring success.
- Deferred commands (returned in `review.deferred`) auto-retry once preconditions are met — fix the underlying cause but do not re-issue the deferred command.

## Framer Agent Reference

This skill uses the official Framer Agent CLI (`npx @framer/agent@latest`) with the project's session id (`-s <id>`).

| Method | Purpose |
|---|---|
| `framer.agent.getNodesOfTypes({ types: ["CollectionNode"] })` | Read live collection metadata (variables/fields, enum case names) for runtime reconciliation if needed |
| `framer.agent.getNodesOfTypes({ types: ["CollectionItemNode"] })` | Look up existing primary items by slug (for `Action: update`); detect duplicate sub-collection items by natural key |
| `framer.agent.serialize({ id, depth: 1 })` | Read a collection plus its direct item children when paginating large sets |
| `framer.agent.applyChanges(dsl)` | Create or update CMS items (primary + linked sub-items) — single write path |
| `framer.agent.reviewChanges()` | Mandatory post-applyChanges diagnostic |
| `framer.agent.publish({ action: "preview" })` | Optional, last-step only: fetch staging/production URLs for the confirmation output. Never call `confirm_publish` or `deploy_to_production` from this skill. |
| `framer.uploadImage({ image, altText })` | Re-host an expiring source URL (e.g. Notion presigned S3) as a durable Framer asset |

Per the project-scoped skill's required workflow, every new API method usage should be preceded by:

```bash
npx @framer/agent@latest docs <Class>
npx @framer/agent@latest docs <Class>.<method>
```

to confirm the current signature. Exec scripts live under `/var/folders/9r/6bc9bw3d48z3clhmgmnwry2w0000gn/T/framer/<sessionId>-<short-summary>.js` and run via `npx @framer/agent@latest exec -s <sessionId> -f <path>`.

## Guardrails

- This skill performs no mapping. If the bundle is missing a field, the answer is *not* to invent its value — re-run `format-for-framer`.
- **Never call `framer.agent.publish({ action: "confirm_publish", … })` or `deploy_to_production` from this skill.** The user goes live manually in Framer. A `preview` call is the only `framer.agent.publish` action allowed, and only to read staging/production URLs for the confirmation output. (This replaces the old `draft: true` guarantee 1-for-1.)
- Never modify, rewrite, or summarize copy at any step.
- Never silently drop a field. If a value cannot be sent, the answer is either fix the bundle and re-publish, or surface it in the manual-actions confirmation.
- Do not call CMS reference files. Schema knowledge lives in `format-for-framer`. If you find yourself wanting to read a reference file, stop — you're doing this skill's job wrong.
- Use `framer.agent.applyChanges` for CMS writes that create items or set non-empty field values. **Do not** use `applyChanges` to clear a field to `""` — it silently no-ops (returns `status: applied` with no errors but does not write). For ad-hoc corrections that clear or overwrite existing fields on already-published items, use `collection.addItems()` (see the exception note in Step 3).
- Use `framer.uploadImage` for expiring source URLs (Notion presigned S3, etc.). Do not pass raw expiring URLs into `applyChanges`.
- Do not touch pages, components, layout templates, or styles. CMS items only. Page templates and component changes are separate human or design-system tasks.
- Always close the loop with `framer.agent.reviewChanges` after any `applyChanges` write, per the project-scoped Framer skill's mandatory review rule.
