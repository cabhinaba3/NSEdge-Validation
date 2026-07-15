#!/bin/bash
# Honest Simu5G measurement -> results/simu5g_measured.json
# Runs the DipDCE-UL 5G-NR standalone config (180 KB TCP uplink offload) and parses the
# NATIVE per-packet endToEndDelay histogram + engine event-processing rate + peak RSS.
# $1 = sim-time-limit seconds (default 10, the natural DipDCE workload length).
TP=/proj/oasees-PG0/NS3-Edge/NSEdge-Validation/third_party
export MAMBA_ROOT_PREFIX=$TP/micromamba_root
export PATH=$MAMBA_ROOT_PREFIX/envs/sim_env/bin:$TP/omnetpp-6.0.3/bin:$PATH
source $TP/omnetpp-6.0.3/setenv -f >/dev/null 2>&1
source $TP/inet45_603/setenv       >/dev/null 2>&1
export LD_LIBRARY_PATH=$TP/inet45_603/src:$TP/Simu5G/src:$LD_LIBRARY_PATH
cd $TP/Simu5G/simulations/nr/standalone || exit 9
SIMT=${1:-10}

OUT=$(/usr/bin/time -v opp_run -u Cmdenv -l INET -l simu5g -c DipDCE-UL --sim-time-limit=${SIMT}s \
    -n $TP/Simu5G/src:$TP/Simu5G/simulations:$TP/inet45_603/src omnetpp.ini 2>&1)
# event-processing time = the "Elapsed: <t>s" reported at 100% completed (excludes NED load)
EVT=$(echo "$OUT" | grep -oE "Elapsed: [0-9.]+s" | tail -1 | grep -oE "[0-9.]+")
WALL=$(echo "$OUT" | grep "Elapsed (wall clock)" | sed -E 's/.*: ([0-9:.]+)/\1/')
RSS=$(echo "$OUT"  | grep "Maximum resident set size" | grep -oE "[0-9]+")
EVENTS=$(echo "$OUT" | grep -oE "event #[0-9]+" | tail -1 | grep -oE "[0-9]+")

SCA=results/DipDCE-UL/0.sca
# NOTE: in the .sca the field order is count, mean, stddev -> only print once mean+stddev seen.
read DMEAN DSTD DCNT < <(awk '
  /statistic .*server.app\[0\] endToEndDelay:histogram/{f=1}
  f&&/field count/{c=$3}
  f&&/field mean/{m=$3}
  f&&/field stddev/{s=$3; print m, s, c; exit}' "$SCA")

python3 - "$SIMT" "$EVT" "$WALL" "$RSS" "$EVENTS" "$DMEAN" "$DSTD" "$DCNT" <<'PY'
import sys, json
simt,evt,wall,rss,events,dmean,dstd,dcnt = sys.argv[1:9]
def f(x):
    try: return float(x)
    except: return None
wall_s=None
if wall and ":" in wall:
    p=[float(a) for a in wall.split(":")]; wall_s=p[0]*60+p[1] if len(p)==2 else p[0]*3600+p[1]*60+p[2]
evt_s=f(evt); simt=f(simt)
rec={"engine":"Simu5G",
     "e2e_delay_ms": round(f(dmean)*1000,1) if f(dmean) else None,
     "e2e_stddev_ms": round(f(dstd)*1000,1) if f(dstd) else None,
     "packets": int(float(dcnt)) if f(dcnt) else None,
     "sim_time_s": simt, "event_proc_s": evt_s, "wall_s": wall_s,
     "events": int(events) if events else None,
     "rtf": round(simt/evt_s,2) if (evt_s and simt) else None,
     "rss_kb": int(rss) if rss else None,
     "config": "DipDCE-UL: 1 UE, 180 KB TCP uplink, 5G-NR standalone; network native, compute injected",
     "note": "delay is per-packet 5G-NR transport (different access tech than the loopback baseline)"}
json.dump(rec, open("/proj/oasees-PG0/NS3-Edge/NSEdge-Validation/results/simu5g_measured.json","w"), indent=2)
print("SIMU5G:", json.dumps(rec))
PY
