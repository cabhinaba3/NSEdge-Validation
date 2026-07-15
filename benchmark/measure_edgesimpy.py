#!/usr/bin/env python3
"""
dipdce_edgesimpy_honest.py — HONEST EdgeSimPy measurement for the cross-simulator benchmark.

This REPLACES the fabricated src/simulators/edgesimpy/dipdce_edgesimpy_native.py, which ran
10 empty EdgeSimPy ticks and then computed delay with a hand-rolled queue + hardcoded
constants (cloud_delay = 0.110 + 0.152) entirely OUTSIDE EdgeSimPy.

What this does instead
----------------------
It drives EdgeSimPy's GENUINE network-transport engine to carry every DipDCE offload frame:
  * a real `Topology` (networkx graph) of a source node + N edge nodes joined by real
    `NetworkLink`s (bandwidth + propagation delay),
  * one real `NetworkFlow` per 180 KB frame (source -> edge),
  * EdgeSimPy's real `max_min_fairness` bandwidth-sharing scheduler run every tick,
  * EdgeSimPy's real `NetworkFlow.step()` transfer dynamics and `Topology.calculate_path_delay`.
The per-frame NETWORK delay therefore comes entirely from EdgeSimPy's own code.

What is injected (identically across ALL four engines, disclosed)
----------------------------------------------------------------
No network simulator here models DNN inference. The measured Intel-i5 compute time
(180 KB -> 132.44 +/- 0.53 ms, from configs/profiles_validation.json) is injected via a
simple per-edge single-server FIFO (captures compute queueing when load is high; zero wait
when the deterministic arrival rate stays below service rate). This is the SAME compute model
applied to every non-native engine, so the NETWORK path is the object of comparison.

Honest limitation surfaced by design
-------------------------------------
EdgeSimPy is FLOW-LEVEL: it has no packet, no loss, no retransmission. Under the "loss"
scenario it transports frames identically to baseline (delay unchanged, SLA ~100%). We report
that as-is: it is exactly the structural gap that motivates NSEdge's packet-level fidelity.

Speed metric: engine wall-clock is timed INTERNALLY (time.perf_counter around the transport
loop) so Python import/startup is excluded — the fair apples-to-apples cost of the simulation
engine itself. Peak RSS via resource.getrusage.
"""
import json, os, sys, time, random, resource, argparse

# EdgeSimPy genuine components
from edge_sim_py.components.topology import Topology
from edge_sim_py.components.network_link import NetworkLink
from edge_sim_py.components.network_flow import NetworkFlow
from edge_sim_py.components.flow_scheduling.max_min_fairness import max_min_fairness

BASE = "/proj/oasees-PG0/NS3-Edge/NSEdge-Validation"
CFG  = json.load(open(os.path.join(BASE, "configs/dipdce_benchmark.json")))
PROF = json.load(open(os.path.join(BASE, "configs/profiles_validation.json")))

W        = CFG["workload"]
NET      = CFG["network"]
OP       = CFG["operating_point"]
DUR_S    = W["sim_duration_s"]
FRAME    = W["frame_bytes"]
FPS      = W["per_worker_fps"]
SLA_MS   = W["sla_ms"]
SEEDS    = CFG["measurement"]["seeds"]

# Compute profile row matching the frame size (injected identically across engines)
_row = next(w for w in PROF["hardware_profiles"][0]["workloads"] if w["input_bytes"] == FRAME)
COMPUTE_MEAN = _row["execution_time_ms"]["mean"]      # 132.44
COMPUTE_STD  = _row["execution_time_ms"]["stddev"]    # 0.53

# Network parameters -> EdgeSimPy tick units. Tick = 1 ms.
def bw_bytes_per_ms(bw_str):
    s = bw_str.strip().lower()
    mult = 1
    if s.endswith("gbps"): mult, s = 10**9, s[:-4]
    elif s.endswith("mbps"): mult, s = 10**6, s[:-4]
    elif s.endswith("bps"): mult, s = 1, s[:-3]
    bits_per_s = float(s) * mult
    return (bits_per_s / 8.0) / 1000.0                # bytes per millisecond-tick
BW_PER_TICK = bw_bytes_per_ms(NET["edge_link_bandwidth"])   # 125000 for 1Gbps
PROP_MS     = NET["edge_link_base_latency_ms"]              # 0.39 (float; used by path-delay)


def build_topology(workers):
    """Fresh EdgeSimPy topology: 'src' node joined to each edge node by a real NetworkLink."""
    # Reset EdgeSimPy global component registries between scenarios.
    NetworkFlow._instances = []; NetworkFlow._object_count = 0
    NetworkLink._instances = []; NetworkLink._object_count = 0
    Topology._instances = [];    Topology._object_count = 0

    topo = Topology()
    edges = [f"edge{i}" for i in range(workers)]
    topo.add_node("src")
    for e in edges:
        link = NetworkLink()
        link["bandwidth"] = BW_PER_TICK
        link["delay"]     = PROP_MS
        link["nodes"]     = ["src", e]
        topo.add_node(e)
        topo.add_edge("src", e)
        topo._adj["src"][e] = link      # the NetworkLink IS the edge attribute dict
        topo._adj[e]["src"] = link
    return topo, edges


class _Model:
    """Minimal model shim: NetworkFlow.step() needs .model.schedule.steps and .model.topology."""
    def __init__(self, topo):
        self.topology = topo
        class _S: steps = 0
        self.schedule = _S()


