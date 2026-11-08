#!/bin/zsh
set -euo pipefail
project_dir="${0:A:h:h}"
cd "$project_dir"
task_verify_dir="${CLAW_APPLICATION_STARTUP_CHECK_DIR:-work/native-application-startup-check}"
mkdir -p "$task_verify_dir"
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
# Reuse the existing native application's cache; no payload scan or project generation.
task_object_dir="${CLAW_APPLICATION_OBJECT_DIR:-work/native-application-check}"
objects=(${(f)"$(work/test-env/bin/python -m tools.claw.native_objects --dir "$task_object_dir" $object_arguments)"})
work/test-env/bin/python -m Tests.NativeApplicationStartup.reference "$task_verify_dir/reference.json"
xcrun swiftc $swift_flags -import-objc-header Tests/NativeApplicationStartup/Bridge.h -I Sources \
 Sources/ClawTokenHeap.swift Sources/ClawNativeResourceArchive.swift Sources/ClawNativeCanonicalHost.swift \
 Sources/ClawNativeRandom.swift Sources/ClawNativeApplicationStartup.swift Sources/ClawNativeApplication.swift \
 Tests/NativeApplicationStartup/main.swift $objects -lc++ -lz -o "$task_verify_dir/startup-tests"
"$task_verify_dir/startup-tests" "$task_verify_dir/reference.json"
