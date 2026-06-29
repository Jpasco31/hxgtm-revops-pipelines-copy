---
name: fetch-linkedin-image
description: Resolve a LinkedIn profile or company URL to a local image file by scraping the page's og:image meta tag and downloading the referenced asset. Used as a fallback path when a producer skill needs a photo or logo but the user supplied only a LinkedIn URL (no file attached). Fails closed when LinkedIn returns a login wall or omits og:image.
user-invocable: false
metadata:
  version: 1.0.0
---

# fetch-linkedin-image skill

Tiny utility skill. Given a LinkedIn URL (person profile `/in/<slug>` or company page `/company/<slug>`), it:

1. Fetches the URL.
2. Extracts the `og:image` meta-tag URL from the returned HTML.
3. Downloads the image to a caller-supplied local path.

It is **not** a substitute for human-attached files — it is a best-effort fallback. LinkedIn frequently returns a login wall to unauthenticated requests; when that happens the skill fails closed (exit non-zero) so the caller can surface a clear "attach the file directly" message to the user.

## When to use

Chained from producer skills that accept a `photo_path` or `logo_path` input. Typical sites:

- `linkedin-customer-quote-card` — when a `Customer Quotes` child-DB row has only a `Customer LinkedIn URL` (no `Customer Photo` file).
- `linkedin-partnership-card` — when a press-release card has only a `Customer LinkedIn URL` body-table row (no `Customer Logo` file attached).
- Ad-hoc: any subagent step that wants to resolve a LinkedIn URL to an image without prompting the user.

The Perkins routine prompts already document this as the fallback branch in the "Photo / logo input resolution" paragraph. Other skills can chain it the same way.

Do NOT use for non-LinkedIn URLs; for generic image URLs use plain `curl` and skip the scrape step.

## Pipeline

### 1. Pre-flight

- Required: `--url <linkedin_url>` and `--output <abs_path>`. The output path's parent directory must exist.
- The URL must match `https://(www\.)?linkedin\.com/(in|company)/...`. Other hosts → exit 4 (bad input).
- The output path must be absolute. Relative paths → exit 4.

### 2. Fetch the LinkedIn HTML

Use `curl` with a browser-like User-Agent and accept-language to maximise the chance LinkedIn returns the public preview HTML rather than the login wall:

```
curl -sS -L --max-time 30 \
  -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36" \
  -H "Accept-Language: en-US,en;q=0.9" \
  "<url>"
```

If `curl` exits non-zero → exit 3 (full failure), surface the verbatim stderr.

### 3. Detect login-wall responses

If the response body matches any of these heuristics, exit 3 with a clear "LinkedIn login wall" message:

- HTTP status was 999 (LinkedIn's anti-scrape signal).
- Response body contains `<title>LinkedIn Login` or `Sign In | LinkedIn` near the head.
- No `<meta property="og:image"` tag is present.

The error message must be verbatim parseable by the caller so it can convert to a user-facing "attach the file directly" prompt.

### 4. Extract the og:image URL

Grep the HTML for the first occurrence of:

```
<meta property="og:image" content="<URL>" />
```

Allow attribute order to vary (`content=...` before `property=...`) and quotes to be single or double. Decode HTML entities (`&amp;` → `&`) in the URL.

If multiple `og:image` tags are present (LinkedIn occasionally emits both raw and CDN), take the **first one**.

### 5. Download the image

```
curl -sS -L --max-time 60 -o "<output>" "<og:image url>"
```

Validate:

- HTTP 200.
- `file <output>` reports an image MIME (`image/jpeg`, `image/png`, `image/webp`, `image/gif`).
- File size ≥ 1024 bytes (anything smaller is likely an error page).

If any check fails → delete the partial output, exit 3 with the failing check named.

### 6. Emit a manifest

Print to stdout a JSON object describing the result:

```json
{
  "source_url": "<linkedin url>",
  "og_image_url": "<resolved og:image url>",
  "local_path": "<output abs path>",
  "bytes": 12345,
  "mime": "image/jpeg"
}
```

Single-line, no trailing newline parsing required. Callers can `jq -r .local_path` to extract the path.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success — image downloaded and validated. |
| 3 | Full failure — login wall, missing og:image, network error, or downloaded asset is not a valid image. The error message names the specific failed step. |
| 4 | Bad input — non-LinkedIn URL, missing flag, non-absolute output path, parent directory missing. |

## Forbidden behaviours

- **Do not retry against an authenticated endpoint.** If LinkedIn returns a login wall, the user must attach the file directly; do not attempt to bypass.
- **Do not substitute a placeholder image.** Failure is the correct outcome when og:image is missing — the caller will surface "attach as file" to the user.
- **Do not cache.** Every invocation re-fetches LinkedIn. There is no fallback to a previously-fetched result.

## Out of scope

- LinkedIn auth, sessions, cookies.
- Resizing, cropping, or post-processing the downloaded image. The producer skill that consumes the path runs its own cleanup pipeline (e.g. `cleanup_headshot.js` for `linkedin-customer-quote-card`).
- Generic web scraping of non-LinkedIn URLs.
