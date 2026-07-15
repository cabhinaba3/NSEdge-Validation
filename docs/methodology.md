# Cross-Simulator Benchmark — Methodology

This document specifies exactly how the NSEdge cross-simulator benchmark is measured, so that
the results in `results/` and the paper are auditable and reproducible. It replaces an earlier
document that overstated the integrations.

## 1. Workload: DipDCE edge offload

The common workload is the **DipDCE** image-offload architecture: sensors emit object-detection
inference frames that are offloaded to edge servers for DNN inference and a small result is
returned. All parameters live in `configs/dipdce_benchmark.json` (the single source of truth
every runner reads):

| Parameter | Value | Meaning |
|---|---|---|
| `frame_bytes` | 180 000 | one inference frame (≈180 KB image) |
| `per_worker_fps` | 5 | frames/s offered to each edge worker |
| `operating_point.edge_workers` | 4 | reference topology (→ 20 fps aggregate) |
| `sim_duration_s` | 30 | simulated wall-time per run |
| `sla_ms` | 250 | per-frame deadline |
| `edge_link` | 1 Gbps, 0.39 ms | device→edge link budget |
| `scalability_sweep` | 1,2,4,8,16,32,64 | edge workers for the scale-out curve |
| `loss_test.loss_rate` | 0.03 | device→edge packet loss for the impairment test |

**Operating point rationale.** With the measured Intel-i5 profile a 180 KB frame takes 132 ms,
capping throughput at ≈5 fps/worker; the 4-worker / 20 fps point matches the regime the physical
testbed was validated in, so it has ground truth (RTT 143.6 ms, SLA 67.2 % under 3 % loss).

## 2. Compute injection (disclosed)

None of the four simulators models DNN inference natively — they are *network* simulators. To
keep the comparison about the thing they actually differ on (the network path), the measured
compute time (`profiles_validation.json`: 180 KB → **132.44 ± 0.53 ms**) is **injected
identically** into every engine. Consequently:

- **NSEdge** samples this time from its native profiling sampler and additionally models the
  full TCP/IP transport, so its per-frame delay = queue + compute + packet transport.
- **EdgeSimPy / Simu5G** contribute their *native* network transport delay; the same 132.44 ms
  compute is added on top.
- **EdgeCloudSim** is reported on its *own* end-to-end service model (its native CloudSim
  compute + WLAN/WAN), i.e. a different compute basis — flagged in every table.

Because compute is identical (or disclosed), the spread between engines reflects their **network
model**, not their compute model.

## 3. Per-engine integration

| Engine | Network model (native) | Loss? | Runner |
|---|---|:--:|---|
| **NSEdge** | ns-3 packet-level TCP/IP over PointToPoint (Ethernet) or `YansWifi` (802.11) | ✅ `RateErrorModel` | `measure_nsedge.py`, `measure_nsedge_wifi.py` |
| **EdgeSimPy** | flow-level: real `NetworkFlow` + `max_min_fairness` over a `Topology`; per-frame transfer time from the engine, propagation from `calculate_path_delay` | ❌ no packet concept | `measure_edgesimpy.py` |
| **EdgeCloudSim** | CloudSim WLAN + WAN service model (`sample_app1`) | ❌ | `measure_edgecloudsim.sh` |
| **Simu5G** | packet-level 5G-NR standalone (`DipDCE-UL`, 180 KB TCP uplink over NR-Uu) | ✅ (`targetBler`) | `measure_simu5g.sh` |

Each runner emits `results/<engine>_measured.json`; `plot_benchmark.py` consolidates them into
`results/benchmark_metrics.json` and renders the four figures + `benchmark_table.tex`.

The EdgeSimPy runner drives EdgeSimPy's *genuine* transport engine (it does **not** hand-roll a
queue): it builds a `Topology` of source + edge nodes joined by real `NetworkLink`s, issues one
`NetworkFlow` per frame, and reads completion times from `NetworkFlow.step()`. Empty ticks are
fast-forwarded (a legitimate optimisation), which is why it is orders of magnitude faster than a
naïve per-microsecond loop.

## 4. Metrics

1. **Speed / real-time factor** — engine wall-clock to simulate the fixed scenario (NSEdge and
   EdgeCloudSim/Simu5G via `/usr/bin/time`; EdgeSimPy via an internal timer around the transport
   loop, excluding Python import). RTF = simulated seconds ÷ wall seconds.
2. **Scalability** — wall-clock vs. number of edge workers (log–log), 1 run per point.
3. **Delay accuracy** — mean per-frame delay vs. the physical 143.6 ms baseline; compared only
   for NSEdge and EdgeSimPy (shared wired access + identical compute). Simu5G/EdgeCloudSim are
   tabulated with their basis, not forced onto the same axis.
4. **Packet-loss degradation** — SLA reliability without loss and under 3 % device→edge loss.
   Packet-level engines reproduce the physical collapse; flow-level engines cannot.

## 5. Threats to validity

- Physical baseline is loopback + `tc netem`, not a hardware cluster (a stated paper limitation).
- No engine models GPU inference → compute is injected (CPU profile); GPU is future work.
- Engines model different access technologies (Ethernet p2p, 5G-NR, abstract flow); **speed** is
  the clean apples-to-apples axis, **fidelity** is framed as distance-from-physical plus the
  structural loss-reproduction capability, not a fragile absolute-delay match across PHYs.
- NSEdge's compute sampler is fixed-seed; run-to-run variance comes from the network model and
  (under loss) the `RateErrorModel` RNG stream (`--RngRun`).
- Absolute delay depends on the arrival process; NSEdge's operating point includes edge
  queueing (~29 ms) absent from the deterministic EdgeSimPy driver — see the README TODO on
  matching arrival processes.

## 6. Reproducing

```bash
PY=third_party/micromamba_root/envs/sim_env/bin/python
$PY  benchmark/measure_nsedge.py
third_party/micromamba_root/envs/edgesimpy_env/bin/python benchmark/measure_edgesimpy.py
bash benchmark/measure_edgecloudsim.sh 3
bash benchmark/measure_simu5g.sh 10
$PY  benchmark/plot_benchmark.py
```

Speed numbers should reproduce within ±10 % across runs; the loss run must show NSEdge < 100 %
completion while EdgeSimPy/EdgeCloudSim remain at 100 %. Spot-check one engine's raw native
output (e.g. Simu5G's `results/DipDCE-UL/0.sca` `endToEndDelay:histogram`) against the parsed
value in the JSON.
