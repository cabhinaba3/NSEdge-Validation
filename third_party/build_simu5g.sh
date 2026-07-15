#!/bin/bash
set -e

# Setup micromamba environment variables
export MAMBA_ROOT_PREFIX=/proj/oasees-PG0/NS3-Edge/validation_experiment/third_party/micromamba_root
export PATH=$MAMBA_ROOT_PREFIX/envs/sim_env/bin:$PATH

echo "Activating omnetpp-6.0.3..."
export PATH=$PATH:/proj/oasees-PG0/NS3-Edge/validation_experiment/third_party/omnetpp-6.0.3/bin
cd /proj/oasees-PG0/NS3-Edge/validation_experiment/third_party/omnetpp-6.0.3
source setenv -f

echo "Setting up INET 4.5.0 environment..."
cd /proj/oasees-PG0/NS3-Edge/validation_experiment/third_party/inet45_603
source setenv

echo "Building Simu5G..."
cd /proj/oasees-PG0/NS3-Edge/validation_experiment/third_party/Simu5G
make makefiles
make -j$(nproc)
echo "Simu5G Build Complete!"
