#!/bin/zsh
set -euo pipefail
project_dir="${0:A:h:h}"
cd "$project_dir"
task_verify_dir="${CLAW_MFC_LOCKS_CHECK_DIR:-work/native-mfc-locks-check}"
mkdir -p "$task_verify_dir"
object_arguments=(--jobs 1)
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
# An optional ignored object permits mutation checks without touching the source.
if [[ -n "${CLAW_MFC_LOCKS_OBJECT:-}" ]]; then
 for ((index=1; index <= ${#objects}; index++)); do
  if [[ "${objects[$index]}" == */MfcStartupLocksRuntime-*.o ]]; then
   objects[$index]="$CLAW_MFC_LOCKS_OBJECT"
  fi
 done
fi
work/test-env/bin/python -m Tests.NativeMfcLocks.reference "$task_verify_dir/reference.json"
xcrun swiftc $swift_flags -import-objc-header Tests/NativeMfcLocks/Bridge.h -I Sources \
 Sources/ClawTokenHeap.swift Sources/ClawNativeResourceArchive.swift Sources/ClawNativeCanonicalHost.swift \
 Sources/ClawNativeRandom.swift Sources/ClawNativeApplicationMetadata.swift Sources/ClawNativeApplicationStartup.swift \
 Sources/ClawNativeApplication.swift Sources/ClawNativeMfcLocks.swift \
 Tests/NativeMfcLocks/main.swift $objects -lc++ -lz -o "$task_verify_dir/mfc-locks-tests"
"$task_verify_dir/mfc-locks-tests" "$task_verify_dir/reference.json"
