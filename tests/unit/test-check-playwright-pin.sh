#!/usr/bin/env bats
# Unit Tests: check-playwright-pin.sh
#
# The script reads four files in a throwaway project: the lockfile (the source of
# truth), package.json, the Makefile and the workflow. Each test builds that project
# with one thing out of step, since the failure it exists to catch is one pin being
# updated alone.

load '../helpers/bats-support/load'
load '../helpers/bats-assert/load'

setup() {
    REPO_DIR="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
    TEST_DIR="$(mktemp -d)"
    mkdir -p "$TEST_DIR/web" "$TEST_DIR/.github/workflows"
    cp -R "$REPO_DIR/scripts" "$TEST_DIR/scripts"
    cd "$TEST_DIR" || exit 1
    make_project 1.63.0 1.63.0 1.63.0 1.63.0 1.63.0
}

teardown() {
    cd / || true
    rm -rf "$TEST_DIR"
}

# tests/helpers/bats-assert is a minimal stub (exact assert_output, regex
# assert_line, no refute), so substring checks are done here, as fixed strings.
has() { [[ "$output" == *"$1"* ]] || { echo "expected output to contain: $1"; echo "got: $output"; return 1; }; }
lacks() { [[ "$output" != *"$1"* ]] || { echo "expected output NOT to contain: $1"; echo "got: $output"; return 1; }; }

# make_project <lockfile> <pkg @playwright/test> <pkg playwright> <makefile image> <workflow image>
# Versions are written as given, so "^1.63.0" makes a caret range.
make_project() {
    cat > web/package-lock.json <<JSON
{"name": "web", "packages": {"": {}, "node_modules/@playwright/test": {"version": "$1"}, "node_modules/playwright": {"version": "$1"}}}
JSON
    cat > web/package.json <<JSON
{"name": "web", "devDependencies": {"@playwright/test": "$2", "playwright": "$3", "vite": "^6.0.0"}}
JSON
    printf 'PLAYWRIGHT_IMAGE := mcr.microsoft.com/playwright:v%s-noble\n' "$4" > Makefile
    cat > .github/workflows/main.yml <<YAML
jobs:
  playwright-tests:
    container:
      image: mcr.microsoft.com/playwright:v$5-noble
YAML
}

check() { ./scripts/check-playwright-pin.sh; }

@test "everything agreeing passes and says what the version is" {
    run check
    assert_success
    has "1.63.0"
    has "all pin 1.63.0"
}

@test "the image in the workflow updated alone fails and names both versions" {
    make_project 1.63.0 1.63.0 1.63.0 1.63.0 1.64.0

    run check
    assert_failure
    has "the playwright-tests job in main.yml is v1.64.0"
    has "the lockfile has 1.63.0"
}

@test "the lockfile updated alone fails against both images" {
    make_project 1.64.0 1.64.0 1.64.0 1.63.0 1.63.0

    run check
    assert_failure
    has "the image in the Makefile is v1.63.0"
    has "the image in the playwright-tests job in main.yml is v1.63.0"
}

@test "the Makefile's image updated alone fails" {
    make_project 1.63.0 1.63.0 1.63.0 1.64.0 1.63.0

    run check
    assert_failure
    has "the image in the Makefile is v1.64.0"
    lacks "main.yml is"
}

@test "a caret range in package.json fails, because the pin must be exact" {
    make_project 1.63.0 '^1.63.0' 1.63.0 1.63.0 1.63.0

    run check
    assert_failure
    has "pins @playwright/test to '^1.63.0'"
    has "pin it exactly"
}

@test "playwright pinned to a different version than @playwright/test fails" {
    make_project 1.63.0 1.63.0 1.62.1 1.63.0 1.63.0

    run check
    assert_failure
    has "pins playwright to '1.62.1'"
}

@test "every disagreement is reported, not just the first" {
    make_project 1.63.0 '^1.63.0' 1.62.1 1.64.0 1.65.0

    run check
    assert_failure
    has "@playwright/test"
    has "pins playwright"
    has "Makefile"
    has "main.yml"
}

@test "a workflow with two Playwright images fails: it cannot say which one runs the tests" {
    cat >> .github/workflows/main.yml <<'YAML'
  other-job:
    container:
      image: mcr.microsoft.com/playwright:v1.63.0-noble
YAML

    run check
    assert_failure
    has "exactly one Playwright image tag in the playwright-tests job in main.yml, found 2"
}

@test "a workflow with no Playwright image fails" {
    printf 'jobs:\n  playwright-tests:\n    runs-on: ubuntu-latest\n' > .github/workflows/main.yml

    run check
    assert_failure
    has "found 0"
}

@test "an unreadable lockfile is reported as such, not as a mismatch" {
    echo 'not json' > web/package-lock.json

    run check
    assert_failure
    [ "$status" -eq 2 ]
    has "Could not read the @playwright/test version"
}

@test "it works with only the basic tools on PATH" {
    mkdir -p bin
    ln -s "$(command -v python3)" bin/python3
    for tool in sed grep dirname cat printf; do
        ln -sf "$(command -v $tool)" "bin/$tool" 2> /dev/null || true
    done

    PATH="$TEST_DIR/bin:/usr/bin:/bin" run check
    assert_success
    has "all pin 1.63.0"
}
