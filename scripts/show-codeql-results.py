#!/usr/bin/env python3
"""Print a CodeQL SARIF file as a readable list.

`make codeql` writes SARIF because that is what the GitHub action uploads, but
SARIF is not something you want to read.

With --changed-since, this filters to results sitting on lines the branch
actually touched, which is what the CodeQL check reports on a pull request
("new alerts in code changed by this pull request"). Without it you get the
whole baseline, which on this repo is in the hundreds and tells you nothing
about the change in front of you.
"""

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

# SARIF severities, most serious first.
LEVEL_ORDER = {"error": 0, "warning": 1, "note": 2, "none": 3}

HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def changed_lines(base):
    """Map each changed file to the set of line numbers the branch touched.

    The diff is taken from the merge base to the *working tree*, not to HEAD:
    CodeQL analysed the files as they are on disk, so comparing against the
    last commit would miss uncommitted work — which is exactly the work you
    are trying to check before pushing it.
    """
    try:
        merge_base = subprocess.run(
            ["git", "merge-base", base, "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        diff = subprocess.run(
            ["git", "diff", "-U0", merge_base],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
    except subprocess.CalledProcessError as exc:
        print(f"Could not diff against {base}: {exc}", file=sys.stderr)
        return None

    touched = {}
    current = None
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            touched.setdefault(current, set())
        elif line.startswith("@@") and current:
            match = HUNK.match(line)
            if match:
                start = int(match.group(1))
                count = int(match.group(2) or 1)
                touched[current].update(range(start, start + count))

    # A file that is new and not yet added shows up in neither the diff nor the
    # index, but CodeQL analysed it along with everything else on disk. Without
    # this, results in a brand-new file are silently reported as clean, which is
    # the exact failure this filter exists to avoid.
    for path in untracked:
        try:
            line_count = sum(1 for _ in Path(path).open("rb"))
        except OSError:
            continue
        touched.setdefault(path, set()).update(range(1, line_count + 2))

    return touched


def load_results(path):
    sarif = json.loads(path.read_text())
    results = []
    for run in sarif.get("runs", []):
        rules = {r["id"]: r for r in run.get("tool", {}).get("driver", {}).get("rules", [])}
        for result in run.get("results", []):
            rule_id = result.get("ruleId", "?")
            rule = rules.get(rule_id, {})
            level = result.get("level") or rule.get("defaultConfiguration", {}).get("level", "note")
            locations = result.get("locations") or []
            if locations:
                physical = locations[0].get("physicalLocation", {})
                file_path = physical.get("artifactLocation", {}).get("uri", "?")
                line = physical.get("region", {}).get("startLine", 0)
            else:
                file_path, line = "?", 0
            results.append(
                {
                    "level": level,
                    "rule": rule_id,
                    "name": rule.get("shortDescription", {}).get("text", rule_id),
                    "message": (result.get("message", {}).get("text", "") or "").split("\n")[0],
                    "file": file_path,
                    "line": line,
                }
            )
    return results


def summarise(results, label):
    counts = Counter(r["level"] for r in results)
    parts = ", ".join(
        f"{counts[level]} {level}" for level in sorted(counts, key=lambda lv: LEVEL_ORDER.get(lv, 9))
    )
    print(f"{label}: {len(results)} results" + (f" ({parts})" if parts else ""))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sarif", nargs="?", default="codeql-results.sarif", type=Path)
    parser.add_argument(
        "--changed-since",
        metavar="REF",
        help="Only show results on lines changed relative to REF, e.g. origin/main",
    )
    args = parser.parse_args()

    if not args.sarif.exists():
        print(f"No results file at {args.sarif}", file=sys.stderr)
        return 1

    results = load_results(args.sarif)
    if not results:
        print("CodeQL found nothing.")
        return 0

    results.sort(key=lambda r: (LEVEL_ORDER.get(r["level"], 9), r["file"], r["line"]))
    summarise(results, "Whole repository")

    shown = results
    if args.changed_since:
        touched = changed_lines(args.changed_since)
        if touched is None:
            return 1
        shown = [r for r in results if r["line"] in touched.get(r["file"], ())]
        print()
        summarise(shown, f"On lines changed since {args.changed_since}")

    print()
    if not shown:
        print("Nothing on the lines this branch touched.")
        return 0

    for r in shown:
        print(f"{r['level']:>7}  {r['file']}:{r['line']}")
        print(f"         {r['name']}")
        if r["message"] and r["message"] != r["name"]:
            print(f"         {r['message'][:160]}")
        print()

    # Errors are what turn the check red on a pull request.
    return 1 if any(r["level"] == "error" for r in shown) else 0


if __name__ == "__main__":
    sys.exit(main())
