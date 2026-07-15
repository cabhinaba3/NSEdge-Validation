#!/bin/bash
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$BASE_DIR")"

set -e

export MAMBA_ROOT_PREFIX="$BASE_DIR"/third_party/micromamba_root
export PATH=$MAMBA_ROOT_PREFIX/envs/sim_env/bin:$PATH

echo "Activating omnetpp-5.6.2..."
export PATH=$PATH:"$BASE_DIR"/third_party/omnetpp-5.6.2/bin
cd "$BASE_DIR"/third_party/omnetpp-5.6.2
source setenv -f

echo "Building INET 3.6.4 for OMNeT++ 5.6.2..."
cd "$BASE_DIR"/third_party/inet3_56
make makefiles
make -j$(nproc)
echo "INET 3.6.4 Build Complete!"
