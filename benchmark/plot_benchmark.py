#!/usr/bin/env python3
"""
plot_benchmark.py — consolidate the four engines' MEASURED results and render
journal-quality figures for the NSEdge cross-simulator benchmark.

Reads (each produced by its own engine runner; nothing hardcoded here):
  results/nsedge_measured.json      (NSEdge, ns-3 packet-level)
  results/edgesimpy_measured.json   (EdgeSimPy, flow-level)
  results/ecs_measured.json         (EdgeCloudSim, CloudSim flow-level)     [optional]
  results/simu5g_measured.json      (Simu5G, 5G-NR packet-level)            [optional]

Writes:
  results/benchmark_metrics.json    (single consolidated, machine-readable summary)
  figs/fig_speed_rtf.pdf            (metric 1: real-time factor, all engines)
  figs/fig_scalability.pdf          (metric 2: wall-clock vs #edge workers)
  figs/fig_delay_accuracy.pdf       (metric 3: per-frame delay vs physical baseline)
  figs/fig_loss_degradation.pdf     (metric 4: SLA reliability, baseline vs 3% loss)
  results/benchmark_table.tex       (LaTeX summary table, all four engines + caveats)

Honesty notes baked into the figures/captions:
  * Speed / RTF is the clean apples-to-apples axis.
  * Delay accuracy is compared ONLY for the two engines on the same wired-access +
    identically-injected-compute basis (NSEdge, EdgeSimPy) against the physical baseline.
    Simu5G (5G-NR access) and EdgeCloudSim (own compute model) are reported in the table
    with explicit caveats, not forced onto the same delay axis.
  * Loss degradation is the structural differentiator: packet-level engines reproduce it,
    flow-level engines cannot.
"""
import json, os, statistics as st

BASE = "/proj/oasees-PG0/NS3-Edge/NSEdge-Validation"
RES  = os.path.join(BASE, "results")
FIGS = os.path.join(BASE, "figs")
os.makedirs(FIGS, exist_ok=True)
CFG  = json.load(open(os.path.join(BASE, "configs/dipdce_benchmark.json")))
PHYS_RTT = CFG["physical_ground_truth"]["baseline_rtt_ms"]      # 143.6
PHYS_LOSS_SLA = CFG["physical_ground_truth"]["loss_reliability_pct"]  # 67.2
DUR = CFG["workload"]["sim_duration_s"]

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams.update({
    "font.family": "serif", "font.size": 9, "axes.titlesize": 9,
    "axes.labelsize": 9, "legend.fontsize": 8, "xtick.labelsize": 8,
    "ytick.labelsize": 8, "figure.dpi": 150, "savefig.bbox": "tight",
    "axes.grid": True, "grid.alpha": 0.3, "grid.linewidth": 0.5,
})
# Wong colour-blind-safe palette
C = {"NSEdge": "#0072B2", "EdgeSimPy": "#E69F00", "EdgeCloudSim": "#009E73", "Simu5G": "#CC79A7"}

def load(name):
    p = os.path.join(RES, name)
    return json.load(open(p)) if os.path.exists(p) else None

nse = load("nsedge_measured.json")
esp = load("edgesimpy_measured.json")
ecs = load("ecs_measured.json")
s5g = load("simu5g_measured.json")

def agg(records, scenario, key):
    vals = [r[key] for r in records if r.get("scenario") == scenario and r.get(key) is not None]
    return vals

# ---- NSEdge aggregates (wall_s) ----
nse_base_wall = agg(nse, "baseline", "wall_s"); nse_base_delay = agg(nse, "baseline", "mean_delay_ms")
nse_base_sla  = agg(nse, "baseline", "sla_pct")
nse_loss_delay = agg(nse, "loss", "mean_delay_ms"); nse_loss_sla = agg(nse, "loss", "sla_pct")
nse_scale = sorted([r for r in nse if r.get("scenario")=="scalability"], key=lambda r: r["workers"])
# ---- EdgeSimPy aggregates (sim_wall_s) ----
esp_base_delay = agg(esp, "baseline", "mean_delay_ms"); esp_base_sla = agg(esp, "baseline", "sla_pct")
esp_base_wall  = agg(esp, "baseline", "sim_wall_s")
esp_loss_delay = agg(esp, "loss", "mean_delay_ms"); esp_loss_sla = agg(esp, "loss", "sla_pct")
esp_scale = sorted([r for r in esp if r.get("scenario")=="scalability"], key=lambda r: r["workers"])

def mean(x): return st.mean(x) if x else None

