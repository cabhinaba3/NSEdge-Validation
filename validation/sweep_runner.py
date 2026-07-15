#!/usr/bin/env python3

import os
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

"""Unified Multi-Scenario Empirical Sweep Runner.

Orchestrates multi-dimensional sweeps (node count, link rate, job rate) across
the physical cluster and the packet-level simulator. Computes stats and
renders publication-quality figures.
"""

import os
import subprocess
import time
import csv
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SLAVES = ["n0710-09", "n078-27", "n079-22", "n0710-10"]
IFACES = ["enp1s0f3", "enp3s0", "enp1s0f0", "enp1s0f1"]
WORKER_PATH = os.path.join(BASE_DIR, "src/worker.py")
ORCH_PATH = os.path.join(BASE_DIR, "src/orchestrator.py")
PYTHON_VENV = "/proj/oasees-PG0/net4hpc/.venv/bin/python3"
NS3_DIR = "/proj/oasees-PG0/NS3-Edge/ns-3"

def start_workers(n: int) -> None:
    print(f"--> Spawning {n} physical workers on slavenodes...")
    for i in range(n):
        host = SLAVES[i]
        cmd = f"ssh -f -o StrictHostKeyChecking=no {host} 'nohup {PYTHON_VENV} {WORKER_PATH} > /tmp/worker.log 2>&1 < /dev/null &'"
        subprocess.run(cmd, shell=True, check=True)
    time.sleep(2)

def stop_workers() -> None:
    print("--> Terminating all remote physical workers...")
    for host in SLAVES:
        cmd = f"ssh -o StrictHostKeyChecking=no {host} 'pkill -f src/worker.py' || true"
        subprocess.run(cmd, shell=True)

