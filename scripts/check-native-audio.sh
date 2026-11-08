#!/bin/zsh
set -euo pipefail
project_dir="${0:A:h:h}"
cd "$project_dir"
mkdir -p work/native-audio-check
objects=()
clang_sanitizers=()
swift_sanitizers=()
if [[ "${CLAW_NATIVE_ASAN:-0}" == 1 ]]; then
 clang_sanitizers=(-fsanitize=address -fno-omit-frame-pointer)
 swift_sanitizers=(-sanitize=address)
fi
for source in AudioPCMTransfer AudioResourceRuntime AudioEvents AmbientAudioBackendRuntime AudioManagerLifecycleRuntime PIDRaster PIDSurfaceRaster AnimationEngine; do
 object="work/native-audio-check/$source.o"
 xcrun clang++ -std=c++17 -ffp-contract=off $clang_sanitizers -c "Sources/$source.cpp" -o "$object"
 objects+=("$object")
done
xcrun swiftc $swift_sanitizers -import-objc-header Sources/Claw-Bridging-Header.h Sources/ClawNativeAudio.swift \
 Sources/ClawAssets.swift Tests/NativeAudio/main.swift $objects -lc++ -lz -o work/native-audio-check/audio-tests
work/native-audio-check/audio-tests App/GameData "$@"
