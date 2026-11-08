#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
task_verify_dir="${CLAW_DIAGNOSTICS_CHECK_DIR:-work/native-diagnostics-check}"
mkdir -p "$task_verify_dir"
work/test-env/bin/python -m Tests.NativeDiagnostics.reference "$task_verify_dir/reference.json"
PYTHONPATH=. work/test-env/bin/python scripts/prepare-diagnostic-assets.py
compile_flags=(-std=c++17 -I Sources)
swift_flags=()
if [[ "${CLAW_NATIVE_ASAN:-1}" == 1 ]]; then
    compile_flags+=(-fsanitize=address,undefined -fno-omit-frame-pointer)
    swift_flags+=(-sanitize=address)
fi
if [[ "${CLAW_NATIVE_OPTIMIZE:-0}" == 1 ]]; then
    compile_flags+=(-O2)
    swift_flags+=(-O)
fi
xcrun clang++ $compile_flags -c Sources/MenuDiagnosticPolicyRuntime.cpp -o "$task_verify_dir/policy.o"
xcrun swiftc $swift_flags -import-objc-header Tests/NativeDiagnostics/Bridge.h -I Sources \
    Sources/ClawNativeDiagnostics.swift Tests/NativeDiagnostics/main.swift \
    "$task_verify_dir/policy.o" -lc++ -o "$task_verify_dir/diagnostics-check"
"$task_verify_dir/diagnostics-check" "$task_verify_dir/reference.json" App/GameData/DiagnosticPolicy.json
