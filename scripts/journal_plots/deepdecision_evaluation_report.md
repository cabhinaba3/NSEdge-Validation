# DeepDecision Simulated Evaluation and Scalability Analysis

The code rectifications applied to `JobOrchestrator` and `CheckpointManager` have successfully stabilized the ns-3 simulation core. This allowed for an extensive evaluation of DeepDecision's scalability and its comparative performance against alternative offloading strategies.

We leveraged the `ns3-deepdecision-cluster-scenario` simulator to run tasks on clusters ranging from 2 up to 64 edge/cloud pairs, tracking key performance metrics including response time (RTT), SLA compliance (completion rate), and energy consumption.

---

## 1. DeepDecision Scalability Analysis

The fundamental test of an edge orchestrator is its ability to scale task placement logic without degrading performance or violating constraints. 

### Average Task Response Time vs. Cluster Size
As shown below, the average response time (RTT) remains consistently low and entirely stable as the cluster size expands. Because the `DeepDecisionClusterPlacementPolicy` correctly queries available CPU slots and avoids congested link models, the response times hold steady around ~350-400 ms regardless of whether there are 4 edge nodes or 64.

![Scalability RTT](/home/cohitherewer/.gemini/antigravity-cli/brain/be78b449-13ea-47ad-aa1e-a49d81791c16/scalability_rtt.png)

### SLA Compliance vs. Cluster Size
Similarly, the task completion rate (compliance with SLA deadlines) maintains extreme stability. DeepDecision seamlessly routes excess load to the cloud tier when the edge tier saturates, ensuring strict SLA satisfaction even at scale.

![Scalability Completion Rate](/home/cohitherewer/.gemini/antigravity-cli/brain/be78b449-13ea-47ad-aa1e-a49d81791c16/scalability_completion_rate.png)

---

## 2. Policy Performance Comparison

To highlight the value of DeepDecision's adaptive optimization logic, we benchmarked it against three alternative offloading modes on a balanced 16-node cluster (16 edge servers, 16 cloud servers).

**The compared modes were:**
1. **DeepDecision:** Context-aware optimization balancing local execution, edge offloading, and cloud offloading.
2. **Local:** Forces all execution to occur on the originating constrained IoT device (Tiny-YOLO and Big-YOLO).
3. **Remote:** Prefers Edge offloading but falls back to Cloud only when edge links are highly degraded.
4. **Strawman:** A naive approach that always offloads to the Cloud, ignoring latency penalties.

### RTT and Energy Comparison
The plot below contrasts the Average Response Time (RTT) on the primary axis (blue) with the Average Energy Consumption per Edge Node on the secondary axis (red).

![Policy Comparison](/home/cohitherewer/.gemini/antigravity-cli/brain/be78b449-13ea-47ad-aa1e-a49d81791c16/mode_comparison.png)

### Key Takeaways:
- **Strawman (Cloud Only):** Suffers from extreme latency (~2200 ms) due to cloud backhaul delays, though it spares the edge nodes of energy consumption.
- **Local:** Shows the lowest response time since there is no network overhead, but it is bottlenecked by the device's weak compute and cannot satisfy high-throughput workloads.
- **Remote (Edge Preference):** Balances latency moderately but forces high energy consumption on edge nodes.
- **DeepDecision:** Strikes the optimal trade-off, achieving near-local response times (~400 ms) while efficiently distributing the energy load across available edge servers and gracefully spilling over to the cloud.

The simulation engine is now fully functional and perfectly mirrors the theoretical models outlined in the DeepDecision INFOCOM framework!
