#!/bin/bash
set -e

export MAMBA_ROOT_PREFIX=/proj/oasees-PG0/NS3-Edge/validation_experiment/third_party/micromamba_root
export PATH=$MAMBA_ROOT_PREFIX/envs/sim_env/bin:$PATH

echo "Activating omnetpp-5.6.2..."
export PATH=$PATH:/proj/oasees-PG0/NS3-Edge/validation_experiment/third_party/omnetpp-5.6.2/bin
cd /proj/oasees-PG0/NS3-Edge/validation_experiment/third_party/omnetpp-5.6.2
source setenv -f

echo "Building INET 3.6.4 for OMNeT++ 5.6.2..."
cd /proj/oasees-PG0/NS3-Edge/validation_experiment/third_party/inet3_56
make makefiles
make -j$(nproc)
echo "INET 3.6.4 Build Complete!"
