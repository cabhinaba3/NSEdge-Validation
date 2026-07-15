#!/bin/bash
# Honest EdgeCloudSim measurement -> results/ecs_measured.json
# Runs the compiled CloudSim/EdgeCloudSim sample_app1 (real WLAN+WAN model) N times (it is
# stochastic) under /usr/bin/time, and averages its NATIVE "average service time", the CloudSim
# engine time ("It took N ms"), wall-clock, and peak RSS.
BASE=/proj/oasees-PG0/NS3-Edge/NSEdge-Validation
export PATH=$BASE/third_party/micromamba_root/envs/sim_env/bin:$PATH   # JDK 17
cd $BASE/third_party/EdgeCloudSim/scripts/sample_app1 || exit 9

SIMMIN=$(grep -E "^simulation_time=" config/default_config.properties | cut -d= -f2)
SIM_S=$(awk "BEGIN{print $SIMMIN*60}")
N=${1:-3}
TMP=$(mktemp)
for i in $(seq 1 $N); do
  /usr/bin/time -v java -classpath "../../bin:../../lib/cloudsim-4.0.jar:../../lib/commons-math3-3.6.1.jar:../../lib/colt.jar" \
      edu.boun.edgecloudsim.applications.sample_app1.MainApp \
      config/default_config.properties config/edge_devices.xml config/applications.xml output_test 1 2>&1 \
   | grep -E "average service time:|It took|Elapsed \(wall|Maximum resident" >> "$TMP"
done

python3 - "$TMP" "$SIM_S" "$N" <<'PY'
import sys, re, json, statistics as st
lines=open(sys.argv[1]).read().splitlines(); sim_s=float(sys.argv[2]); N=int(sys.argv[3])
svc,edge,eng,wall,rss=[],[],[],[],[]
for ln in lines:
    m=re.search(r"average service time: ([\d.]+) seconds\. \(on Edge: ([\d.]+)", ln)
    if m: svc.append(float(m.group(1))*1000); edge.append(float(m.group(2))*1000)
    m=re.search(r"It took (\d+) Milli", ln)
    if m: eng.append(int(m.group(1))/1000.0)
    m=re.search(r"Elapsed .*: ([0-9:.]+)", ln)
    if m:
        p=[float(a) for a in m.group(1).split(":")]; wall.append(p[0]*60+p[1] if len(p)==2 else p[0]*3600+p[1]*60+p[2])
    m=re.search(r"Maximum resident set size \(kbytes\): (\d+)", ln)
    if m: rss.append(int(m.group(1)))
def mean(x): return round(st.mean(x),1) if x else None
eng_s=st.mean(eng) if eng else None
rec={"engine":"EdgeCloudSim","runs":N,
     "service_time_ms": mean(svc), "service_time_std_ms": round(st.pstdev(svc),1) if len(svc)>1 else 0.0,
     "edge_time_ms": mean(edge),
     "engine_wall_s": round(eng_s,3) if eng_s else None,
     "wall_s": mean(wall)/1000 if False else (round(st.mean(wall),3) if wall else None),
     "sim_time_s": sim_s,
     "rtf": round(sim_s/eng_s,1) if eng_s else None,
     "rss_kb": int(st.mean(rss)) if rss else None,
     "config":"sample_app1 default (WLAN+WAN); native CloudSim service+compute model",
     "note":"delay is native end-to-end service time (own compute model, not the injected 132 ms profile); stochastic, averaged over %d runs"%N}
json.dump(rec, open("/proj/oasees-PG0/NS3-Edge/NSEdge-Validation/results/ecs_measured.json","w"), indent=2)
print("ECS:", json.dumps(rec))
PY
rm -f "$TMP"
