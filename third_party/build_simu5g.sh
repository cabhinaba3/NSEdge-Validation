#!/bin/bash
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$BASE_DIR")"

set -e

# Setup micromamba environment variables
export MAMBA_ROOT_PREFIX="$BASE_DIR"/third_party/micromamba_root
export PATH=$MAMBA_ROOT_PREFIX/envs/sim_env/bin:$PATH

echo "Activating omnetpp-6.0.3..."
export PATH=$PATH:"$BASE_DIR"/third_party/omnetpp-6.0.3/bin
cd "$BASE_DIR"/third_party/omnetpp-6.0.3
source setenv -f

echo "Setting up INET 4.5.0 environment..."
cd "$BASE_DIR"/third_party/inet45_603
source setenv

echo "Building Simu5G..."
cd "$BASE_DIR"/third_party/Simu5G
make makefiles
make -j$(nproc)
echo "Simu5G Build Complete!"
