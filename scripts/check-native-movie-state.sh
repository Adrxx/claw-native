#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
inputs() {
    shasum -a 256 Sources/*.h Sources/*.hpp \
        Sources/MovieStateCleanupRuntime.cpp Sources/BootyProgressionRuntime.cpp \
        Sources/ApplicationLevelProgressionRuntime.cpp Sources/ClawTokenHeap.swift \
        Sources/ClawNativeMovieStateServices.swift Tests/NativeMovieState/* \
        scripts/check-native-movie-state.sh
    clang++ --version
    swiftc --version 2>&1
}
key=$(inputs | shasum -a 256 | cut -d ' ' -f 1)
build="work/build/movie-state-cleanup/$key"
mkdir -p "$build"
if [[ ! -x "$build/check" ]]; then
    for source in Sources/MovieStateCleanupRuntime.cpp Sources/BootyProgressionRuntime.cpp Sources/ApplicationLevelProgressionRuntime.cpp Tests/NativeMovieState/bridge.cpp Tests/NativeMovieState/unreached.cpp; do
        clang++ -std=c++17 -O2 -Wall -Wextra -Werror -I Sources -I Tests/NativeMovieState -c "$source" -o "$build/$(basename "${source%.cpp}").o"
    done
    swiftc -O -I Sources -import-objc-header Tests/NativeMovieState/bridge.h \
        Sources/ClawTokenHeap.swift Sources/ClawNativeMovieStateServices.swift Tests/NativeMovieState/main.swift \
        "$build/MovieStateCleanupRuntime.o" "$build/BootyProgressionRuntime.o" \
        "$build/ApplicationLevelProgressionRuntime.o" "$build/bridge.o" "$build/unreached.o" \
        -Xlinker -lc++ -o "$build/check-building"
    [[ "$key" == "$(inputs | shasum -a 256 | cut -d ' ' -f 1)" ]]
    mv "$build/check-building" "$build/check"
fi
"$build/check"
