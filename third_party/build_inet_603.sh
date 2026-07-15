#!/bin/bash
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$BASE_DIR")"

set -e

echo "Activating omnetpp-6.0.3..."
export PATH=$PATH:"$BASE_DIR"/third_party/omnetpp-6.0.3/bin
cd "$BASE_DIR"/third_party/omnetpp-6.0.3
source setenv -f

echo "Building INET 4.5.0..."
cd "$BASE_DIR"/third_party/inet45_603
source setenv
make makefiles
make -j$(nproc)
