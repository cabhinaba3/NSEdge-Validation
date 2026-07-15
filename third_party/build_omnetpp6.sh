#!/bin/bash
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$BASE_DIR")"

set -e

# Setup micromamba environment variables
export MAMBA_ROOT_PREFIX="$BASE_DIR"/third_party/micromamba_root
export PATH=$MAMBA_ROOT_PREFIX/envs/sim_env/bin:$PATH

echo "Activating omnetpp-6.0.3..."
cd "$BASE_DIR"/third_party/omnetpp-6.0.3
source setenv -f

echo "Configuring OMNeT++ 6.0.3..."
./configure WITH_QTENV=no WITH_OSG=no WITH_OSGEARTH=no

echo "Making OMNeT++ 6.0.3 base..."
make base -j$(nproc)
echo "OMNeT++ 6.0.3 Build Complete!"
