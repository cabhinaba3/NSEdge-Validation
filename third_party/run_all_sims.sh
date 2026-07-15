#!/bin/bash
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$BASE_DIR")"

set -e

export MAMBA_ROOT_PREFIX="$BASE_DIR"/third_party/micromamba_root
eval "$("$BASE_DIR"/third_party/micromamba/micromamba shell hook -s bash)"
micromamba activate sim_env

cd "$BASE_DIR"/third_party

echo "Building FogNetSim++..."
export PATH=$PATH:"$BASE_DIR"/third_party/omnetpp-5.6.2/bin
cd omnetpp-5.6.2
source setenv -f
cd ..

if [ ! -d "fognetsimpp" ]; then
    git clone https://github.com/rtqayyum/fognetsimpp.git
fi
cd fognetsimpp
# Setup FogNetSim++
opp_makemake -f --deep -O out || true
make -j$(nproc) || true

echo "Running FogNetSim++ baseline simulation..."
cd simulations
# Run the generic IoT simulation to measure execution overhead for 10s of simulation
(time opp_run -u Cmdenv -c General -n .:../src omnetpp.ini --sim-time-limit=10s) > fognetsim_results.txt 2>&1 || true

echo "Extracting Execution Time from FogNetSim++..."
grep "Elapsed:" fognetsim_results.txt > fognetsim_exec.txt || true
cd ../..

echo "Building Simu5G..."
export PATH=$PATH:"$BASE_DIR"/third_party/omnetpp-6.0.3/bin
cd omnetpp-6.0.3
source setenv -f
cd ..

if [ ! -d "inet4" ]; then
    wget https://github.com/inet-framework/inet/releases/download/v4.4.0/inet-4.4.0-src.tgz
    tar -xzf inet-4.4.0-src.tgz
    mv inet-4.4.0 inet4
    cd inet4
    make makefiles
    make -j$(nproc)
    cd ..
fi

if [ ! -d "Simu5G" ]; then
    git clone https://github.com/Simu5G/Simu5G.git
fi
cd Simu5G
# Build Simu5G
make makefiles || true
make -j$(nproc) || true

echo "Running Simu5G baseline simulation..."
cd simulations/NR
# Run the NR simulation to measure execution overhead for 10s of simulation
(time opp_run -u Cmdenv -c General -n .:../../src:../../../inet4/src omnetpp.ini --sim-time-limit=10s) > simu5g_results.txt 2>&1 || true

echo "Extracting Execution Time from Simu5G..."
grep "Elapsed:" simu5g_results.txt > simu5g_exec.txt || true
cd ../../..

echo "Done running simulations!"
