#!/usr/bin/env python3
"""
resolve_mcp_path.py

One-stop resolver for the hxgtm-mcp-server path kb-update and
kb-integrate need at runtime. Writes the resolved absolute path to
`.kb-local.json` at the repo root so subsequent invocations skip the
discovery phase — scans of ~/Desktop and friends are cheap but not
free on a run where scope narrowing + parallel comparators are racing
against a <2 min budget.

Resolution order:

  1. `.kb-local.json.hxgtm_mcp_server_path` — cached absolute path
     from a previous successful run. Must still exist AND contain
     both `context/` and `.git/`; stale cache is ignored (and gets
     overwritten by the next successful lookup).
  2. `HXGTM_MCP_SERVER_PATH` env var — explicit override, wins over
     discovery but not over the cache-hit fast path. If set and
     valid, resolved value is written back to `.kb-local.json` so
     subsequent runs can skip the env-read.
  3. `../hxgtm-mcp-server/` — adjacent-repo convention.
  4. Dev-root scan — walk `~/Desktop`, `~/dev`, `~/code`, `~/Projects`
     and their immediate children looking for a directory literally
     named `hxgtm-mcp-server` with a `context/` subfolder. First hit
     wins; later candidates are not considered.

All candidates must carry a `.git/` directory — a zip-download with
no git history breaks the kb-integrate follow-up (`git diff`,
`git commit`). Halts with the `git clone` instruction when the only
match is a zip-extract.

Usage:
  python3 resolve_mcp_path.py mcp-path [--quiet]

    JSON to stdout:
      {
        "path": "/abs/path/to/hxgtm-mcp-server",
        "source": "cache" | "env" | "adjacent" | "scan",
        "cached": true | false,
        "duration_ms": 12
      }

    Exit 0 on success, 1 on halt (path not found / zip-not-git / etc.).
    --quiet suppresses the stderr progress lines.

  python3 resolve_mcp_path.py write-notion-id --group <slug> --id <uuid>

    Writes `.kb-local.json.notion_ids.<slug>` = <uuid>. Used after a
    lazy Notion-search fallback resolves a new database ID. No stdout
    output on success; exit 1 on write failure.

  python3 resolve_mcp_path.py read-notion-id --group <slug>

    Prints the cached Notion data source ID for the group to stdout,
    or empty string if not cached. Exit 0 either way.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path


# Repo root is 4 levels up from this script: scripts/ → kb-update/ → skills/
# → .claude/ → repo root.
REPO_ROOT = Path(__file__).resolve().parents[4]
LOCAL_STATE_PATH = REPO_ROOT / ".kb-local.json"


# Scan targets — user's common dev-root conventions. Each entry is a
# directory whose immediate children are candidates for a
# hxgtm-mcp-server clone. Expanded with Path.expanduser() at runtime.
SCAN_ROOTS = [
    "~/Desktop",
    "~/dev",
    "~/code",
    "~/Projects",
    "~/projects",
]


# ---------------------------------------------------------------------------
# State file I/O
# ---------------------------------------------------------------------------


def _read_local_state():
    """Return the parsed `.kb-local.json` dict, or {} if missing/corrupt."""
    if not LOCAL_STATE_PATH.exists():
        return {}
    try:
        with LOCAL_STATE_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return data
    except (OSError, json.JSONDecodeError):
        return {}


def _write_local_state(data):
    """Write `.kb-local.json` atomically. Fields preserved on write."""
    tmp = LOCAL_STATE_PATH.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")
    tmp.replace(LOCAL_STATE_PATH)


# ---------------------------------------------------------------------------
# Path validation
# ---------------------------------------------------------------------------


def _is_valid_mcp_root(path):
    """Return True if `path` looks like a real hxgtm-mcp-server clone."""
    path = Path(path).expanduser()
    if not path.is_dir():
        return False
    if not (path / "context").is_dir():
        return False
    if not (path / ".git").is_dir():
        return False
    return True


def _is_zip_not_git(path):
    """Return True if `path` has context/ but no .git/ (zip-extract case)."""
    path = Path(path).expanduser()
    return (
        path.is_dir()
        and (path / "context").is_dir()
        and not (path / ".git").is_dir()
    )


# ---------------------------------------------------------------------------
# Candidate enumeration
# ---------------------------------------------------------------------------


def _enumerate_dev_root_candidates(log):
    """Yield (source_name, candidate_path) pairs from the dev-root scan."""
    for raw in SCAN_ROOTS:
        root = Path(raw).expanduser()
        if not root.is_dir():
            continue
        # Direct: ~/Desktop/hxgtm-mcp-server
        direct = root / "hxgtm-mcp-server"
        if direct.is_dir():
            yield ("scan", direct)
        # One level deep: ~/Desktop/Huw/hxgtm-mcp-server
        try:
            for child in root.iterdir():
                if not child.is_dir():
                    continue
                deeper = child / "hxgtm-mcp-server"
                if deeper.is_dir():
                    yield ("scan", deeper)
        except OSError as exc:
            log(f"  scan: couldn't list {root}: {exc}")


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------


def resolve(quiet=False):
    """
    Resolve the hxgtm-mcp-server path and return a dict
        {path, source, cached, duration_ms}
    OR sys.exit()s with a human-readable halt message on failure.
    """

    start = time.perf_counter()

    def log(msg):
        if not quiet:
            print(f"[resolve_mcp_path] {msg}", file=sys.stderr)

    state = _read_local_state()

    # --- 1. Cached path -----------------------------------------------------
    cached = state.get("hxgtm_mcp_server_path")
    if cached and _is_valid_mcp_root(cached):
        ms = int((time.perf_counter() - start) * 1000)
        log(f"cache hit: {cached}")
        return {
            "path": str(Path(cached).expanduser().resolve()),
            "source": "cache",
            "cached": True,
            "duration_ms": ms,
        }

    if cached and not _is_valid_mcp_root(cached):
        log(f"cache miss: {cached} no longer valid — rediscovering")

    # --- 2. Env var ---------------------------------------------------------
    env = os.environ.get("HXGTM_MCP_SERVER_PATH")
    if env:
        env_path = Path(env).expanduser().resolve()
        if _is_zip_not_git(env_path):
            _halt_zip_not_git(env_path)
        if _is_valid_mcp_root(env_path):
            _cache_path(state, str(env_path))
            ms = int((time.perf_counter() - start) * 1000)
            log(f"env HXGTM_MCP_SERVER_PATH: {env_path}")
            return {
                "path": str(env_path),
                "source": "env",
                "cached": False,
                "duration_ms": ms,
            }
        log(f"env HXGTM_MCP_SERVER_PATH points at invalid path: {env_path}")

    # --- 3. Adjacent convention ---------------------------------------------
    adjacent = (REPO_ROOT.parent / "hxgtm-mcp-server").resolve()
    if _is_zip_not_git(adjacent):
        _halt_zip_not_git(adjacent)
    if _is_valid_mcp_root(adjacent):
        _cache_path(state, str(adjacent))
        ms = int((time.perf_counter() - start) * 1000)
        log(f"adjacent: {adjacent}")
        return {
            "path": str(adjacent),
            "source": "adjacent",
            "cached": False,
            "duration_ms": ms,
        }

    # --- 4. Dev-root scan ---------------------------------------------------
    log("scan: walking dev roots…")
    zip_misses = []
    for source, candidate in _enumerate_dev_root_candidates(log):
        candidate = candidate.resolve()
        if _is_valid_mcp_root(candidate):
            _cache_path(state, str(candidate))
            ms = int((time.perf_counter() - start) * 1000)
            log(f"scan hit: {candidate}")
            return {
                "path": str(candidate),
                "source": source,
                "cached": False,
                "duration_ms": ms,
            }
        if _is_zip_not_git(candidate):
            zip_misses.append(str(candidate))

    # --- 5. Halt ------------------------------------------------------------
    if zip_misses:
        # Found a hxgtm-mcp-server directory but every candidate is a
        # zip-extract. Surface the first miss with the git clone
        # instruction — more useful than a generic "not found" halt.
        _halt_zip_not_git(Path(zip_misses[0]))

    tried = [
        "  - .kb-local.json cache (missing or stale)",
        "  - $HXGTM_MCP_SERVER_PATH "
        + (f"(= {env}, invalid)" if env else "(unset)"),
        f"  - {REPO_ROOT.parent / 'hxgtm-mcp-server'} (adjacent)",
        "  - scan: " + ", ".join(
            str(Path(r).expanduser()) for r in SCAN_ROOTS
        ),
    ]
    sys.exit(
        "ERROR: could not locate hxgtm-mcp-server (need a directory "
        "with both `context/` and `.git/`).\nTried:\n"
        + "\n".join(tried)
        + "\nSet HXGTM_MCP_SERVER_PATH or clone the repo next to this one:\n"
        "  git clone git@github.com:hx-gtm/hxgtm-mcp-server.git"
    )


def _halt_zip_not_git(path):
    sys.exit(
        f"ERROR: hxgtm-mcp-server at {path} is not a git clone — "
        f"kb-integrate needs git diff/commit to work. Run:\n"
        f"  git clone git@github.com:hx-gtm/hxgtm-mcp-server.git"
    )


def _cache_path(state, abs_path):
    """Merge the resolved path into local state and persist."""
    if state.get("hxgtm_mcp_server_path") == abs_path:
        return
    state["hxgtm_mcp_server_path"] = abs_path
    try:
        _write_local_state(state)
    except OSError as exc:
        # Non-fatal — the resolver still returns the correct path, we
        # just won't get the cache speedup on the next run.
        print(
            f"[resolve_mcp_path] warning: couldn't write {LOCAL_STATE_PATH}: {exc}",
            file=sys.stderr,
        )


# ---------------------------------------------------------------------------
# Notion ID cache (read + write only — lazy discovery lives in
# publish_to_notion.py)
# ---------------------------------------------------------------------------


def read_notion_id(group):
    state = _read_local_state()
    return (state.get("notion_ids") or {}).get(group, "") or ""


def write_notion_id(group, uuid):
    state = _read_local_state()
    state.setdefault("notion_ids", {})[group] = uuid
    _write_local_state(state)


def read_landing_page_id():
    """Return the cached 'KB - Updates Review' landing page UUID, or ''.

    The landing page is a single workspace-level object shared by all
    groups, so it lives at the top level of .kb-local.json (not under a
    per-group key).
    """
    state = _read_local_state()
    return state.get("notion_landing_page_id", "") or ""


def write_landing_page_id(page_id):
    """Cache the 'KB - Updates Review' landing page UUID."""
    state = _read_local_state()
    state["notion_landing_page_id"] = page_id
    _write_local_state(state)


def resolve_notion_id_for_group(group):
    """
    Walk the full resolution ladder for a group's Notion data source ID
    and return (id, source) where `source` is one of:

        "env"     — KB_UPDATE_NOTION_DS_<GROUP_UPPER> env var was set.
                    Highest priority — lets a testing-environment
                    override skip the cache without editing config.
        "cache"   — .kb-local.json.notion_ids.<group> was set by a
                    previous successful run or by a fallback lookup.
        "config"  — .claude/skills/kb-update/config.yaml has a non-empty
                    groups.<group>.notion_data_source_id.
        "missing" — nothing resolved; caller must reconcile.

    The ladder is designed so the same repo can target different
    Notion workspaces (testing vs production) without config edits —
    just export the env var per environment, or let `.kb-local.json`
    carry the machine-local override.
    """
    env_key = f"KB_UPDATE_NOTION_DS_{group.upper().replace('-', '_')}"
    env_val = os.environ.get(env_key, "").strip()
    if env_val:
        return env_val, "env"

    cached = read_notion_id(group)
    if cached:
        return cached, "cache"

    config_path = REPO_ROOT / ".claude" / "skills" / "kb-update" / "config.yaml"
    if config_path.exists():
        value = _read_config_scalar(
            config_path, ("groups", group, "notion_data_source_id")
        )
        if value:
            return value, "config"

    return "", "missing"


def _read_config_scalar(path, key_path):
    """Minimal YAML reader for a nested scalar — stdlib only.

    Mirrors the helper in publish_to_notion.py / apply_integrations.py
    so resolve_mcp_path.py stays dependency-free (no pyyaml needed at
    runtime, matches the rest of the kb-* scripts).
    """
    with path.open("r", encoding="utf-8") as f:
        lines = f.readlines()

    path_stack = []
    for raw in lines:
        stripped = raw.rstrip("\n")
        if not stripped.strip() or stripped.strip().startswith("#"):
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        content = stripped.strip()
        if ":" not in content:
            continue
        key, _, value = content.partition(":")
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        while path_stack and path_stack[-1][1] >= indent:
            path_stack.pop()
        path_stack.append((key, indent))

        current_keys = tuple(k for k, _ in path_stack)
        if current_keys == key_path and value:
            return value
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_mcp = sub.add_parser(
        "mcp-path",
        help="Resolve the hxgtm-mcp-server path. JSON to stdout.",
    )
    p_mcp.add_argument("--quiet", action="store_true")

    p_read = sub.add_parser(
        "read-notion-id",
        help="Print the cached Notion data source ID for a group, or empty.",
    )
    p_read.add_argument("--group", required=True)

    p_write = sub.add_parser(
        "write-notion-id",
        help="Cache a Notion data source ID for a group in .kb-local.json.",
    )
    p_write.add_argument("--group", required=True)
    p_write.add_argument("--id", dest="uuid", required=True)

    p_resolve = sub.add_parser(
        "resolve-notion-id",
        help=(
            "Walk env → .kb-local.json cache → config.yaml for a group's "
            "Notion data source ID. JSON to stdout."
        ),
    )
    p_resolve.add_argument("--group", required=True)

    p_lget = sub.add_parser(
        "landing-page-id-get",
        help=(
            "Print the cached 'KB - Updates Review' landing page UUID, "
            "or empty string if not cached. Exit 0 on hit, 1 on miss."
        ),
    )

    p_lset = sub.add_parser(
        "landing-page-id-set",
        help=(
            "Cache the 'KB - Updates Review' landing page UUID after a "
            "successful notion-search discovery. Shared across groups."
        ),
    )
    p_lset.add_argument("--id", dest="page_id", required=True)

    args = parser.parse_args()

    if args.cmd == "mcp-path":
        result = resolve(quiet=args.quiet)
        print(json.dumps(result, indent=2))
        return 0

    if args.cmd == "read-notion-id":
        print(read_notion_id(args.group))
        return 0

    if args.cmd == "write-notion-id":
        write_notion_id(args.group, args.uuid)
        return 0

    if args.cmd == "resolve-notion-id":
        uuid, source = resolve_notion_id_for_group(args.group)
        print(json.dumps({
            "group": args.group,
            "id": uuid,
            "source": source,
        }, indent=2))
        # Exit 0 when resolved, 1 when missing — lets shell callers
        # branch on `if ! resolver resolve-notion-id …; then reconcile`.
        return 0 if uuid else 1

    if args.cmd == "landing-page-id-get":
        cached = read_landing_page_id()
        print(cached)
        return 0 if cached else 1

    if args.cmd == "landing-page-id-set":
        write_landing_page_id(args.page_id)
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
