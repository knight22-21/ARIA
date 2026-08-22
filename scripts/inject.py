"""Fire a synthetic payment event at the running ARIA API (Path B).

Examples:
    python scripts/inject.py --list
    python scripts/inject.py --scenario hdfc_soft_decline
    python scripts/inject.py --scenario b2b_invoice_overdue --url http://localhost:8000
"""

from __future__ import annotations

import argparse
import json
import sys

import httpx


def main() -> int:
    ap = argparse.ArgumentParser(description="Inject a synthetic payment event into ARIA.")
    ap.add_argument("--scenario", help="scenario name (see --list)")
    ap.add_argument("--url", default="http://localhost:8000", help="ARIA API base URL")
    ap.add_argument("--list", action="store_true", help="list available scenarios")
    ap.add_argument("--no-inline", action="store_true", help="enqueue detection via Celery instead")
    args = ap.parse_args()

    base = args.url.rstrip("/")

    if args.list:
        r = httpx.get(f"{base}/dev/scenarios", timeout=10)
        r.raise_for_status()
        for name in r.json()["scenarios"]:
            print(f"  - {name}")
        return 0

    if not args.scenario:
        ap.error("--scenario is required (or use --list)")

    payload = {"scenario": args.scenario, "inline": not args.no_inline}
    r = httpx.post(f"{base}/dev/inject", json=payload, timeout=60)
    if r.status_code != 200:
        print(f"ERROR {r.status_code}: {r.text}", file=sys.stderr)
        return 1
    print(json.dumps(r.json(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
