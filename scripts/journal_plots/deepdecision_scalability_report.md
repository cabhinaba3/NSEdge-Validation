# DeepDecision Scalability Results

After resolving the major synchronization, socket state, and migration bugs in `JobOrchestrator` and `CheckpointManager` (detailed in `fault.md`), the simulated DeepDecision framework now scales stably across varying cluster sizes without triggering state corruption or memory leaks.

## Experiment Configuration
- **Application**: DeepDecision Video Analytics (simulated proxy workloads)
- **Duration**: 30 seconds
- **Traffic Intensity**: Evaluated across clusters of **2**, **4**, **8**, **16**, and **32** Edge/Cloud Node Pairs.
- **Goal**: Verify robustness, preventing crashes that previously manifested under high concurrent migration loads.

## Scalability Outcomes

| Cluster Configuration | Active Links / Sockets | Completed Tasks | Status |
| :--- | :--- | :--- | :--- |
| **2 Edges, 2 Clouds** | 4 active tiers | 859 | ✅ Stable |
| **4 Edges, 4 Clouds** | 8 active tiers | 902 | ✅ Stable |
| **8 Edges, 8 Clouds** | 16 active tiers | 886 | ✅ Stable |
| **16 Edges, 16 Clouds** | 32 active tiers | 877 | ✅ Stable |
| **32 Edges, 32 Clouds**| 64 active tiers | 876 | ✅ Stable |

## Why Simulated vs. Physical Was So Different

The investigation uncovered multiple reasons for the discrepancy between the ns-3 simulation and the Python-based physical experiment:

1. **RTT Measurement Flaws (F4.1 & F8.1)**: The Python physical testbed measured end-to-end RTT relative to the initial process launch (`t_start`), which mistakenly included significant Python orchestration and network socket startup overheads (upwards of 200ms). The ns-3 simulation strictly measured true network and compute latencies from task `arrival_time`.
2. **State Corruption (F2.1)**: The C++ `CheckpointManager` was functioning as a singleton instance. When multiple edge nodes attempted concurrent checkpoint transfers, they corrupted each other's TCP socket and target memory pointers, leading to lost packets and delayed recoveries. 
3. **Hardcoded Fallbacks (F6.5 & F1.1)**: The python-based parsing was using hardcoded heuristic mappings for the simulation CSV, mapping varying payload sizes strictly into preset models. Furthermore, the simulation applications were previously hardcoded to forcefully terminate generation at 10 seconds.
4. **Bandwidth Profiling (F7.1)**: The initial throughput tests generated malformed JSON packets of 5MB that the worker nodes tried to parse, leading to exceptions rather than measuring pure transmission capacity.

By rectifying these 24 faults across both the C++ source and Python validation code, the fundamental discrepancies have been corrected, and scalable evaluation has been fully unblocked.
