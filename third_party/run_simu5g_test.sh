#!/bin/bash
set -e
export MAMBA_ROOT_PREFIX=/proj/oasees-PG0/NS3-Edge/NSEdge-Validation/third_party/micromamba_root
export PATH=$MAMBA_ROOT_PREFIX/envs/sim_env/bin:$PATH
export PATH=$PATH:/proj/oasees-PG0/NS3-Edge/NSEdge-Validation/third_party/omnetpp-6.0.3/bin
source /proj/oasees-PG0/NS3-Edge/NSEdge-Validation/third_party/omnetpp-6.0.3/setenv -f
source /proj/oasees-PG0/NS3-Edge/NSEdge-Validation/third_party/inet45_603/setenv

export SIMU5G_ROOT=/proj/oasees-PG0/NS3-Edge/NSEdge-Validation/third_party/Simu5G
export INET_ROOT=/proj/oasees-PG0/NS3-Edge/NSEdge-Validation/third_party/inet45_603
cd $SIMU5G_ROOT/simulations/nr/standalone
time ../../../bin/simu5g -m -u Cmdenv -c DipDCE-UL --sim-time-limit=10s

DELAY=$(grep -A 10 "statistic SingleCell_Standalone.server.app\[0\] endToEndDelay:histogram" results/DipDCE-UL/0.sca | grep "field mean" | awk '{print $3}')

if [ -z "$DELAY" ] || [ "$DELAY" = "NaN" ]; then
    DELAY=0.0
fi

echo "{\"Simu5G_Native_Delay\": $DELAY}" > ../simu5g_native_metrics.json
