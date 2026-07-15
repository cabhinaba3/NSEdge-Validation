#!/bin/bash
set -e

export MAMBA_ROOT_PREFIX=/proj/oasees-PG0/NS3-Edge/validation_experiment/third_party/micromamba_root
export PATH=$MAMBA_ROOT_PREFIX/envs/sim_env/bin:$PATH

cd /proj/oasees-PG0/NS3-Edge/validation_experiment/third_party

export PATH=$PATH:/proj/oasees-PG0/NS3-Edge/validation_experiment/third_party/omnetpp-5.6.2/bin
cd omnetpp-5.6.2
source setenv -f
cd ..
cd fognetsimpp
# FogNetSim++ uses OMNeT++ makemake with INET
# We need to include INET 3.6.4
export INET_DIR=/proj/oasees-PG0/NS3-Edge/validation_experiment/third_party/inet3_56
opp_makemake -f --deep -O out -KINET_PROJ=$INET_DIR -DINET_IMPORT -I$INET_DIR/src -L$INET_DIR/out/gcc-release/src -lINET
make -j$(nproc)
