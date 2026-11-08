#!/bin/zsh
set -euo pipefail
project_dir="${0:A:h:h}"
cd "$project_dir"
task_verify_dir="${CLAW_APPLICATION_EXECUTION_CHECK_DIR:-work/native-application-execution-check}"
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
task_object_dir="${CLAW_APPLICATION_OBJECT_DIR:-work/native-application-check}"
objects=(${(f)"$(work/test-env/bin/python -m tools.claw.native_objects --dir "$task_object_dir" $object_arguments)"})
# This shared helper owns its original Machine and checks the pinned EXE hash.
work/test-env/bin/python -m Tests.NativeApplicationConfiguration.reference "$task_verify_dir/reference.json"
work/test-env/bin/python scripts/prepare-application-assets.py
sources=(Sources/ClawTokenHeap.swift Sources/ClawNativeResourceArchive.swift Sources/ClawNativeCanonicalHost.swift
 Sources/ClawNativeRandom.swift Sources/ClawNativeApplicationMetadata.swift Sources/ClawNativeApplicationStartup.swift
 Sources/ClawNativeApplication.swift Sources/ClawNativeExecutionLane.swift)
for version in 5 6; do
 xcrun swiftc $swift_flags -parse-as-library -swift-version "$version" -strict-concurrency=complete -warnings-as-errors \
  -import-objc-header Tests/NativeApplicationExecution/Bridge.h -I Sources \
  $sources Tests/NativeApplicationExecution/main.swift $objects -lc++ -lz -o "$task_verify_dir/application-execution-swift$version"
 ASAN_OPTIONS=detect_stack_use_after_return=1 UBSAN_OPTIONS=halt_on_error=1 \
  "$task_verify_dir/application-execution-swift$version" "$task_verify_dir/reference.json" App/GameData/APPLICATION/startup.json
done
for fixture in RejectedApplicationEscape RejectedHeapEscape RejectedPointerEscape; do
 if xcrun swiftc -swift-version 6 -strict-concurrency=complete -warnings-as-errors -typecheck \
  -import-objc-header Tests/NativeApplicationExecution/Bridge.h -I Sources $sources \
  "Tests/NativeApplicationExecution/$fixture.swift" > "$task_verify_dir/$fixture.log" 2>&1; then
  print -u2 "Unsafe application boundary unexpectedly compiled: $fixture"
  exit 1
 fi
 rg -q 'Sendable' "$task_verify_dir/$fixture.log"
done
print 'PASS compiler rejects application, heap and raw pointer async result escape'
