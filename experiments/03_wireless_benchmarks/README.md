# Wireless Topologies (Wi-Fi 802.11ac and 5G-NR) Benchmark
This directory contains the instructions for running the DipDCE cross-simulator benchmark workload using Wi-Fi 802.11ac and 5G-NR (sub-6 GHz) access networks in NSEdge.

## Running the benchmarks
Run the benchmarks using the `dipdce-benchmark` scenario with the `--tech` argument.

**Wi-Fi 802.11ac:**
```bash
cd /proj/oasees-PG0/NS3-Edge/ns-3
./ns3 run 'scratch/dipdce-benchmark --tech=WIFI_80211AC --loss=0.0 --lambda=20 --num_nodes=4'
```

**5G-NR (Sub-6 GHz):**
```bash
cd /proj/oasees-PG0/NS3-Edge/ns-3
./ns3 run 'scratch/dipdce-benchmark --tech=NR_5G_SUB6 --loss=0.0 --lambda=20 --num_nodes=4'
```
