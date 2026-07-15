#!/bin/bash
set -e

# Setup micromamba environment variables
export MAMBA_ROOT_PREFIX=/proj/oasees-PG0/NS3-Edge/validation_experiment/third_party/micromamba_root
export PATH=$MAMBA_ROOT_PREFIX/envs/sim_env/bin:$PATH

echo "Activating omnetpp-6.0.3..."
cd /proj/oasees-PG0/NS3-Edge/validation_experiment/third_party/omnetpp-6.0.3
source setenv -f

echo "Configuring OMNeT++ 6.0.3..."
./configure WITH_QTENV=no WITH_OSG=no WITH_OSGEARTH=no

echo "Making OMNeT++ 6.0.3 base..."
make base -j$(nproc)
echo "OMNeT++ 6.0.3 Build Complete!"
