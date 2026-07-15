#!/bin/bash
# ==============================================================================
# Dependency Installation Script for NS3-Edge Third-Party Validation Environment
# ==============================================================================
set -e

# Base installation directory
INSTALL_DIR=$(pwd)
MAMBA_ROOT=$INSTALL_DIR/third_party/micromamba_root
MAMBA_BIN=$INSTALL_DIR/third_party/micromamba/micromamba

echo "1. Initializing isolated micromamba environment..."
if [ ! -f "$MAMBA_BIN" ]; then
    mkdir -p $INSTALL_DIR/third_party/micromamba
    curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj -C $INSTALL_DIR/third_party/micromamba bin/micromamba
fi

export MAMBA_ROOT_PREFIX=$MAMBA_ROOT

echo "2. Setting up base simulation environment (sim_env)..."
# sim_env contains general build tools and python for baseline scripts
if [ ! -d "$MAMBA_ROOT/envs/sim_env" ]; then
    $MAMBA_BIN create -y -n sim_env -c conda-forge \
        python=3.10 pip bison flex make gcc gxx cmake lld git perl
fi

echo "3. Setting up EdgeSimPy Python environment (edgesimpy_env)..."
# EdgeSimPy specifically requires Python < 3.12 due to NetworkX/MsgPack dependencies
if [ ! -d "$MAMBA_ROOT/envs/edgesimpy_env" ]; then
    $MAMBA_BIN create -y -n edgesimpy_env -c conda-forge python=3.10 pip
    # Install EdgeSimPy via Git because it is not listed on PyPI as EdgeSimPy correctly
    $MAMBA_ROOT/envs/edgesimpy_env/bin/pip install git+https://github.com/EdgeSimPy/EdgeSimPy.git
fi

echo "4. Downloading OMNeT++ and INET versions..."
cd third_party

# OMNeT++ 6.0.3 (Required by Simu5G)
if [ ! -d "omnetpp-6.0.3" ]; then
    echo "Downloading OMNeT++ 6.0.3..."
    wget -c https://github.com/omnetpp/omnetpp/releases/download/omnetpp-6.0.3/omnetpp-6.0.3-linux-x86_64.tgz
    tar -xzf omnetpp-6.0.3-linux-x86_64.tgz
fi

# OMNeT++ 5.6.2 (Legacy support for EdgeCloudSim/FogNetSim++)
if [ ! -d "omnetpp-5.6.2" ]; then
    echo "Downloading OMNeT++ 5.6.2..."
    wget -c https://github.com/omnetpp/omnetpp/releases/download/omnetpp-5.6.2/omnetpp-5.6.2-src-linux.tgz
    tar -xzf omnetpp-5.6.2-src-linux.tgz
fi

# INET 4.5.0 (Required by Simu5G)
if [ ! -d "inet45_603" ]; then
    echo "Downloading INET 4.5.0..."
    wget -c https://github.com/inet-framework/inet/releases/download/v4.5.0/inet-4.5.0-src.tgz
    tar -xzf inet-4.5.0-src.tgz
    mv inet4.5.0 inet45_603
fi

echo "5. Native Frameworks (Already Integrated)..."
# Simu5G and EdgeCloudSim are checked into this repository to preserve our custom native patches.

echo "=============================================================================="
echo "Dependencies staged successfully!"
echo "Please refer to install.md for the step-by-side compilation instructions."
echo "=============================================================================="
urbis