def apply_shaping(bw_mbps: int) -> None:
    print(f"--> Applying Linux tc qdisc rate limiting: {bw_mbps} Mbps...")
    for dev in IFACES:
        subprocess.run(f"sudo tc qdisc del dev {dev} root || true", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cmd = f"sudo tc qdisc add dev {dev} root tbf rate {bw_mbps}mbit burst 32k latency 100ms"
        subprocess.run(cmd, shell=True, check=True)

def clear_shaping() -> None:
    print("--> Clearing all Linux tc qdisc configurations...")
    for dev in IFACES:
        subprocess.run(f"sudo tc qdisc del dev {dev} root || true", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def load_avg_rtt(csv_path: str) -> float:
    rtts = []
    if not os.path.exists(csv_path):
        return 0.0
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Physical records RTT in ms
            if "response_time_ms" in row and row["response_time_ms"]:
                rtts.append(float(row["response_time_ms"]))
            # Simulated logs completion & arrival times in seconds
            elif "arrival_time_s" in row and "completion_time_s" in row:
                rtt = (float(row["completion_time_s"]) - float(row["arrival_time_s"])) * 1000.0
                rtts.append(rtt)
    return float(np.mean(rtts)) if rtts else 0.0

def run_physical(duration: float, rate: float, size: int, policy: str, slaves: int, csv_out: str) -> float:
    stop_workers()
    start_workers(slaves)
    cmd = f"{PYTHON_VENV} {ORCH_PATH} {duration} {rate} {size} {policy} {slaves} {csv_out}"
    subprocess.run(cmd, shell=True, check=True)
    stop_workers()
    return load_avg_rtt(csv_out)

def run_simulated(duration: float, rate: float, size: int, slaves: int, bandwidth: str, csv_out_dir: str) -> float:
    cmd = f"cd {NS3_DIR} && ./ns3 run 'ns3-validation-scenario --duration={duration} --lambda={rate} --workload_size={size*size*8} --num_nodes={slaves} --bandwidth={bandwidth}'"
    subprocess.run(cmd, shell=True, check=True)
    csv_file = os.path.join(NS3_DIR, "results-validation/tasks.csv")
    return load_avg_rtt(csv_file)

def main() -> None:
    print("==================================================")
    print("      NSEdge Unified Empirical Sweep Engine")
    print("==================================================")
    
    os.makedirs("results", exist_ok=True)
    os.makedirs("docs", exist_ok=True)
    
    # Clean initial state
    stop_workers()
    clear_shaping()

    # ----------------------------------------------------
    # SWEEP 1: Federated Learning - Client Node Scalability
    # ----------------------------------------------------
    print("\n[Sweep 1] Scalability (Client Nodes Sweep)")
    nodes_x = [1, 2, 3, 4]
    sweep1_phys = []
    sweep1_sim = []
    
    for n in nodes_x:
        print(f"\nEvaluating: Client Nodes = {n}")
        phys_csv = f"results/sweep1_phys_nodes_{n}.csv"
        
        # Physical Execution (Duration = 10s, Rate = 5Hz, Workload Size = 150)
        phys_rtt = run_physical(10.0, 5.0, 150, "rr", n, phys_csv)
        sweep1_phys.append(phys_rtt)
        
        # Simulated Execution
        sim_rtt = run_simulated(10.0, 5.0, 150, n, "760Mbps", "results/sweep1_sim")
        sweep1_sim.append(sim_rtt)
        
        print(f"--> Nodes {n} | Phys = {phys_rtt:.2f} ms | Sim = {sim_rtt:.2f} ms")

    # ----------------------------------------------------
    # SWEEP 2: Smart City - Network Bandwidth Constraints
    # ----------------------------------------------------
    print("\n[Sweep 2] Networking (Bandwidth Sweep)")
    bw_x = [10, 20, 50, 100, 200, 500]
    sweep2_phys = []
    sweep2_sim = []
    
    for bw in bw_x:
        print(f"\nEvaluating: Bandwidth Limit = {bw} Mbps")
        apply_shaping(bw)
        phys_csv = f"results/sweep2_phys_bw_{bw}.csv"
        
        # Physical Execution (Duration = 10s, Rate = 5Hz, Workload Size = 150, Nodes = 4)
        phys_rtt = run_physical(10.0, 5.0, 150, "rr", 4, phys_csv)
        sweep2_phys.append(phys_rtt)
        clear_shaping()
        
        # Simulated Execution
        sim_rtt = run_simulated(10.0, 5.0, 150, 4, f"{bw}Mbps", "results/sweep2_sim")
        sweep2_sim.append(sim_rtt)
        
        print(f"--> Bandwidth {bw} Mbps | Phys = {phys_rtt:.2f} ms | Sim = {sim_rtt:.2f} ms")

    # ----------------------------------------------------
    # SWEEP 3: Workload Intensity - Task Generation Rate
    # ----------------------------------------------------
    print("\n[Sweep 3] Workload Intensity (Poisson Rate Sweep)")
    rates_x = [2.0, 4.0, 6.0, 8.0, 10.0]
    sweep3_phys = []
    sweep3_sim = []
    
    for r in rates_x:
        print(f"\nEvaluating: Arrival Rate = {r} Hz")
        phys_csv = f"results/sweep3_phys_rate_{r}.csv"
        
        # Physical Execution (Duration = 10s, Rate = r, Workload Size = 150, Nodes = 4)
        phys_rtt = run_physical(10.0, r, 150, "rr", 4, phys_csv)
        sweep3_phys.append(phys_rtt)
        
        # Simulated Execution
        sim_rtt = run_simulated(10.0, r, 150, 4, "760Mbps", "results/sweep3_sim")
        sweep3_sim.append(sim_rtt)
        
        print(f"--> Rate {r} Hz | Phys = {phys_rtt:.2f} ms | Sim = {sim_rtt:.2f} ms")

    # ----------------------------------------------------
    # Plotting Publication-Quality Figures (Separate plots)
    # ----------------------------------------------------
    print("\nRendering separate Federated Learning and Smart City validation plots...")
    
    # 1. Federated Learning Scenario Validation Plot
    plt.figure(figsize=(7, 5))
    plt.plot(nodes_x, sweep1_phys, marker='o', label="Physical (i5 Cluster)", color="#1f77b4", linewidth=2.5)
    plt.plot(nodes_x, sweep1_sim, marker='s', label="NSEdge Simulation", color="#d62728", linestyle="--", linewidth=2.5)
    plt.title("Federated Learning Scenario: Client Node Scalability", fontsize=12, fontweight="bold")
    plt.xlabel("Number of Participating Client Nodes", fontsize=10)
    plt.ylabel("Mean Local Epoch Training & Aggregation RTT (ms)", fontsize=10)
    plt.xticks(nodes_x)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend(fontsize=10)
    plt.tight_layout()
    plt.savefig("docs/federated_sweeps.png", dpi=300)
    plt.close()
    
    # 2. Smart City Scenario Validation Plot (2 subplots: Bandwidth and Load Intensity)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Subplot 2.1: Bandwidth constraints
    ax1.plot(bw_x, sweep2_phys, marker='o', label="Physical (i5 Cluster)", color="#1f77b4", linewidth=2.2)
    ax1.plot(bw_x, sweep2_sim, marker='s', label="NSEdge Simulation", color="#d62728", linestyle="--", linewidth=2.2)
    ax1.set_title("Smart City Scenario: Network Bandwidth constraints", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Link Bandwidth Limit (Mbps)", fontsize=10)
    ax1.set_ylabel("Mean Task Offloading RTT (ms)", fontsize=10)
    ax1.set_xscale("log")
    ax1.set_xticks(bw_x)
    ax1.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.legend(fontsize=9)
    
    # Subplot 2.2: Arrival Rate Load Intensity
    ax2.plot(rates_x, sweep3_phys, marker='o', label="Physical (i5 Cluster)", color="#1f77b4", linewidth=2.2)
    ax2.plot(rates_x, sweep3_sim, marker='s', label="NSEdge Simulation", color="#d62728", linestyle="--", linewidth=2.2)
    ax2.set_title("Smart City Scenario: Load Intensity (Arrival Rate)", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Task Generation Rate (Hz)", fontsize=10)
    ax2.set_ylabel("Mean Task Offloading RTT (ms)", fontsize=10)
    ax2.set_xticks(rates_x)
    ax2.grid(True, linestyle=":", alpha=0.6)
    ax2.legend(fontsize=9)
    
    plt.suptitle("Smart City Scenario Validation Sweeps", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig("docs/smart_city_sweeps.png", dpi=300)
    plt.close()
    
    print("Plots saved successfully to docs/federated_sweeps.png and docs/smart_city_sweeps.png")

    # Save JSON metrics file
    sweep_results = {
        "sweep1_nodes": {"x": nodes_x, "phys": sweep1_phys, "sim": sweep1_sim},
        "sweep2_bw": {"x": bw_x, "phys": sweep2_phys, "sim": sweep2_sim},
        "sweep3_rate": {"x": rates_x, "phys": sweep3_phys, "sim": sweep3_sim}
    }
    with open("results/sweep_metrics.json", "w") as f:
        json.dump(sweep_results, f, indent=4)
        
    print("Sweep metrics exported successfully to results/sweep_metrics.json")

if __name__ == "__main__":
    main()
