#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
task_verify_dir="${CLAW_CRT_MEMORY_CHECK_DIR:-work/native-crt-memory-check}"
mkdir -p "$task_verify_dir"
swift_flags=()
if [[ "${CLAW_NATIVE_ASAN:-1}" == 1 ]]; then swift_flags+=(-sanitize=address); fi
if [[ "${CLAW_NATIVE_OPTIMIZE:-0}" == 1 ]]; then swift_flags+=(-O); fi
xcrun swiftc $swift_flags Sources/ClawTokenHeap.swift Sources/ClawNativeCrtMemory.swift \
 Tests/NativeCrtMemory/main.swift -o "$task_verify_dir/crt-memory-tests"
"$task_verify_dir/crt-memory-tests"
