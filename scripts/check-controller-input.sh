#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
(( $(sysctl -n vm.loadavg | awk '{printf "%d", $2}') < 16 )) || { echo 'Wait for load below 16' >&2; exit 2; }
task_verify_dir=work/controller-input-check
mkdir -p "$task_verify_dir"
work/test-env/bin/python -m Tests.NativeControllerInput.reference "$task_verify_dir/reference.json"
objects=(${(f)"$(work/test-env/bin/python -m tools.claw.native_objects --dir "$task_verify_dir" --jobs "${CLAW_NATIVE_JOBS:-1}")"})
xcrun swiftc -O -import-objc-header Tests/NativeControllerInput/Bridge.h -I Sources \
    Sources/ClawTokenHeap.swift Sources/ClawNativeCanonicalHost.swift Sources/ClawNativeMfcMemory.swift Sources/ClawNativeMfcLocks.swift Sources/ClawNativeWindowInputQueue.swift Tests/NativeControllerInput/main.swift \
    $objects -lc++ -lz -o "$task_verify_dir/controller-input-check"
"$task_verify_dir/controller-input-check" "$task_verify_dir/reference.json"