def run_scenario(workers, loss, seed):
    """One measured EdgeSimPy run. Returns a normalized record."""
    lam = FPS * workers                          # aggregate frames/sec
    n_frames = int(round(lam * DUR_S))
    rng = random.Random(seed)

    topo, edges = build_topology(workers)
    model = _Model(topo)

    # Deterministic periodic arrivals (matches NSEdge's periodic generator), round-robin.
    inter_ms = 1000.0 / lam
    pending = []                                 # (arrival_tick, frame_id, edge_name, arrival_ms)
    for i in range(n_frames):
        arr_ms = i * inter_ms
        pending.append((int(round(arr_ms)), i, edges[i % workers], arr_ms))
    pending.sort()

    # ---- timed region: EdgeSimPy native transport of every frame ----------------------
    t0 = time.perf_counter()
    active = []
    end_tick = {}                                # frame_id -> flow end tick
    pi = 0
    model.schedule.steps = 0
    while pi < len(pending) or active:
        # Skip empty gaps: jump clock straight to next arrival when nothing is in flight.
        if not active and pi < len(pending) and pending[pi][0] > model.schedule.steps:
            model.schedule.steps = pending[pi][0]
        tick = model.schedule.steps
        while pi < len(pending) and pending[pi][0] <= tick:
            at, fid, e, arr_ms = pending[pi]; pi += 1
            flow = NetworkFlow(topology=topo, source="src", target=e, start=tick,
                               path=["src", e], data_to_transfer=FRAME,
                               metadata={"type": "dipdce_frame", "fid": fid})
            flow.model = model
            active.append(flow)
        # EdgeSimPy native bandwidth sharing + transfer step
        max_min_fairness(topology=topo, flows=active)
        for f in active:
            f.step()
        still = []
        for f in active:
            if f.status == "finished":
                end_tick[f.metadata["fid"]] = f.end
            else:
                still.append(f)
        active = still
        model.schedule.steps += 1

    # ---- assemble per-frame end-to-end delay ------------------------------------------
    # network = EdgeSimPy path propagation (up+down) + EdgeSimPy flow transfer time;
    # compute = injected per-edge FIFO with measured service time (identical across engines).
    prop_ms = topo.calculate_path_delay(["src", edges[0]])   # native EdgeSimPy propagation
    edge_free = {e: 0.0 for e in edges}
    delays, met = [], 0
    for (at, fid, e, arr_ms) in pending:
        transfer_ms = (end_tick[fid] - at)                    # native EdgeSimPy transfer (ticks=ms)
        up_done = arr_ms + prop_ms + transfer_ms
        service = max(0.0, rng.gauss(COMPUTE_MEAN, COMPUTE_STD))
        comp_start = max(up_done, edge_free[e])               # FIFO compute queue
        comp_end = comp_start + service
        edge_free[e] = comp_end
        delay = (comp_end + prop_ms) - arr_ms                 # + return propagation
        delays.append(delay)
        met += 1 if delay <= SLA_MS else 0
    sim_wall = time.perf_counter() - t0
    n = len(delays)
    return {
        "engine": "EdgeSimPy", "workers": workers, "loss": loss, "seed": seed,
        "sim_duration_s": DUR_S, "sim_wall_s": sim_wall,
        "rtf": (DUR_S / sim_wall) if sim_wall > 0 else None,
        "rss_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "n_tasks": n,
        "mean_delay_ms": sum(delays) / n if n else None,
        "p95_delay_ms": sorted(delays)[int(0.95 * n)] if n else None,
        "sla_pct": 100.0 * met / n if n else None,
        "loss_modeled": False,     # EdgeSimPy is flow-level: no packet loss concept
    }


def fmt(v, d=2):
    return f"{v:.{d}f}" if v is not None else "NA"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="1 seed, operating point + loss only")
    args = ap.parse_args()
    records = []

    print("== baseline ==", flush=True)
    for s in range(1, (2 if args.quick else SEEDS) + 1):
        r = run_scenario(OP["edge_workers"], 0.0, s); r["scenario"] = "baseline"; records.append(r)
        print(f"  seed {s}: sim_wall={fmt(r['sim_wall_s'],4)}s rtf={fmt(r['rtf'],1)} "
              f"delay={fmt(r['mean_delay_ms'],1)}ms sla={fmt(r['sla_pct'],1)}% n={r['n_tasks']}", flush=True)

    print("== loss 3% (EdgeSimPy has NO loss model -> expect unchanged) ==", flush=True)
    for s in range(1, (2 if args.quick else SEEDS) + 1):
        r = run_scenario(OP["edge_workers"], CFG["loss_test"]["loss_rate"], s)
        r["scenario"] = "loss"; records.append(r)
        print(f"  seed {s}: delay={fmt(r['mean_delay_ms'],1)}ms sla={fmt(r['sla_pct'],1)}% "
              f"(loss_modeled={r['loss_modeled']})", flush=True)

    if not args.quick:
        print("== scalability ==", flush=True)
        for w in CFG["scalability_sweep"]["edge_workers"]:
            r = run_scenario(w, 0.0, 1); r["scenario"] = "scalability"; records.append(r)
            print(f"  workers={w}: sim_wall={fmt(r['sim_wall_s'],4)}s rtf={fmt(r['rtf'],1)} "
                  f"delay={fmt(r['mean_delay_ms'],1)}ms n={r['n_tasks']}", flush=True)

    out = os.path.join(BASE, "results/edgesimpy_measured.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(records, open(out, "w"), indent=2)
    print("WROTE", out, flush=True)


if __name__ == "__main__":
    main()
