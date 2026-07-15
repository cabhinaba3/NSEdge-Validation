#!/bin/bash
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$BASE_DIR")"

set -e

export MAMBA_ROOT_PREFIX="$BASE_DIR"/third_party/micromamba_root
export PATH=$MAMBA_ROOT_PREFIX/envs/sim_env/bin:$PATH

cd "$BASE_DIR"/third_party

export PATH=$PATH:"$BASE_DIR"/third_party/omnetpp-5.6.2/bin
cd omnetpp-5.6.2
source setenv -f
cd ..
cd fognetsimpp
# FogNetSim++ uses OMNeT++ makemake with INET
# We need to include INET 3.6.4
export INET_DIR="$BASE_DIR"/third_party/inet3_56
opp_makemake -f --deep -O out -KINET_PROJ=$INET_DIR -DINET_IMPORT -I$INET_DIR/src -L$INET_DIR/out/gcc-release/src -lINET
make -j$(nproc)
