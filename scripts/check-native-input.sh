#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
task_verify_dir=work/native-input-check
mkdir -p "$task_verify_dir"
python3 -m tools.claw.gen_project check
work/test-env/bin/python -m Tests.NativeInput.reference "$task_verify_dir/reference.json"
export CLAW_NATIVE_CXXFLAGS="${CLAW_NATIVE_CXXFLAGS:-} -fsanitize=undefined"
objects=(${(f)"$(work/test-env/bin/python -m tools.claw.native_objects --dir "$task_verify_dir" --asan --jobs "${CLAW_NATIVE_JOBS:-1}")"})
xcrun swiftc -sanitize=address -import-objc-header Tests/NativeInput/Bridge.h -I Sources \
    Sources/ClawTokenHeap.swift Sources/ClawNativeCanonicalHost.swift Tests/NativeInput/main.swift \
    $objects -lc++ -lz -o "$task_verify_dir/input-check"
"$task_verify_dir/input-check" "$task_verify_dir/reference.json"
