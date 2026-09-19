# bats-assert - Assertion library for Bats
# Minimal implementation for basic assertions

assert_success() {
    if [ "$status" -ne 0 ]; then
        echo "Command failed with exit code $status"
        return 1
    fi
}

assert_failure() {
    if [ "$status" -eq 0 ]; then
        echo "Command succeeded but expected failure"
        return 1
    fi
}

assert_output() {
    local expected="$1"
    if [ "$output" != "$expected" ]; then
        echo "Expected: $expected"
        echo "Got: $output"
        return 1
    fi
}

assert_line() {
    local expected="$1"
    echo "$output" | grep -q "$expected" || {
        echo "Expected line not found: $expected"
        return 1
    }
}

assert_file_exists() {
    local file="$1"
    if [ ! -e "$file" ]; then
        echo "Expected file to exist: $file"
        return 1
    fi
}

assert_dir_exists() {
    local dir="$1"
    if [ ! -d "$dir" ]; then
        echo "Expected directory to exist: $dir"
        return 1
    fi
}

assert_file_contains() {
    local file="$1"
    local expected="$2"
    if [ ! -e "$file" ]; then
        echo "Expected file to exist: $file"
        return 1
    fi
    if ! grep -q "$expected" "$file"; then
        echo "Expected file $file to contain: $expected"
        return 1
    fi
}
