#!/bin/zsh
set -euo pipefail
project_dir="${0:A:h:h}"
cd "$project_dir"
task_verify_dir="${CLAW_MFC_TLS_MANAGER_CHECK_DIR:-work/native-mfc-tls-manager-check}"
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
# Ignored-object substitution permits a focused frame mutation check without
# editing the admitted source or its independent family cases.
if [[ -n "${CLAW_MFC_TLS_MANAGER_OBJECT:-}" ]]; then
 for ((index=1; index <= ${#objects}; index++)); do
  if [[ "${objects[$index]}" == */MfcTlsManagerRuntime-*.o ]]; then
   objects[$index]="$CLAW_MFC_TLS_MANAGER_OBJECT"
  fi
 done
fi
work/test-env/bin/python -m Tests.NativeMfcTlsManager.reference "$task_verify_dir/reference.json"
xcrun swiftc $swift_flags -import-objc-header Tests/NativeMfcTlsManager/Bridge.h -I Sources \
 Sources/ClawTokenHeap.swift Sources/ClawNativeResourceArchive.swift Sources/ClawNativeCanonicalHost.swift \
 Sources/ClawNativeRandom.swift Sources/ClawNativeApplicationMetadata.swift Sources/ClawNativeApplicationStartup.swift \
 Sources/ClawNativeApplication.swift Sources/ClawNativeMfcLocks.swift Sources/ClawNativeMfcMemory.swift \
 Tests/NativeMfcTlsManager/main.swift $objects -lc++ -lz -o "$task_verify_dir/mfc-tls-manager-tests"
"$task_verify_dir/mfc-tls-manager-tests" "$task_verify_dir/reference.json"
