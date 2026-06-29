#!/usr/bin/env python3
"""
perplexity-sonar.py

Thin wrapper around the Perplexity Sonar API for dossier subagents. Preferred
primary path for web research in the generate-dossier skill.
If this script fails (missing key, network, HTTP error), the caller is expected
to cascade to Perplexity MCP, then to WebSearch / WebFetch.

Usage:
    python3 perplexity-sonar.py --query "..."
    python3 perplexity-sonar.py --query "..." --model sonar-pro
    python3 perplexity-sonar.py --query "..." --recency month
    python3 perplexity-sonar.py --query "..." --system "custom system prompt"
    python3 perplexity-sonar.py --query "..." --output result.json

Output: JSON on stdout with shape:
    {
      "query": "...",
      "model": "sonar-pro",
      "response": "...",
      "citations": ["https://...", ...]
    }

Exit codes (deterministic so callers can branch to fallback tiers):
    0  success
    2  PERPLEXITY_API_KEY not set
    3  HTTP error from Perplexity (non-2xx)
    4  request timed out
    5  other request failure (DNS, connection, etc.)
    6  missing `requests` dependency

Requires: PERPLEXITY_API_KEY environment variable (or a .env file in CWD).
Install: pip install requests python-dotenv
"""

import argparse
import json
import os
import sys

try:
    import requests
except ImportError:
    print(
        "Error: requests not installed. Run: pip install requests",
        file=sys.stderr,
    )
    sys.exit(6)

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
DEFAULT_MODEL = "sonar-pro"
DEFAULT_SYSTEM_PROMPT = (
    "You are a research assistant helping build an insurance account dossier. "
    "Return specific, evidence-based findings grounded in primary sources "
    "(annual reports, 10-Ks, shareholder letters, IR pages, official press "
    "releases, earnings transcripts). Prefer recent material (last 12-18 "
    "months). Always cite sources. Be conservative: if a fact is not in a "
    "primary source, say so explicitly rather than guessing."
)


def get_api_key():
    key = os.environ.get("PERPLEXITY_API_KEY")
    if not key:
        print(
            "Error: PERPLEXITY_API_KEY not set. Fallback to Perplexity MCP or "
            "WebSearch/WebFetch.",
            file=sys.stderr,
        )
        sys.exit(2)
    return key


def research(query, model=DEFAULT_MODEL, recency=None, system_prompt=None):
    api_key = get_api_key()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt or DEFAULT_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
        "temperature": 0.1,
        "return_citations": True,
    }

    if recency:
        payload["search_recency_filter"] = recency

    try:
        response = requests.post(
            PERPLEXITY_API_URL, headers=headers, json=payload, timeout=60
        )
        response.raise_for_status()
        data = response.json()

        return {
            "query": query,
            "model": model,
            "response": data["choices"][0]["message"]["content"],
            "citations": data.get("citations", []),
        }

    except requests.exceptions.Timeout:
        print(
            "Error: Perplexity Sonar request timed out. Cascade to MCP or WebSearch.",
            file=sys.stderr,
        )
        sys.exit(4)
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "?"
        body = e.response.text if e.response is not None else ""
        print(
            f"Error: Perplexity Sonar returned HTTP {status}: {body[:400]}",
            file=sys.stderr,
        )
        sys.exit(3)
    except Exception as e:
        print(f"Error: Perplexity Sonar request failed: {e}", file=sys.stderr)
        sys.exit(5)


def main():
    parser = argparse.ArgumentParser(
        description="Query Perplexity Sonar and print JSON with the answer + citations."
    )
    parser.add_argument("--query", required=True, help="Research query to send.")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Sonar model name (default: {DEFAULT_MODEL}). Examples: sonar, sonar-pro, sonar-reasoning.",
    )
    parser.add_argument(
        "--recency",
        choices=["day", "week", "month", "year"],
        default=None,
        help="Optional search recency filter.",
    )
    parser.add_argument(
        "--system",
        default=None,
        help="Optional system prompt override. Defaults to the dossier research persona.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional output file path. Defaults to stdout.",
    )

    args = parser.parse_args()

    print(f"Researching via Sonar: {args.query[:80]}...", file=sys.stderr)
    result = research(
        args.query,
        model=args.model,
        recency=args.recency,
        system_prompt=args.system,
    )
    print(
        f"Done. Response: {len(result['response'])} chars, "
        f"{len(result['citations'])} citations",
        file=sys.stderr,
    )

    output = json.dumps(result, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Results saved to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
