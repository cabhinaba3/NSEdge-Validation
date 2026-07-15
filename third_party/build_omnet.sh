#!/bin/bash
set -e

# Setup environment
export MAMBA_ROOT_PREFIX=/proj/oasees-PG0/NS3-Edge/validation_experiment/third_party/micromamba_root
eval "$(/proj/oasees-PG0/NS3-Edge/validation_experiment/third_party/micromamba/micromamba shell hook -s bash)"
micromamba activate sim_env

cd /proj/oasees-PG0/NS3-Edge/validation_experiment/third_party

# OMNeT++ 5.6.2
if [ ! -f "omnetpp-5.6.2/bin/opp_run" ]; then
    if [ ! -d "omnetpp-5.6.2" ]; then
        wget -q https://github.com/omnetpp/omnetpp/releases/download/omnetpp-5.6.2/omnetpp-5.6.2-src-linux.tgz
        tar -xzf omnetpp-5.6.2-src-linux.tgz
        rm omnetpp-5.6.2-src-linux.tgz
    fi
    cd omnetpp-5.6.2
    
    cp configure.user configure.user.orig || true
    sed -i 's/^WITH_QTENV=yes/WITH_QTENV=no/' configure.user
    sed -i 's/^WITH_TKENV=yes/WITH_TKENV=no/' configure.user
    sed -i 's/^WITH_OSG=yes/WITH_OSG=no/' configure.user
    sed -i 's/^WITH_OSGEARTH=yes/WITH_OSGEARTH=no/' configure.user
    
    source setenv -f
    ./configure
    make -j$(nproc)
    cd ..
fi

# OMNeT++ 6.0.3
if [ ! -f "omnetpp-6.0.3/bin/opp_run" ]; then
    if [ ! -d "omnetpp-6.0.3" ]; then
        wget -q https://github.com/omnetpp/omnetpp/releases/download/omnetpp-6.0.3/omnetpp-6.0.3-linux-x86_64.tgz
        tar -xzf omnetpp-6.0.3-linux-x86_64.tgz
        rm omnetpp-6.0.3-linux-x86_64.tgz
    fi
    cd omnetpp-6.0.3
    
    cp configure.user configure.user.orig || true
    sed -i 's/^WITH_QTENV=yes/WITH_QTENV=no/' configure.user
    sed -i 's/^WITH_OSG=yes/WITH_OSG=no/' configure.user
    sed -i 's/^WITH_OSGEARTH=yes/WITH_OSGEARTH=no/' configure.user
    
    source setenv -f
    ./configure
    make -j$(nproc)
    cd ..
fi
