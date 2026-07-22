#!/usr/bin/env python3
"""Post-deploy smoke: health + anonymous lookup + score.

Usage:
  python scripts/deploy_smoke.py \\
    --api-base https://api.nh-iq.com \\
    --web-base https://nh-iq.com \\
    --address "609 SE Jamaica Dr, Bentonville, AR"

Exit 0 on success; non-zero on failure. Never prints secrets.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request


def _get(url: str, timeout: float = 60.0) -> tuple[int, str]:
    req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="NeighborhoodInsight deploy smoke")
    p.add_argument("--api-base", required=True, help="Public API origin, e.g. https://api.nh-iq.com")
    p.add_argument("--web-base", default="", help="Optional public web origin")
    p.add_argument(
        "--address",
        default="609 SE Jamaica Dr, Bentonville, AR",
        help="Anonymous lookup smoke address",
    )
    p.add_argument("--skip-web", action="store_true", help="Skip web GET even if --web-base set")
    args = p.parse_args(argv)

    api = args.api_base.rstrip("/")
    print(f"smoke: GET {api}/health")
    status, body = _get(f"{api}/health")
    if status != 200:
        print(f"error: health HTTP {status}: {body[:200]}", file=sys.stderr)
        return 1
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        print(f"error: health non-JSON: {body[:200]}", file=sys.stderr)
        return 1
    if payload.get("status") != "ok":
        print(f"error: health status not ok: {payload!r}", file=sys.stderr)
        return 1
    print("smoke: health ok")

    if args.web_base and not args.skip_web:
        web = args.web_base.rstrip("/")
        print(f"smoke: GET {web}/")
        # HTML home — accept 200
        req = urllib.request.Request(web + "/", method="GET")
        try:
            with urllib.request.urlopen(req, timeout=60.0) as resp:
                if resp.status != 200:
                    print(f"error: web HTTP {resp.status}", file=sys.stderr)
                    return 1
        except urllib.error.HTTPError as exc:
            print(f"error: web HTTP {exc.code}", file=sys.stderr)
            return 1
        print("smoke: web ok")

    q = urllib.parse.urlencode({"address": args.address})
    lookup_url = f"{api}/api/v1/lookup?{q}"
    print(f"smoke: GET lookup address={args.address!r}")
    status, body = _get(lookup_url, timeout=120.0)
    if status != 200:
        print(f"error: lookup HTTP {status}: {body[:300]}", file=sys.stderr)
        return 1
    try:
        lookup = json.loads(body)
    except json.JSONDecodeError:
        print(f"error: lookup non-JSON: {body[:200]}", file=sys.stderr)
        return 1
    address_id = lookup.get("address_id")
    if not address_id:
        print(f"error: lookup missing address_id: {lookup!r}", file=sys.stderr)
        return 1
    print(f"smoke: lookup ok address_id={address_id}")

    score_url = f"{api}/api/v1/score/{address_id}"
    print(f"smoke: GET score/{address_id}")
    status, body = _get(score_url, timeout=120.0)
    if status != 200:
        print(f"error: score HTTP {status}: {body[:300]}", file=sys.stderr)
        return 1
    try:
        report = json.loads(body)
    except json.JSONDecodeError:
        print(f"error: score non-JSON: {body[:200]}", file=sys.stderr)
        return 1
    # Accept full report or computing status shapes
    if "overall_score" in report or report.get("status") in ("computing", "ok", None) or "address_normalized" in report:
        print("smoke: score/report ok")
        return 0
    print(f"error: unexpected score payload keys: {list(report)[:20]}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
