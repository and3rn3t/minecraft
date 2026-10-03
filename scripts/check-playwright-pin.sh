#!/bin/bash
# Check that every place Playwright's version is pinned agrees.
#
# The visual-regression baselines are only valid in the Playwright image that drew
# them, and CI runs the browser tests in that image, so the image tag must equal the
# @playwright/test version the lockfile installs. The version lives in:
#
#   web/package-lock.json            (the source of truth: what npm ci installs)
#   web/package.json                 @playwright/test and playwright, pinned exactly
#   Makefile                         PLAYWRIGHT_IMAGE
#   .github/workflows/main.yml       the playwright-tests job's container image
#
# The image tag in the workflow has to be a literal (a job's container cannot read a
# variable), so this reads it from the file instead of repeating the version, which
# is how a check ends up passing while the image and the package disagree.
#
# Run by the playwright-tests job in CI; also fine to run by hand.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source-path=SCRIPTDIR
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

LOCKFILE="${PROJECT_DIR}/web/package-lock.json"
PACKAGE_JSON="${PROJECT_DIR}/web/package.json"
MAKEFILE="${PROJECT_DIR}/Makefile"
WORKFLOW="${PROJECT_DIR}/.github/workflows/main.yml"

# json_get <file> <key>...: the value at that path in a JSON file. Node where there is
# one (the CI container has it), python3 otherwise. Prints nothing if the path is absent.
json_get() {
    local file="$1"
    shift
    if command -v node > /dev/null 2>&1; then
        node -e 'let c = JSON.parse(require("fs").readFileSync(process.argv[1], "utf8"));
for (const k of process.argv.slice(2)) c = c[k];
console.log(c);' "$file" "$@" 2> /dev/null
    else
        python3 -c 'import json, sys
c = json.load(open(sys.argv[1]))
for k in sys.argv[2:]:
    c = c[k]
print(c)' "$file" "$@" 2> /dev/null
    fi
}

FAILED=0
fail() {
    echo -e "${RED}✗ $1${NC}" >&2
    FAILED=1
}

# check_image_tag <label> <file> <sed-pattern>: the one Playwright image tag in a file
# must equal the locked version. The pattern's single group is the version.
check_image_tag() {
    local label="$1" file="$2" pattern="$3" tags count
    tags="$(sed -n "$pattern" "$file")"
    count="$(printf '%s\n' "$tags" | grep -c . || true)"
    if [ "$count" -ne 1 ]; then
        fail "expected exactly one Playwright image tag in ${label}, found ${count}"
    elif [ "$tags" != "$locked" ]; then
        fail "the image in ${label} is v${tags}, the lockfile has ${locked}"
    fi
}

locked="$(json_get "$LOCKFILE" packages node_modules/@playwright/test version || true)"
if [ -z "$locked" ]; then
    echo -e "${RED}Could not read the @playwright/test version from web/package-lock.json${NC}" >&2
    exit 2
fi

echo "@playwright/test in the lockfile: ${locked}"

for pkg in "@playwright/test" "playwright"; do
    declared="$(json_get "$PACKAGE_JSON" devDependencies "$pkg" || true)"
    if [ "$declared" != "$locked" ]; then
        fail "web/package.json pins ${pkg} to '${declared:-nothing}', the lockfile has ${locked} (pin it exactly)"
    fi
done

check_image_tag "the Makefile" "$MAKEFILE" \
    's|^PLAYWRIGHT_IMAGE := mcr.microsoft.com/playwright:v\([0-9][0-9.]*\)-.*|\1|p'
check_image_tag "the playwright-tests job in main.yml" "$WORKFLOW" \
    's|^[[:space:]]*image: mcr.microsoft.com/playwright:v\([0-9][0-9.]*\)-.*|\1|p'

if [ "$FAILED" -ne 0 ]; then
    echo "" >&2
    echo "Update all four together, run make test-visual, and only if screenshots differ" >&2
    echo "run make test-visual-update and look at the new images (see docs/CI_CD.md)." >&2
    exit 1
fi

echo -e "${GREEN}✓ The lockfile, package.json, the Makefile and the workflow all pin ${locked}${NC}"