# =========================== consolidated metrics ==============================
M = {
    "physical_baseline": {"rtt_ms": PHYS_RTT, "loss_sla_pct": PHYS_LOSS_SLA,
                          "source": CFG["physical_ground_truth"]["source"]},
    "operating_point": CFG["operating_point"],
    "engines": {}
}
M["engines"]["NSEdge"] = {
    "type": "packet-level (ns-3, Ethernet p2p)", "models_packets": True, "models_loss": True,
    "compute": "native profiling-driven sampler",
    "rtf": round(DUR / mean(nse_base_wall), 3) if nse_base_wall else None,
    "wall_s": round(mean(nse_base_wall), 3) if nse_base_wall else None,
    "delay_ms": round(mean(nse_base_delay), 1) if nse_base_delay else None,
    "delay_err_pct": round(100*(mean(nse_base_delay)-PHYS_RTT)/PHYS_RTT, 1) if nse_base_delay else None,
    "sla_baseline_pct": round(mean(nse_base_sla), 1) if nse_base_sla else None,
    "delay_loss_ms": round(mean(nse_loss_delay), 1) if nse_loss_delay else None,
    "sla_loss_pct": round(mean(nse_loss_sla), 1) if nse_loss_sla else None,
    "rss_mb": round(mean(agg(nse,"baseline","rss_kb"))/1024, 1) if agg(nse,"baseline","rss_kb") else None,
}
M["engines"]["EdgeSimPy"] = {
    "type": "flow-level (Python, max-min fairness)", "models_packets": False, "models_loss": False,
    "compute": "injected (identical profile)",
    "rtf": round(DUR / mean(esp_base_wall), 1) if esp_base_wall else None,
    "wall_s": round(mean(esp_base_wall), 4) if esp_base_wall else None,
    "delay_ms": round(mean(esp_base_delay), 1) if esp_base_delay else None,
    "delay_err_pct": round(100*(mean(esp_base_delay)-PHYS_RTT)/PHYS_RTT, 1) if esp_base_delay else None,
    "sla_baseline_pct": round(mean(esp_base_sla), 1) if esp_base_sla else None,
    "delay_loss_ms": round(mean(esp_loss_delay), 1) if esp_loss_delay else None,
    "sla_loss_pct": round(mean(esp_loss_sla), 1) if esp_loss_sla else None,
    "rss_mb": round(mean(agg(esp,"baseline","rss_kb"))/1024, 1) if agg(esp,"baseline","rss_kb") else None,
}
if ecs:
    M["engines"]["EdgeCloudSim"] = {
        "type": "flow-level (Java/CloudSim, WLAN+WAN)", "models_packets": False, "models_loss": False,
        "compute": "native CloudSim service model (NOT the injected profile)",
        "rtf": ecs.get("rtf"), "wall_s": ecs.get("wall_s"),
        "delay_ms": ecs.get("service_time_ms"), "delay_note": "native end-to-end service time; different compute basis",
        "rss_mb": round(ecs["rss_kb"]/1024, 1) if ecs.get("rss_kb") else None,
    }
if s5g:
    M["engines"]["Simu5G"] = {
        "type": "packet-level (OMNeT++/INET, 5G-NR)", "models_packets": True, "models_loss": True,
        "compute": "injected (identical profile); network is native 5G-NR",
        "rtf": s5g.get("rtf"), "wall_s": s5g.get("wall_s"),
        "net_delay_ms": s5g.get("e2e_delay_ms"), "net_delay_stddev_ms": s5g.get("e2e_stddev_ms"),
        "delay_note": "per-packet 5G-NR transport delay; different access tech (not loopback baseline)",
        "rss_mb": round(s5g["rss_kb"]/1024, 1) if s5g.get("rss_kb") else None,
    }
json.dump(M, open(os.path.join(RES, "benchmark_metrics.json"), "w"), indent=2)

# ================================ FIGURE 1: RTF ================================
fig, ax = plt.subplots(figsize=(3.6, 2.7))
names, rtfs, cols = [], [], []
for e in ["NSEdge", "EdgeSimPy", "EdgeCloudSim", "Simu5G"]:
    v = M["engines"].get(e, {}).get("rtf")
    if v:
        names.append(e); rtfs.append(v); cols.append(C[e])
xpos = range(len(names))
bars = ax.bar(xpos, rtfs, color=cols, width=0.66, edgecolor="black", linewidth=0.4)
ax.set_yscale("log")
ax.set_ylabel("Real-time factor  (sim s / wall s)")
ax.axhline(1.0, color="grey", ls="--", lw=0.7)
ax.text(len(names)-0.5, 1.2, "real-time", fontsize=6.5, color="grey", ha="right")
for b, v in zip(bars, rtfs):
    ax.text(b.get_x()+b.get_width()/2, v*1.18, f"{v:g}", ha="center", va="bottom", fontsize=7)
ax.set_xticks(list(xpos))
ax.set_xticklabels(names, rotation=18, ha="right")
ax.set_title("Simulation speed (higher = faster)")
ax.margins(y=0.28)
fig.savefig(os.path.join(FIGS, "fig_speed_rtf.pdf"))
plt.close(fig)

# ============================ FIGURE 2: scalability ===========================
fig, ax = plt.subplots(figsize=(3.4, 2.6))
if nse_scale:
    ax.plot([r["workers"] for r in nse_scale], [r["wall_s"] for r in nse_scale],
            "o-", color=C["NSEdge"], label="NSEdge (packet-level)", ms=4, lw=1.3)
