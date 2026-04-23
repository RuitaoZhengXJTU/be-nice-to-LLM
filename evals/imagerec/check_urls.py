#!/usr/bin/env python3
"""Smoke-check all image URLs in evals/imagerec/problems/ YAML files.
Stdlib only -- no pip installs needed.
Usage: python check_urls.py [problems_dir]
"""
import urllib.request
import pathlib
import sys


def check_url(url: str, timeout: int = 10) -> tuple:
    """Returns (status_code, ok_bool)."""
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.status == 200
    except Exception:
        return None, False


def main():
    problems_dir = (
        pathlib.Path(sys.argv[1])
        if len(sys.argv) > 1
        else pathlib.Path(__file__).parent / "problems"
    )
    yaml_files = sorted(f for f in problems_dir.glob("*.yaml") if f.stem != "manifest")

    if not yaml_files:
        print(f"No YAML instance files found in {problems_dir}")
        return

    failures = []
    for yf in yaml_files:
        url = None
        for line in yf.read_text().splitlines():
            line = line.strip()
            if line.startswith("image_url:"):
                url = line.split("image_url:", 1)[1].strip().strip('"').strip("'")
                break
        if url is None:
            print(f"  {yf.stem}: no image_url -- SKIP")
            continue
        status, ok = check_url(url)
        marker = "OK" if ok else "FAIL"
        print(f"  {yf.stem}: {status} {marker} -- {url}")
        if not ok:
            failures.append(yf.stem)

    print()
    if failures:
        print(f"FAILURES ({len(failures)}): {failures}")
        sys.exit(1)
    else:
        print(f"All {len(yaml_files)} URLs: 200 OK")


if __name__ == "__main__":
    main()
