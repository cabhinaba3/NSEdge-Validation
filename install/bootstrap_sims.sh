#!/bin/bash
# =============================================================================
# bootstrap_sims.sh
# Re-stage + build the third-party simulator toolchains deleted from disk, for
# the honest NSEdge cross-simulator benchmark:
#   - micromamba sim_env  (OMNeT++ build deps + IDE python modules + JDK)
#   - edgesimpy_env       (EdgeSimPy via pip)
#   - OMNeT++ 6.0.3       (make base; no IDE/Qtenv)
#   - INET 4.5.0          (inet45_603)
#   - Simu5G              (against omnetpp-6.0.3 + inet45_603)
# Skips OMNeT++ 5.6.2 (only needed for the excluded FogNetSim++).
# Does NOT use `set -e`; records per-stage exit codes to rebuild_status.txt.
# =============================================================================

BASE=/proj/oasees-PG0/NS3-Edge/NSEdge-Validation
TP=$BASE/third_party
MAMBA_ROOT=$TP/micromamba_root
MAMBA_BIN=$TP/micromamba/bin/micromamba
export MAMBA_ROOT_PREFIX=$MAMBA_ROOT
STATUS=$TP/rebuild_status.txt
: > "$STATUS"
NPROC=$(nproc)

log()  { echo ""; echo "===== STAGE: $1 ====="; echo "$(date '+%H:%M:%S') START $1" >> "$STATUS"; }
end()  { echo "$(date '+%H:%M:%S') END   $2 rc=$1" >> "$STATUS"; echo ">>> $2 rc=$1"; }

cd "$TP" || exit 99

# ---------------------------------------------------------------------------
log "micromamba-init"
if [ ! -f "$MAMBA_BIN" ]; then
  mkdir -p "$TP/micromamba"
  curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj -C "$TP/micromamba" bin/micromamba
fi
end $? micromamba-init

# ---------------------------------------------------------------------------
log "sim_env"
if [ ! -d "$MAMBA_ROOT/envs/sim_env" ]; then
  "$MAMBA_BIN" create -y -n sim_env -c conda-forge \
      python=3.10 pip bison flex make cmake lld git perl \
      gcc gxx \
      numpy scipy pandas matplotlib \
      openjdk=17
  "$MAMBA_ROOT/envs/sim_env/bin/pip" install posix_ipc
fi
end $? sim_env

# ---------------------------------------------------------------------------
log "edgesimpy_env"
if [ ! -d "$MAMBA_ROOT/envs/edgesimpy_env" ]; then
  "$MAMBA_BIN" create -y -n edgesimpy_env -c conda-forge python=3.10 pip
  "$MAMBA_ROOT/envs/edgesimpy_env/bin/pip" install "git+https://github.com/EdgeSimPy/EdgeSimPy.git"
fi
end $? edgesimpy_env

export PATH=$MAMBA_ROOT/envs/sim_env/bin:$PATH

# ---------------------------------------------------------------------------
log "download-omnetpp6"
if [ ! -d "omnetpp-6.0.3" ]; then
  wget -q -c https://github.com/omnetpp/omnetpp/releases/download/omnetpp-6.0.3/omnetpp-6.0.3-linux-x86_64.tgz
  tar -xzf omnetpp-6.0.3-linux-x86_64.tgz
fi
end $? download-omnetpp6

# ---------------------------------------------------------------------------
log "download-inet45"
if [ ! -d "inet45_603" ]; then
  if [ ! -f "inet-4.5.0-src.tgz" ]; then
    wget -q -c https://github.com/inet-framework/inet/releases/download/v4.5.0/inet-4.5.0-src.tgz
  fi
  [ ! -d "inet4.5" ] && [ ! -d "inet4.5.0" ] && tar -xzf inet-4.5.0-src.tgz
  mv inet4.5 inet45_603 2>/dev/null || mv inet4.5.0 inet45_603 2>/dev/null || mv inet-4.5.0 inet45_603 2>/dev/null
fi
end $? download-inet45

# ---------------------------------------------------------------------------
log "build-omnetpp6"
cd "$TP/omnetpp-6.0.3" || exit 98
source setenv -f
./configure WITH_QTENV=no WITH_OSG=no WITH_OSGEARTH=no
make base -j"$NPROC"
end $? build-omnetpp6
export PATH=$TP/omnetpp-6.0.3/bin:$PATH

# ---------------------------------------------------------------------------
log "build-inet45"
cd "$TP/inet45_603" || exit 97
source setenv 2>/dev/null
make makefiles
make -j"$NPROC"
end $? build-inet45

# ---------------------------------------------------------------------------
log "build-simu5g"
cd "$TP/Simu5G" || exit 96
source "$TP/inet45_603/setenv" 2>/dev/null
make makefiles
make -j"$NPROC"
end $? build-simu5g

echo ""; echo "===== REBUILD COMPLETE ====="
cat "$STATUS"