if esp_scale:
    ax.plot([r["workers"] for r in esp_scale], [r["sim_wall_s"] for r in esp_scale],
            "s-", color=C["EdgeSimPy"], label="EdgeSimPy (flow-level)", ms=4, lw=1.3)
ax.set_xscale("log", base=2); ax.set_yscale("log")
ax.set_xlabel("Number of edge workers"); ax.set_ylabel("Wall-clock time (s)")
ax.set_title(f"Scalability ({DUR}s scenario, 5 fps/worker)")
ax.legend(frameon=False, loc="upper left")
fig.savefig(os.path.join(FIGS, "fig_scalability.pdf"))
plt.close(fig)

# ========================== FIGURE 3: delay accuracy ==========================
fig, ax = plt.subplots(figsize=(3.4, 2.6))
dn = [("NSEdge", mean(nse_base_delay)), ("EdgeSimPy", mean(esp_base_delay))]
dn = [(n, v) for n, v in dn if v]
bars = ax.bar([n for n, _ in dn], [v for _, v in dn],
              color=[C[n] for n, _ in dn], width=0.5, edgecolor="black", linewidth=0.4)
ax.axhline(PHYS_RTT, color="red", ls="--", lw=1.0, label=f"Physical baseline ({PHYS_RTT} ms)")
for b, (n, v) in zip(bars, dn):
    err = 100*(v-PHYS_RTT)/PHYS_RTT
    ax.text(b.get_x()+b.get_width()/2, v+4, f"{v:.0f} ms\n({err:+.0f}%)", ha="center", va="bottom", fontsize=7)
ax.set_ylabel("Mean per-frame delay (ms)")
ax.set_title("Delay accuracy vs. physical\n(wired access, identical compute)")
ax.legend(frameon=False, loc="lower right")
ax.margins(y=0.22)
fig.savefig(os.path.join(FIGS, "fig_delay_accuracy.pdf"))
plt.close(fig)

# ========================= FIGURE 4: loss degradation =========================
fig, ax = plt.subplots(figsize=(3.4, 2.6))
groups = ["Baseline\n(no loss)", "3% packet loss"]
x = range(len(groups)); w = 0.34
nse_vals = [mean(nse_base_sla), mean(nse_loss_sla)]
esp_vals = [mean(esp_base_sla), mean(esp_loss_sla)]
ax.bar([i-w/2 for i in x], nse_vals, w, color=C["NSEdge"], label="NSEdge (packet-level)", edgecolor="black", linewidth=0.4)
ax.bar([i+w/2 for i in x], esp_vals, w, color=C["EdgeSimPy"], label="EdgeSimPy (flow-level)", edgecolor="black", linewidth=0.4)
ax.axhline(PHYS_LOSS_SLA, color="red", ls="--", lw=1.0, label=f"Physical @loss ({PHYS_LOSS_SLA}%)")
ax.set_xticks(list(x)); ax.set_xticklabels(groups)
ax.set_ylabel("SLA reliability (% within deadline)"); ax.set_ylim(0, 108)
ax.set_title("Packet-loss degradation")
for i, (a, b) in enumerate(zip(nse_vals, esp_vals)):
    ax.text(i-w/2, a+1.5, f"{a:.0f}", ha="center", fontsize=7)
    ax.text(i+w/2, b+1.5, f"{b:.0f}", ha="center", fontsize=7)
ax.legend(frameon=False, loc="lower left", fontsize=7)
fig.savefig(os.path.join(FIGS, "fig_loss_degradation.pdf"))
plt.close(fig)

# =============================== LaTeX table ==================================
def cell(e, k, fmt="{}"):
    v = M["engines"].get(e, {}).get(k)
    return fmt.format(v) if v is not None else "--"
rows = []
for e in ["NSEdge", "EdgeSimPy", "EdgeCloudSim", "Simu5G"]:
    if e not in M["engines"]: continue
    en = M["engines"][e]
    rows.append(" & ".join([
        e,
        "pkt" if en.get("models_packets") else "flow",
        cell(e, "rtf", "{:g}"),
        cell(e, "delay_ms", "{:.0f}") if en.get("delay_ms") else cell(e, "net_delay_ms", "{:.0f}"),
        cell(e, "sla_loss_pct", "{:.0f}") if en.get("sla_loss_pct") is not None else ("100" if e=="EdgeCloudSim" else "--"),
        r"\checkmark" if en.get("models_loss") else r"$\times$",
        cell(e, "rss_mb", "{:.0f}"),
    ]) + r" \\")
tex = (r"\begin{tabular}{lrrrrcr}" + "\n\\toprule\n"
       r"Simulator & Model & RTF & Delay & SLA$_{loss}$ & Loss? & RSS \\"
       + "\n & & & (ms) & (\\%) & & (MB) \\\\\n\\midrule\n"
       + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n")
open(os.path.join(RES, "benchmark_table.tex"), "w").write(tex)

print("WROTE benchmark_metrics.json, 4 figures, benchmark_table.tex")
print(json.dumps(M["engines"], indent=1)[:1500])
