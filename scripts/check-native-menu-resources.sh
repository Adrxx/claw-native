#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
mkdir -p work/native-menu-resources
work/test-env/bin/python -m Tests.NativeMenuResources.compare --prepare
objects=(${(f)"$(work/test-env/bin/python -m Tests.NativeMenuResources.build)"})
xcrun swiftc -import-objc-header Sources/ClawNativeMenuResources.h Sources/ClawTokenHeap.swift Sources/ClawNativeMenuResources.swift Tests/NativeMenuResources/main.swift $objects -lc++ -o work/native-menu-resources/check
work/native-menu-resources/check
work/test-env/bin/python -m Tests.NativeMenuResources.compare
