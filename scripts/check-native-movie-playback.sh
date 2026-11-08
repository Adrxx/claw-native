#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if [ "$#" -ne 3 ]; then
    echo "usage: $0 <prepared-logo.mp4> <prepared-intro.mp4> <movie-directory>" >&2
    exit 2
fi
mkdir -p work/native-movie-playback-check
xcrun swiftc -swift-version 5 -parse-as-library \
    Sources/ClawNativeMovieCatalog.swift Sources/ClawNativeMoviePlayback.swift Tests/NativeMoviePlayback/main.swift \
    -o work/native-movie-playback-check/check
work/native-movie-playback-check/check "$1" "$2" "$3"
