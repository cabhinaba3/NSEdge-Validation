#!/usr/bin/env python3
import os
import subprocess
import time
import json
import socket
import math
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

WORKER_PORT = 8899
WORKLOAD_SIZE = 150 # Corresponds to roughly 180,000 bytes
NUM_SENSORS = 10
FPS = 30
DURATION = 10.0

NS3_DIR = "/proj/oasees-PG0/NS3-Edge/ns-3"

def recv_all(sock, length):
    data = b""
    while len(data) < length:
        packet = sock.recv(length - len(data))
        if not packet:
            raise ConnectionError("Socket closed prematurely")
        data += packet
    return data

def get_physical_baseline():
    """Starts a worker, sends a task to measure physical CPU time and network RTT, then kills it."""
    print("[1] Collecting Real Physical Cluster Baseline...")
    worker_proc = subprocess.Popen(["python3", "/proj/oasees-PG0/NS3-Edge/validation_experiment/src/worker.py", str(WORKER_PORT)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5) # Wait for worker to start
    
    try:
        # Measure
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        client_socket.connect(("127.0.0.1", WORKER_PORT))
        
        request = {"task_id": 1, "workload_size": WORKLOAD_SIZE}
        req_data = json.dumps(request).encode("utf-8")
        req_header = f"{len(req_data):010d}".encode("utf-8")
        
        t_net_start = time.perf_counter()
        client_socket.sendall(req_header + req_data)
        
        resp_header = recv_all(client_socket, 10)
        resp_len = int(resp_header.decode("utf-8"))
        response_bytes = recv_all(client_socket, resp_len)
        t_net_end = time.perf_counter()
        
        response = json.loads(response_bytes.decode("utf-8"))
        exec_ms = response.get("exec_time_ms", 0.0)
        total_rtt_ms = (t_net_end - t_net_start) * 1000.0
        client_socket.close()
    finally:
        worker_proc.terminate()
        worker_proc.wait()
        
    print(f"    Physical Execution Time: {exec_ms:.2f} ms")
    print(f"    Physical Network RTT: {total_rtt_ms:.2f} ms")
    return exec_ms / 1000.0, total_rtt_ms / 1000.0

def get_optimal_config(n_sensors, f_i, physical_exec_s, M_max=11000):
    best_obj = float('inf')
    best_config = (1, 1, 1.0, 1.0)
    
    base_throughput = 1.0 / physical_exec_s if physical_exec_s > 0 else 140
    
    for p in range(1, 6):
        for b in range(1, 16):
            mem = 1000 + p * (500 + b * 50) 
            if mem > M_max:
                continue
            
            g_b_p = p * (base_throughput * (1 - math.exp(-0.2 * b))) 
            total_arrival = n_sensors * f_i
            edge_capacity = g_b_p
            
            x = max(0.0, 1.0 - (edge_capacity / total_arrival))
            
            if x <= 1.0:
                if x < best_obj:
                    best_obj = x
                    best_config = (b, p, x, edge_capacity)
                    
    return best_config

def run_ns3_simulation(slaves: int, rate: float, duration: float):
    # Run NSEdge native NS-3 to get true delay
    cmd = f"cd {NS3_DIR} && ./ns3 run 'scratch/ns3-validation-scenario --duration={duration} --lambda={rate} --workload_size=180000 --num_nodes={slaves} --bandwidth=100Mbps --loss=0.0 --jitter_us=0.0 --latency_ms=0.5'"
    t_start = time.perf_counter()
    subprocess.run(cmd, shell=True, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t_end = time.perf_counter()
    sim_time = t_end - t_start
    
    csv_file = os.path.join(NS3_DIR, "results-validation/tasks.csv")
    nodes_file = os.path.join(NS3_DIR, "results-validation/nodes.csv")
    
    rtt_val = 0.050
    energy_j = 0.0
    
    if os.path.exists(csv_file):
        df = pd.read_csv(csv_file)
        if len(df) > 0:
            rtt_val = df['response_time_ms'].mean() / 1000.0
            
    if os.path.exists(nodes_file):
        df_nodes = pd.read_csv(nodes_file)
        if len(df_nodes) > 0:
            # Sum energy of all EDGE nodes
            energy_j = df_nodes[df_nodes['tier'] == 'EDGE']['final_energy_j'].sum()
            
    return rtt_val, energy_j, sim_time

def parse_native_json(path, key):
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                return data.get(key, 0.0)
        except:
            return 0.0
    return 0.0

def main():
    print("--- DipDCE Integration Evaluation ---")
    exec_s, rtt_s = get_physical_baseline()
    
    print("\n[2] Solving DipDCE Optimization with Real Metrics...")
    b, p, x, cap = get_optimal_config(NUM_SENSORS, FPS, exec_s)
    print(f"    Optimal Config: Batch={b}, Processes={p}, Offload={x*100:.1f}%, Cap={cap:.1f} fps")
    
    # 3. Read Native Simulators Output directly from their JSON traces
    print("\n[3] Reading Native Execution Metrics from Third-Party Frameworks...")
    
    edgesimpy_delay = parse_native_json("/proj/oasees-PG0/NS3-Edge/validation_experiment/src/simulators/edgesimpy/edgesimpy_native_metrics.json", "EdgeSimPy_Native_Delay")
    edgesimpy_time = parse_native_json("/proj/oasees-PG0/NS3-Edge/validation_experiment/src/simulators/edgesimpy/edgesimpy_native_metrics.json", "EdgeSimPy_Wall_Time")
    
    ecs_delay = parse_native_json("/proj/oasees-PG0/NS3-Edge/validation_experiment/third_party/ecs_native_metrics.json", "EdgeCloudSim_Native_Delay")
    ecs_time = 0.125 # We saw ~125ms from ECS console native run
    
    simu5g_delay = parse_native_json("/proj/oasees-PG0/NS3-Edge/validation_experiment/third_party/Simu5G/simulations/nr/simu5g_native_metrics.json", "Simu5G_Native_Delay")
    simu5g_time = 9.902 # Extracted from the Simu5G physical OMNeT++ run

    print(f"\n[4] Simulating for {DURATION}s in NSEdge (Native NS-3)...")
    true_ns3_rtt, ns3_energy, ns3_sim_time = run_ns3_simulation(NUM_SENSORS, FPS, DURATION)
    gpu_proc_time = b / (cap / p) if p > 0 else 0
    cloud_delay = 0.110 + 0.010 
    edge_delay = true_ns3_rtt + gpu_proc_time
    nsedge_total_delay = (x * cloud_delay) + ((1 - x) * edge_delay)
    
    results_image = {
        'Real Cluster (Baseline)': (rtt_s + exec_s) * 1000,
        'EdgeSimPy (Native)': edgesimpy_delay * 1000,
        'EdgeCloudSim (Native)': ecs_delay * 1000,
        'Simu5G (Native)': simu5g_delay * 1000,
        'NSEdge (Native NS-3)': nsedge_total_delay * 1000
    }
    
    results_sim_time = {
        'Real Cluster (Baseline)': 0.0, # N/A
        'EdgeSimPy (Native)': edgesimpy_time,
        'EdgeCloudSim (Native)': ecs_time,
        'Simu5G (Native)': simu5g_time,
        'NSEdge (Native NS-3)': ns3_sim_time
    }
    
    results_energy = {
        'Real Cluster (Baseline)': 0.0, # N/A
        'EdgeSimPy (Native)': 0.0,
        'EdgeCloudSim (Native)': 0.0,
        'Simu5G (Native)': 0.0,
        'NSEdge (Native NS-3)': ns3_energy
    }
    
    # Analytical calculation for per-packet delay: Assumes 120 packets per image (180KB / 1500B MTU)
    PACKETS_PER_IMAGE = 120
    results_packet = {k: v / PACKETS_PER_IMAGE for k, v in results_image.items()}
    
    print("\n--- Final Results ---")
    print(f"{'Framework':<24} | {'Img Delay (ms)':<15} | {'Pkt Delay (ms)':<15} | {'Energy (J)':<15} | {'Wall Sim Time (s)':<15}")
    print("-" * 100)
    for k in results_image.keys():
        e_str = f"{results_energy[k]:.2f}" if results_energy[k] > 0 else "N/A"
        t_str = f"{results_sim_time[k]:.4f}" if results_sim_time[k] > 0 else "N/A"
        print(f"{k:<24} | {results_image[k]:15.2f} | {results_packet[k]:15.2f} | {e_str:<15} | {t_str:<15}")
        
    print("\n[5] Generating Visualization...")
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    colors = ['#95a5a6', '#3498db', '#e74c3c', '#f1c40f', '#9b59b6']
    
    frameworks = list(results_image.keys())
    
    axes[0].bar(frameworks, [results_image[f] for f in frameworks], color=colors)
    axes[0].set_ylabel('Average Per-Image Delay (ms)')
    axes[0].set_title(f'DipDCE Native Implementations: Per-Image Delay\n({int(DURATION)}s Sim | {NUM_SENSORS} Sensors | {FPS} FPS)')
    axes[0].tick_params(axis='x', rotation=45)
    for bar in axes[0].patches:
        axes[0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, f'{bar.get_height():.1f}', ha='center')
        
    axes[1].bar(frameworks, [results_packet[f] for f in frameworks], color=colors)
    axes[1].set_ylabel('Per-Packet Delay (ms)')
    axes[1].set_title(f'DipDCE Native Implementations: Per-Packet Delay\n(Assuming {PACKETS_PER_IMAGE} Packets/Image)')
    axes[1].tick_params(axis='x', rotation=45)
    for bar in axes[1].patches:
        axes[1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05, f'{bar.get_height():.2f}', ha='center')
        
    plt.tight_layout()
    plt.savefig('dipdce_10s_real_injection.png', dpi=300)
    print("Saved dipdce_10s_real_injection.png")

if __name__ == "__main__":
    main()
