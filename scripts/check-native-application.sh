#!/bin/zsh
set -euo pipefail
project_dir="${0:A:h:h}"
cd "$project_dir"
task_verify_dir="${CLAW_APPLICATION_CHECK_DIR:-work/native-application-check}"
mkdir -p "$task_verify_dir"
# Canonical dispatch links real admitted entries using generated app membership.
# Default to one compiler process; never replace unrelated entries with stubs.
python3 -m tools.claw.gen_project check
object_arguments=(--jobs "${CLAW_NATIVE_JOBS:-1}")
swift_flags=()
if [[ "${CLAW_NATIVE_ASAN:-1}" == 1 ]]; then
 object_arguments+=(--asan)
 swift_flags+=(-sanitize=address)
 export CLAW_NATIVE_CXXFLAGS="${CLAW_NATIVE_CXXFLAGS:-} -fsanitize=undefined"
fi
if [[ "${CLAW_NATIVE_OPTIMIZE:-0}" == 1 ]]; then
 swift_flags+=(-O)
fi
objects=(${(f)"$(work/test-env/bin/python -m tools.claw.native_objects --dir "$task_verify_dir" $object_arguments)"})
work/test-env/bin/python -m Tests.native_bootstrap_manager_reference "$task_verify_dir/bootstrap-reference.json"
xcrun swiftc $swift_flags -import-objc-header Tests/NativeApplication/Bridge.h -I Sources Sources/ClawTokenHeap.swift Sources/ClawNativeResourceArchive.swift Sources/ClawNativeCanonicalHost.swift Sources/ClawNativeRandom.swift Sources/ClawNativeApplicationStartup.swift Sources/ClawNativeApplication.swift Tests/NativeApplication/main.swift $objects -lc++ -lz -o "$task_verify_dir/application-tests"
"$task_verify_dir/application-tests" "$@" "$task_verify_dir/bootstrap-reference.json"
