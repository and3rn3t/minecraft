#!/usr/bin/env bash
# Syntax-check shell scripts, skipping BATS test files.
#
# Mirrors the "Check shell script syntax" step in .github/workflows/main.yml.
# BATS files use `@test "name" { ... }`, which is not valid bash, so `bash -n`
# rejects them; CI skips them and so must this, or the hook blocks every commit
# that touches a test.
set -euo pipefail

status=0
for script in "$@"; do
    if grep -qE '^@test|^#!/usr/bin/env bats|^#!/bin/bats' "$script"; then
        continue
    fi
    if ! bash -n "$script"; then
        status=1
    fi
done
exit $status
