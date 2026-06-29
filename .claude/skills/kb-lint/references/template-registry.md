# Template Registry

Files in these directories are validated against their corresponding canonical
template. Template files themselves (prefixed with `_template-`) are excluded
from validation.

> This is the human-facing reference. The **operative** copy the Canon
> Analyzer subagent runs from lives inline in
> [`canon-analyzer.md`](canon-analyzer.md) Check 4 (subagents only receive
> their own prompt, so the rules must be inlined there). Keep the two in sync.

## Registry

| Directory | Template file | Exclusion pattern |
|-----------|--------------|-------------------|
| `truth/audiences/*.md` | `truth/audiences/_template-persona.md` | `_template-*` |
| `truth/messaging/products/*.md` | `truth/messaging/_template-product.md` | `_template-*` |
| `truth/messaging/segments/*.md` | `truth/messaging/_template-segment.md` | `_template-*` |

## Validation rules

1. **Required sections:** Every `##` heading in the template must appear in the
   target file, in the same order.
2. **`[NEEDS COMPLETION]` is acceptable.** A section that exists but contains only
   `[NEEDS COMPLETION]` or placeholder text is noted as informational (severity:
   low), not flagged as an error.
3. **Missing sections are flagged** as medium severity.
4. **Extra sections** in the target file (not in the template) are allowed — they
   are not flagged.
5. **Heading text matching** is case-insensitive and ignores leading/trailing
   whitespace.

## Owned by

These templates and their instances are maintained by hx-ops refresh skills:

| Template directory | Owning skill(s) |
|-------------------|-----------------|
| `truth/audiences/` | refresh-personas, refresh-icp |
| `truth/messaging/products/` | refresh-messaging |
| `truth/messaging/segments/` | refresh-messaging |
