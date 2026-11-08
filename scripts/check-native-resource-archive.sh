#!/bin/zsh
set -euo pipefail
project_dir="${0:A:h:h}"
cd "$project_dir"
mkdir -p work/native-resource-archive-check
objects=()
for source in ResourceArchiveLoadingRuntime ResourceTableConstructionRuntime ResourceNamespaceRuntime ResourceDataRuntime AudioPCMTransfer AudioResourceRuntime CArrayRuntime AmbientAudioBackendRuntime AudioEvents; do
 object="work/native-resource-archive-check/$source.o"
 xcrun clang++ -std=c++17 -ffp-contract=off -Wall -Wextra -Werror -fsanitize=address,undefined -fno-omit-frame-pointer -c "Sources/$source.cpp" -o "$object"
 objects+=("$object")
done
xcrun swiftc -sanitize=address -import-objc-header Tests/NativeResourceArchive/Bridge.h -I Sources Sources/ClawTokenHeap.swift Sources/ClawNativeResourceArchive.swift Tests/NativeResourceArchive/main.swift $objects -lc++ -o work/native-resource-archive-check/archive-tests
work/native-resource-archive-check/archive-tests "$@"
