#!/bin/bash
set -e

# Setup micromamba environment variables
export MAMBA_ROOT_PREFIX=/proj/oasees-PG0/NS3-Edge/NSEdge-Validation/third_party/micromamba_root
export PATH=$MAMBA_ROOT_PREFIX/envs/sim_env/bin:$PATH

echo "Activating omnetpp-5.6.2..."
export PATH=$PATH:/proj/oasees-PG0/NS3-Edge/NSEdge-Validation/third_party/omnetpp-5.6.2/bin
cd /proj/oasees-PG0/NS3-Edge/NSEdge-Validation/third_party/omnetpp-5.6.2
source setenv -f

echo "Building INET 4.4.0 for OMNeT++ 5.6.2..."
cd /proj/oasees-PG0/NS3-Edge/NSEdge-Validation/third_party/inet4_56
source setenv
make makefiles
make -j$(nproc)
echo "INET for OMNeT++ 5.6.2 Build Complete!"
