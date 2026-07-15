# Baseline Benchmark Experiments

This directory contains the data, logs, and figures generated from the initial cross-simulator evaluation and physical baseline validation.

These previous experiments have been separated here to ensure a hygienic codebase and prevent data mix-ups with subsequent experiments (e.g., service migration).

## Contents
- `results/`: Contains the JSON metrics, CSV traces, and LaTeX tables from the NSEdge, EdgeSimPy, EdgeCloudSim, and Simu5G evaluations, as well as the testbed ground truth metrics.
- `figs/`: Contains the generated PDF plots (delay accuracy, loss degradation, scalability, and speed comparisons) used in the manuscript.

---

## 1. Running the Cross-Simulator Benchmarks

All benchmark orchestration scripts are located in the `benchmark/` folder at the root of `NSEdge-Validation`.
To reproduce the baseline benchmark results:

From the root of `NSEdge-Validation`:

**Run NSEdge Baseline (Ethernet & Wi-Fi):**
```bash
# This automatically executes the ns-3 C++ scenario and parses the output
python3 benchmark/measure_nsedge.py
python3 benchmark/measure_nsedge_wifi.py
```

**Run Flow-Level Engines (EdgeSimPy & EdgeCloudSim):**
```bash
python3 benchmark/measure_edgesimpy.py
bash benchmark/measure_edgecloudsim.sh
```

**Run Packet-Level 5G Baseline (Simu5G):**
```bash
bash benchmark/measure_simu5g.sh
```

---

## 2. Generating the Plots
After running all the benchmark scripts, the raw metrics are saved in `results/` in the root directory. To combine these into the final PDF plots:

From the root of `NSEdge-Validation`:
```bash
python3 benchmark/plot_benchmark.py
```

This consolidates the measurements into `results/consolidated_metrics.json` and outputs the figures into `figs/` (e.g., `figs/delay_accuracy.pdf`, `figs/loss_degradation.pdf`, `figs/scalability.pdf`, `figs/speed_comparison.pdf`). 
You can then archive these generated files into `experiments/01_baseline_benchmark/results/` and `experiments/01_baseline_benchmark/figs/` for safekeeping.
