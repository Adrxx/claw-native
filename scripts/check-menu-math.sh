#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
mkdir -p work/menu-on-screen
xcrun clang++ -std=c++17 -O1 -ffunction-sections -fdata-sections -Wl,-dead_strip \
  -I Sources Tests/NativeMenuMath/main.cpp Sources/ClawNativeMenuInterface.cpp \
  -o work/menu-on-screen/menu-math
work/menu-on-screen/menu-math
