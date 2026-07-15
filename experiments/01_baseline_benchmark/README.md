# Baseline Benchmark Experiments

This directory contains the data, logs, and figures generated from the initial cross-simulator evaluation and physical baseline validation.

## Contents
- `results/`: Contains the JSON metrics, CSV traces, and LaTeX tables from the NSEdge, EdgeSimPy, EdgeCloudSim, and Simu5G evaluations, as well as the testbed ground truth metrics.
- `figs/`: Contains the generated PDF plots (delay accuracy, loss degradation, scalability, and speed comparisons) used in the manuscript.

These previous experiments have been separated here to ensure a hygienic codebase and prevent data mix-ups with subsequent experiments (e.g., service migration).
