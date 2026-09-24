#!/usr/bin/env bats
# Unit Tests: docker-compose.registry.yml stays in step with docker-compose.yml
#
# The two files differ only in where the image comes from. The registry file
# once drifted far enough to set the container's memory limit equal to the
# Java heap, which is the restart loop docker-compose.yml warns about, and to
# keep a health check that reported "healthy" before the server accepted
# connections.

load '../helpers/bats-support/load'
load '../helpers/bats-assert/load'

setup() {
    REPO_DIR="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
}

# Function to print a compose file from `services:` on, without its image source
without_image_source() {
    sed -n '/^services:/,$p' "$1" |
        sed '/^    build:$/,/^        - MINECRAFT_VERSION/d' |
        sed '/^    # Pulled from GitHub Container Registry/,/^    pull_policy: missing$/d'
}

@test "the registry compose file matches the main one apart from the image source" {
    run diff <(without_image_source "$REPO_DIR/docker-compose.yml") \
        <(without_image_source "$REPO_DIR/docker-compose.registry.yml")
    assert_success
}

@test "the registry compose file pulls rather than builds" {
    run grep -E '^    build:' "$REPO_DIR/docker-compose.registry.yml"
    assert_failure
    run grep -E '^    image: ghcr.io/' "$REPO_DIR/docker-compose.registry.yml"
    assert_success
}
