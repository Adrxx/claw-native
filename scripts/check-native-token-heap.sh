#!/bin/zsh
set -euo pipefail
project_dir="${0:A:h:h}"
cd "$project_dir"
task_verify_dir="${CLAW_TOKEN_HEAP_CHECK_DIR:-work/native-token-heap-check}"
mkdir -p "$task_verify_dir"
swift_flags=()
if [[ "${CLAW_NATIVE_ASAN:-0}" == 1 ]]; then
  swift_flags=(-sanitize=address)
fi
swiftc $swift_flags Sources/ClawTokenHeap.swift Tests/NativeTokenHeap/main.swift \
  -o "$task_verify_dir/token-heap-tests"
"$task_verify_dir/token-heap-tests"
