#!/usr/bin/env python3
"""
measure_nsedge.py — honest NSEdge measurement pass for the cross-simulator benchmark.

Runs the built `dipdce-benchmark` ns-3 scenario directly (no ./ns3 wrapper, so wall
clock reflects simulation cost only), under /usr/bin/time -v for wall-clock + peak RSS.
Parses the emitted tasks.csv for per-frame delay + SLA reliability. Emits one JSON
record per (scenario, run) to results/nsedge_measured.json.

Scenarios (all read the shared operating point in configs/dipdce_benchmark.json):
  - baseline   : 4 edges, 5 Hz/edge, no loss           (N seeds)
  - loss       : 4 edges, 5 Hz/edge, 3% device->edge loss (N seeds)
  - scalability: workers in the sweep, 5 Hz/edge, no loss (1 run each)

Nothing here is hardcoded from a prior result: every number comes from the run it labels.
"""
import csv, json, os, re, subprocess, sys, statistics

BASE   = "/proj/oasees-PG0/NS3-Edge/NSEdge-Validation"
NS3    = "/proj/oasees-PG0/NS3-Edge/ns-3"
BIN    = os.path.join(NS3, "build/scratch/ns3.43-dipdce-benchmark-default")
CFG    = json.load(open(os.path.join(BASE, "configs/dipdce_benchmark.json")))
OUTJSON= os.path.join(BASE, "results/nsedge_measured.json")

W      = CFG["workload"]
NET    = CFG["network"]
OP     = CFG["operating_point"]
DUR    = W["sim_duration_s"]
FRAME  = W["frame_bytes"]
FPS    = W["per_worker_fps"]
SLA    = W["sla_ms"]
BW     = NET["edge_link_bandwidth"]
LAT    = NET["edge_link_base_latency_ms"]
SEEDS  = CFG["measurement"]["seeds"]

env = dict(os.environ)
env["LD_LIBRARY_PATH"] = os.path.join(NS3, "build/lib") + ":" + env.get("LD_LIBRARY_PATH", "")

def run_one(workers, loss, rng, outdir):
    """One timed run. Returns dict with wall_s, rss_kb, and fidelity stats."""
    lam = FPS * workers
    full = os.path.join(NS3, outdir)
    # Pre-create the (possibly nested) outdir: the C++ scenario uses a single-level
    # mkdir and cannot create nested paths, so the CSV would silently not be written.
    os.makedirs(full, exist_ok=True)
    for f in os.listdir(full):
        fp = os.path.join(full, f)
        if os.path.isfile(fp):
            os.remove(fp)
    cmd = ["/usr/bin/time", "-v", BIN,
           f"--duration={DUR}", f"--lambda={lam}", f"--workload_size={FRAME}",
           f"--num_nodes={workers}", f"--bandwidth={BW}", f"--latency_ms={LAT}",
           f"--sla_ms={SLA}", f"--loss={loss}", f"--outdir={outdir}",
           f"--RngRun={rng}", "--tech=WIFI_80211AC"]
    p = subprocess.run(cmd, cwd=NS3, env=env, capture_output=True, text=True)
    err = p.stderr
    wall = None
    m = re.search(r"Elapsed .*: ([0-9:.]+)", err)
    if m:
        t = m.group(1)
        parts = [float(x) for x in t.split(":")]
        wall = parts[0]*60 + parts[1] if len(parts) == 2 else parts[0]*3600 + parts[1]*60 + parts[2]
    rss = None
    m = re.search(r"Maximum resident set size \(kbytes\): (\d+)", err)
    if m:
        rss = int(m.group(1))
    # fidelity
    csvpath = os.path.join(full, "tasks.csv")
    delays, met = [], 0
    n = 0
    if os.path.exists(csvpath):
        for row in csv.DictReader(open(csvpath)):
            delays.append(float(row["response_time_ms"]))
            met += 1 if row["met_sla"] in ("1", "true", "True") else 0
            n += 1
    rec = {
        "engine": "NSEdge", "workers": workers, "loss": loss, "rng": rng,
        "sim_duration_s": DUR, "wall_s": wall, "rss_kb": rss,
        "rtf": (DUR / wall) if wall else None,
        "n_tasks": n,
        "mean_delay_ms": statistics.mean(delays) if delays else None,
        "p95_delay_ms": (sorted(delays)[int(0.95*len(delays))] if delays else None),
        "sla_pct": (100.0 * met / n) if n else None,
    }
    return rec

def fmt(v, d=2):
    return f"{v:.{d}f}" if v is not None else "NA"

def main():
    records = []
    # baseline (N seeds)
    print("== baseline ==", flush=True)
    for s in range(1, SEEDS+1):
        r = run_one(OP["edge_workers"], 0.0, s, "results-bench/baseline")
        r["scenario"] = "baseline"; records.append(r)
        print(f"  seed {s}: wall={fmt(r['wall_s'])}s rtf={fmt(r['rtf'])} delay={fmt(r['mean_delay_ms'],1)}ms sla={fmt(r['sla_pct'],1)}% n={r['n_tasks']}", flush=True)
    # loss (N seeds)
    print("== loss 3% ==", flush=True)
    for s in range(1, SEEDS+1):
        r = run_one(OP["edge_workers"], CFG["loss_test"]["loss_rate"], s, "results-bench/loss")
        r["scenario"] = "loss"; records.append(r)
        print(f"  seed {s}: wall={fmt(r['wall_s'])}s delay={fmt(r['mean_delay_ms'],1)}ms sla={fmt(r['sla_pct'],1)}% n={r['n_tasks']}", flush=True)
    # scalability (1 run each)
    print("== scalability ==", flush=True)
    for w in CFG["scalability_sweep"]["edge_workers"]:
        r = run_one(w, 0.0, 1, f"results-bench/scale_{w}")
        r["scenario"] = "scalability"; records.append(r)
        print(f"  workers={w}: wall={fmt(r['wall_s'])}s rtf={fmt(r['rtf'])} delay={fmt(r['mean_delay_ms'],1)}ms n={r['n_tasks']}", flush=True)

    os.makedirs(os.path.dirname(OUTJSON), exist_ok=True)
    json.dump(records, open(OUTJSON, "w"), indent=2)
    print("WROTE", OUTJSON, flush=True)

    # summary
    base = [r for r in records if r["scenario"]=="baseline"]
    loss = [r for r in records if r["scenario"]=="loss"]
    print("\n=== NSEdge SUMMARY ===")
    print(f"baseline wall {statistics.mean([r['wall_s'] for r in base]):.2f}±{statistics.pstdev([r['wall_s'] for r in base]):.2f}s "
          f"rtf {statistics.mean([r['rtf'] for r in base]):.2f} "
          f"delay {statistics.mean([r['mean_delay_ms'] for r in base]):.1f}ms "
          f"sla {statistics.mean([r['sla_pct'] for r in base]):.1f}%")
    print(f"loss     delay {statistics.mean([r['mean_delay_ms'] for r in loss]):.1f}ms "
          f"sla {statistics.mean([r['sla_pct'] for r in loss]):.1f}%")

if __name__ == "__main__":
    main()
