#!/bin/zsh
set -euo pipefail
project_dir="${0:A:h:h}"
cd "$project_dir"
if [[ ! -d work/unshield/.git ]]; then
    git clone --depth 1 --branch 1.6.2 https://github.com/twogood/unshield.git work/unshield
fi
[[ "$(git -C work/unshield rev-parse HEAD)" == 51de441ba6893f11026d4671ccef9e8e2a4634fa ]]
work/test-env/bin/cmake -S work/unshield -B work/unshield-build -DUSE_OUR_OWN_MD5=ON -DBUILD_TESTING=OFF
work/test-env/bin/cmake --build work/unshield-build -j 2
