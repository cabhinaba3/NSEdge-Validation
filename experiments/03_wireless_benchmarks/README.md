# Wireless Topologies (Wi-Fi 802.11ac and 5G-NR) Benchmark
This directory isolates the instructions for running the DipDCE cross-simulator benchmark workload using Wi-Fi 802.11ac and 5G-NR (sub-6 GHz) access networks in NSEdge.

---

## 1. Running the benchmarks

Run the benchmarks by executing the `dipdce-benchmark` scenario directly via ns-3 from the root of `NSEdge-Validation`.
We specify the access network technology using the `--tech` argument.

From the root of `NSEdge-Validation`:

**Wi-Fi 802.11ac:**
```bash
cd ../ns-3
./ns3 run 'scratch/dipdce-benchmark --tech=WIFI_80211AC --loss=0.0 --lambda=20 --num_nodes=4'
cd ../NSEdge-Validation
```

**5G-NR (Sub-6 GHz):**
```bash
cd ../ns-3
./ns3 run 'scratch/dipdce-benchmark --tech=NR_5G_SUB6 --loss=0.0 --lambda=20 --num_nodes=4'
cd ../NSEdge-Validation
```

*(Output traces will be automatically generated and exported as `.csv` files inside `/proj/oasees-PG0/NS3-Edge/ns-3/results/` depending on your configurations.)*

---

## 2. Generating the Plots

To parse these wireless benchmarks systematically and generate figures against baseline configurations, use the main benchmark measuring harness:

From the root of `NSEdge-Validation`:
```bash
python3 benchmark/measure_nsedge_wifi.py
python3 benchmark/plot_benchmark.py
```

This will automatically extract the metrics and output consolidated PDF plots comparing the wireless access networks into the `figs/` directory.
