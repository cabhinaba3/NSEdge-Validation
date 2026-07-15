#!/bin/bash
set -e

echo "Activating omnetpp-6.0.3..."
export PATH=$PATH:/proj/oasees-PG0/NS3-Edge/validation_experiment/third_party/omnetpp-6.0.3/bin
cd /proj/oasees-PG0/NS3-Edge/validation_experiment/third_party/omnetpp-6.0.3
source setenv -f

echo "Building INET 4.5.0..."
cd /proj/oasees-PG0/NS3-Edge/validation_experiment/third_party/inet45_603
source setenv
make makefiles
make -j$(nproc)
