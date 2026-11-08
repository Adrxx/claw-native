#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
task_verify_dir="${CLAW_MFC_OWNERSHIP_CHECK_DIR:-work/native-mfc-ownership-identity-check}"
mkdir -p "$task_verify_dir"
object_arguments=(--jobs 1)
swift_flags=()
if [[ "${CLAW_NATIVE_ASAN:-1}" == 1 ]]; then
 object_arguments+=(--asan)
 swift_flags+=(-sanitize=address)
 export CLAW_NATIVE_CXXFLAGS="${CLAW_NATIVE_CXXFLAGS:-} -fsanitize=undefined"
fi
if [[ "${CLAW_NATIVE_OPTIMIZE:-0}" == 1 ]]; then swift_flags+=(-O); fi
task_object_dir="${CLAW_APPLICATION_OBJECT_DIR:-work/native-application-check}"
objects=(${(f)"$(work/test-env/bin/python -m tools.claw.native_objects --dir "$task_object_dir" $object_arguments)"})
xcrun swiftc $swift_flags -import-objc-header Tests/NativeMfcOwnershipIdentity/Bridge.h -I Sources \
 Sources/ClawTokenHeap.swift Sources/ClawNativeCanonicalHost.swift \
 Sources/ClawNativeMfcLocks.swift Sources/ClawNativeMfcMemory.swift \
 Tests/NativeMfcOwnershipIdentity/main.swift $objects -lc++ -o "$task_verify_dir/mfc-ownership-tests"
arguments=()
if [[ "${CLAW_NATIVE_ASAN:-1}" == 0 && "${CLAW_NATIVE_OPTIMIZE:-0}" == 1 ]]; then arguments+=(--require-pointer-reuse); fi
"$task_verify_dir/mfc-ownership-tests" $arguments
