#!/bin/zsh
set -euo pipefail
project_dir="${0:A:h:h}"
cd "$project_dir"
task_verify_dir="${CLAW_APPLICATION_TEXT_CHECK_DIR:-work/native-application-text-check}"
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
work/test-env/bin/python -m Tests.NativeApplicationText.reference "$task_verify_dir/reference.json"
work/test-env/bin/python scripts/prepare-application-assets.py
xcrun swiftc $swift_flags -import-objc-header Tests/NativeApplicationText/Bridge.h -I Sources \
 Sources/ClawTokenHeap.swift Sources/ClawNativeResourceArchive.swift Sources/ClawNativeCanonicalHost.swift \
 Sources/ClawNativeRandom.swift Sources/ClawNativeApplicationMetadata.swift Sources/ClawNativeApplicationStartup.swift Sources/ClawNativeApplication.swift \
 Tests/NativeApplicationText/main.swift $objects -lc++ -lz -o "$task_verify_dir/text-tests"
"$task_verify_dir/text-tests" "$task_verify_dir/reference.json" App/GameData/APPLICATION/startup.json \
 Original/claw-disc/files/DATA/CLAW.REZ work/media/source/CLAW.FEC
