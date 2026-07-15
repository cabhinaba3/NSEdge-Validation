#!/usr/bin/env python3
"""Runner script for DeepDecision validation (INFOCOM 2018) with Edge & Cloud clusters.

Runs both the physical orchestrator and ns-3 simulation across all 4 modes,
compares per-image processing delay, energy consumption, and model accuracy,
and renders comparative figures.
"""

import os
import subprocess
import time
import csv
import math
import json
import numpy as np
import threading
import matplotlib.pyplot as plt

DURATION = 100.0
NS3_DIR = "/proj/oasees-PG0/NS3-Edge/ns-3"
VAL_DIR = "/proj/oasees-PG0/NS3-Edge/validation_experiment"

SLAVES = ["n0710-09", "n078-27", "n079-22", "n0710-10"]
MODES = ["deepdecision", "local", "remote", "strawman"]

def stop_workers():
    print("--> Terminating remote workers on all cluster nodes...")
    for host in SLAVES:
        subprocess.run(
            f"ssh -o StrictHostKeyChecking=no {host} 'pkill -f src/worker.py' || true",
            shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

def start_workers():
    print("--> Spawning workers on all 4 cluster nodes...")
    for host in SLAVES:
        cmd = (
            f"ssh -f -o StrictHostKeyChecking=no {host} "
            f"'nohup /proj/oasees-PG0/net4hpc/.venv/bin/python3 "
            f"{VAL_DIR}/src/worker.py > /tmp/worker_dd_{host}.log 2>&1 < /dev/null &'"
        )
        subprocess.run(cmd, shell=True, check=True)
    time.sleep(2)  # Wait for socket startup

def apply_dynamic_shaping_profile(duration_s: float) -> threading.Thread:
    """Spawns a thread to apply the dynamic bandwidth/delay profile using tc qdisc netem."""
    def run_profile():
        edge_devs = ["enp1s0f3", "enp3s0"]
        cloud_devs = ["enp1s0f0", "enp1s0f1"]
        
        # Clear any existing shaping first
        for dev in edge_devs + cloud_devs:
            subprocess.run(f"sudo tc qdisc del dev {dev} root || true", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Apply constant cloud links shaping: 5 Mbps, 80 ms delay
        for dev in cloud_devs:
            print(f"--> Dynamic Shaping: setting cloud link {dev} to 5 Mbps, 80 ms delay...")
            subprocess.run(f"sudo tc qdisc add dev {dev} root netem rate 5mbit delay 80ms", shell=True, check=True)
            
        # Step 1: Edge links 100 kbps, 10 ms delay (t < 20s)
        for dev in edge_devs:
            print(f"--> Dynamic Shaping: setting edge link {dev} to 100 kbps, 10 ms delay (t < 20s)...")
            subprocess.run(f"sudo tc qdisc add dev {dev} root netem rate 100kbit delay 10ms", shell=True, check=True)
            
        # Wait 20s
        time.sleep(20)
        
        # Step 2: Edge links 500 kbps, 10 ms delay (20 <= t < 60s)
        for dev in edge_devs:
            print(f"--> Dynamic Shaping: transitioning edge link {dev} to 500 kbps, 10 ms delay (20 <= t < 60s)...")
            subprocess.run(f"sudo tc qdisc replace dev {dev} root netem rate 500kbit delay 10ms", shell=True, check=True)
            
        # Wait 40s
        time.sleep(40)
        
        # Step 3: Edge links 1000 kbps, 10 ms delay (t >= 60s)
        for dev in edge_devs:
            print(f"--> Dynamic Shaping: transitioning edge link {dev} to 1000 kbps, 10 ms delay (t >= 60s)...")
            subprocess.run(f"sudo tc qdisc replace dev {dev} root netem rate 1000kbit delay 10ms", shell=True, check=True)
            
        # Wait remainder of duration
        rem = max(0.0, duration_s - 60)
        if rem > 0:
            time.sleep(rem)
            
        # Cleanup at end
        print("--> Dynamic Shaping: clearing shaping on all devices...")
        for dev in edge_devs + cloud_devs:
            subprocess.run(f"sudo tc qdisc del dev {dev} root || true", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    t = threading.Thread(target=run_profile, daemon=False)
    t.start()
    return t

def run_physical_mode(mode: str) -> str:
    out_csv = f"results/deepdecision_phys_{mode}.csv"
    if os.path.exists(out_csv):
        os.remove(out_csv)
    print(f"--> Running Physical test for mode: {mode} ({DURATION}s)...")
    
    # Start dynamic netem shaping
    shaper_thread = apply_dynamic_shaping_profile(DURATION)
    
    try:
        cmd = (
            f"/proj/oasees-PG0/net4hpc/.venv/bin/python3 src/deepdecision_orchestrator.py "
            f"{DURATION} {mode} {out_csv}"
        )
        subprocess.run(cmd, shell=True, check=True)
    finally:
        # Guarantee cleanup of netem shaping
        for dev in ["enp1s0f3", "enp3s0", "enp1s0f0", "enp1s0f1"]:
            subprocess.run(f"sudo tc qdisc del dev {dev} root || true", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
    return out_csv

def run_simulated_mode(mode: str) -> str:
    dst_csv = f"results/deepdecision_sim_{mode}.csv"
    if os.path.exists(dst_csv):
        os.remove(dst_csv)
    print(f"--> Running Simulation test for mode: {mode} ({DURATION}s)...")
    cmd = (
        f"cd {NS3_DIR} && ./ns3 run 'ns3-deepdecision-cluster-scenario --duration={DURATION} --mode={mode} --num_edges=2 --num_clouds=2'"
    )
    subprocess.run(cmd, shell=True, check=True)
    
    # Copy output tasks.csv to unique path
    src_csv = os.path.join(NS3_DIR, "results-deepdecision/tasks.csv")
    dst_csv = f"results/deepdecision_sim_{mode}.csv"
    if os.path.exists(src_csv):
        import shutil
        shutil.copy(src_csv, dst_csv)
    return dst_csv

def analyze_csv(file_path: str, is_sim: bool = False) -> dict:
    """Analyzes results and returns average delay, energy, and accuracy."""
    delays = []
    energies = []
    accuracies = []
    
    if not os.path.exists(file_path):
        print(f"Warning: File {file_path} not found.")
        return {"delay": 0.0, "energy": 0.0, "accuracy": 0.0}
        
    with open(file_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if is_sim:
                # In simulation: task_id,workload_class,node_id,size_bytes,arrival_time_s,queue_time_s,exec_time_s,completion_time_s,response_time_ms,met_sla
                rtt = float(row.get("response_time_ms", 0.0))
                size = int(row.get("size_bytes", 100))
                node_id = int(row.get("node_id", 0))
                
                # Energy mapping
                if node_id in [1, 2, 3, 4]:
                    power = 2060.0
                elif size in [100, 200, 300]:
                    power = 3727.0
                else:
                    power = 5000.0
                    
                # Accuracy mapping
                if node_id in [1, 2]: # Edge offload
                    base_acc = 0.60 if size == 400 else (0.80 if size == 500 else 0.90)
                    bit_disc = 0.65 if size == 400 else (0.85 if size == 500 else 1.0)
                    staleness = math.exp(-0.002 * max(0.0, rtt - 100.0))
                    acc = base_acc * bit_disc * staleness
                elif node_id in [3, 4]: # Cloud offload
                    base_acc = 0.65 if size == 400 else (0.85 if size == 500 else 0.95)
                    bit_disc = 0.65 if size == 400 else (0.85 if size == 500 else 1.0)
                    staleness = math.exp(-0.002 * max(0.0, rtt - 100.0))
                    acc = base_acc * bit_disc * staleness
                else: # Local
                    if size == 100: acc = 0.30
                    elif size == 200: acc = 0.45
                    elif size == 300: acc = 0.55
                    elif size == 400: acc = 0.55
                    elif size == 500: acc = 0.75
                    else: acc = 0.85
            else:
                # In physical orchestrator csv format
                rtt = float(row.get("response_time_ms", 0.0))
                power = float(row.get("energy_mw", 0.0))
                acc = float(row.get("accuracy", 0.0))
                
            delays.append(rtt)
            energies.append(power)
            accuracies.append(acc * 100.0) # convert to %
            
    return {
        "delay": np.mean(delays) if delays else 0.0,
        "energy": np.mean(energies) if energies else 0.0,
        "accuracy": np.mean(accuracies) if accuracies else 0.0
    }

def main():
    os.makedirs("results", exist_ok=True)
    os.makedirs("docs", exist_ok=True)
    
    stop_workers()
    start_workers()
    
    results = {
        "phys": {},
        "sim": {}
    }
    
    # Run physical experiments
    for mode in MODES:
        csv_path = run_physical_mode(mode)
        results["phys"][mode] = analyze_csv(csv_path, is_sim=False)
        
    stop_workers()
    
    # Run simulation experiments
    for mode in MODES:
        csv_path = run_simulated_mode(mode)
        results["sim"][mode] = analyze_csv(csv_path, is_sim=True)
        
    print("\n==================================================")
    print("      DeepDecision Cluster Validation Results")
    print("==================================================")
    for mode in MODES:
        print(f"\nMode: {mode.upper()}")
        print(f"  Physical: Delay = {results['phys'][mode]['delay']:.2f} ms | Energy = {results['phys'][mode]['energy']:.2f} mW | Accuracy = {results['phys'][mode]['accuracy']:.2f}%")
        print(f"  Simulated: Delay = {results['sim'][mode]['delay']:.2f} ms | Energy = {results['sim'][mode]['energy']:.2f} mW | Accuracy = {results['sim'][mode]['accuracy']:.2f}%")
        
    # Write JSON results
    with open("results/deepdecision_results.json", "w") as f:
        json.dump(results, f, indent=4)
        
    # Render comparative plots
    render_plots(results)
    
    print("\nAll experiments successfully completed and plotted!")

def render_plots(results):
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    modes_labels = ["DeepDecision", "Local-Only", "Remote-Only", "Strawman"]
    
    phys_delays = [results["phys"][m]["delay"] for m in MODES]
    sim_delays = [results["sim"][m]["delay"] for m in MODES]
    
    phys_energies = [results["phys"][m]["energy"] for m in MODES]
    sim_energies = [results["sim"][m]["energy"] for m in MODES]
    
    phys_accuracies = [results["phys"][m]["accuracy"] for m in MODES]
    sim_accuracies = [results["sim"][m]["accuracy"] for m in MODES]
    
    x = np.arange(len(modes_labels))
    width = 0.35
    
    # Plot 1: Per-image Processing Delay
    axes[0].bar(x - width/2, phys_delays, width, label="Physical (Cluster)", color="#4A90E2")
    axes[0].bar(x + width/2, sim_delays, width, label="NSEdge Cluster Sim", color="#50E3C2")
    axes[0].set_ylabel("Per-Image Delay (ms)")
    axes[0].set_title("Processing Delay Comparison")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(modes_labels)
    axes[0].grid(axis="y", linestyle="--", alpha=0.7)
    axes[0].legend()
    
    # Plot 2: Energy Consumption at Edge
    axes[1].bar(x - width/2, phys_energies, width, label="Physical (Cluster)", color="#D0021B")
    axes[1].bar(x + width/2, sim_energies, width, label="NSEdge Cluster Sim", color="#F5A623")
    axes[1].set_ylabel("Energy Consumption at Edge (mW)")
    axes[1].set_title("Energy Consumption Comparison")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(modes_labels)
    axes[1].grid(axis="y", linestyle="--", alpha=0.7)
    axes[1].legend()
    
    # Plot 3: Model Accuracy
    axes[2].bar(x - width/2, phys_accuracies, width, label="Physical (Cluster)", color="#7ED321")
    axes[2].bar(x + width/2, sim_accuracies, width, label="NSEdge Cluster Sim", color="#B8E986")
    axes[2].set_ylabel("Model Accuracy (%)")
    axes[2].set_title("Model Accuracy Comparison")
    axes[2].set_xticks(x)
    axes[2].set_xticklabels(modes_labels)
    axes[2].grid(axis="y", linestyle="--", alpha=0.7)
    axes[2].legend()
    
    plt.tight_layout()
    plt.savefig("docs/deepdecision_comparison.png", dpi=300)
    plt.close()

if __name__ == "__main__":
    main()
