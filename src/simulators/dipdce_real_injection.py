#!/usr/bin/env python3

import os
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

import subprocess
import time
import json
import socket
import math
import random
import concurrent.futures
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
    print("[1] Collecting Single-Request Physical Cluster Baseline...")
    log_file = open(os.path.join(BASE_DIR, "worker.log"), "w")
    worker_proc = subprocess.Popen(["python3", os.path.join(BASE_DIR, "src/worker.py"), "--port", str(WORKER_PORT)], stdout=log_file, stderr=subprocess.STDOUT)
    time.sleep(1.5) # Wait for worker to start
    
    try:
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
        subprocess.run(["pkill", "-9", "-f", "worker.py"])
        worker_proc.wait(timeout=2)
        
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

def send_request(task_id):
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        client_socket.connect(("127.0.0.1", WORKER_PORT))
        
        request = {"task_id": task_id, "workload_size": WORKLOAD_SIZE}
        req_data = json.dumps(request).encode("utf-8")
        req_header = f"{len(req_data):010d}".encode("utf-8")
        
        t_net_start = time.perf_counter()
        client_socket.sendall(req_header + req_data)
        
        resp_header = recv_all(client_socket, 10)
        resp_len = int(resp_header.decode("utf-8"))
        recv_all(client_socket, resp_len)
        t_net_end = time.perf_counter()
        client_socket.close()
        return (t_net_end - t_net_start)
    except Exception:
        return 0.0

def run_physical_dipdce(b, p, x):
    print(f"\n[3] Generating Physical Traffic Profile (b={b}, p={p}, x={x*100:.1f}%) against Worker...")
    log_file = open(os.path.join(BASE_DIR, "worker.log"), "a")
    worker_proc = subprocess.Popen(["python3", os.path.join(BASE_DIR, "src/worker.py"), "--port", str(WORKER_PORT), "--batch-size", str(b), "--processes", str(p)], stdout=log_file, stderr=subprocess.STDOUT)
    time.sleep(1.5)
    
    total_requests = int(NUM_SENSORS * FPS * DURATION)
    interval = 1.0 / (NUM_SENSORS * FPS)
    delays = []
    
    print(f"    Pacing {total_requests} requests at {NUM_SENSORS * FPS} requests/sec...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=1000) as executor:
        futures = []
        for i in range(total_requests):
            if random.random() < x:
                delays.append(0.120) # 120ms cloud delay assumption
            else:
                futures.append(executor.submit(send_request, i))
            time.sleep(interval)
            
        for future in concurrent.futures.as_completed(futures):
            delays.append(future.result())
            
    subprocess.run(["pkill", "-9", "-f", "worker.py"])
    try:
        worker_proc.wait(timeout=2)
    except:
        pass
    
    avg_delay = sum(delays) / len(delays) if delays else 0.0
    print(f"    Physical DipDCE Average Delay: {avg_delay*1000:.2f} ms")
    return avg_delay

def run_ns3_simulation(slaves: int, rate: float, duration: float):
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
            energy_j = df_nodes[df_nodes['tier'] == 'EDGE']['final_energy_j'].sum()
            
    return rtt_val, energy_j, sim_time

def parse_native_json(path, key):
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                return data.get(key, 0.0)
        except:
            pass
    return 0.0

def main():
    print("--- DipDCE Integration Evaluation ---")
    exec_s, rtt_s = get_physical_baseline()
    
    print("\n[2] Solving DipDCE Optimization with Real Metrics...")
    b, p, x, cap = get_optimal_config(NUM_SENSORS, FPS, exec_s)
    print(f"    Optimal Config: Batch={b}, Processes={p}, Offload={x*100:.1f}%, Cap={cap:.1f} fps")
    
    physical_dipdce_delay = run_physical_dipdce(b, p, x)
    
    print("\n[4] Reading Native Execution Metrics from Third-Party Frameworks...")
    edgesimpy_delay = parse_native_json(os.path.join(BASE_DIR, "src/simulators/edgesimpy/edgesimpy_native_metrics.json"), "EdgeSimPy_Native_Delay")
    edgesimpy_time = parse_native_json(os.path.join(BASE_DIR, "src/simulators/edgesimpy/edgesimpy_native_metrics.json"), "EdgeSimPy_Wall_Time")
    ecs_delay = parse_native_json(os.path.join(BASE_DIR, "third_party/ecs_native_metrics.json"), "EdgeCloudSim_Native_Delay")
    ecs_time = 0.125
    simu5g_delay = parse_native_json(os.path.join(BASE_DIR, "third_party/Simu5G/simulations/nr/simu5g_native_metrics.json"), "Simu5G_Native_Delay")
    simu5g_time = 9.902
    
    print(f"\n[5] Simulating for {DURATION}s in NSEdge (Native NS-3)...")
    true_ns3_rtt, ns3_energy, ns3_sim_time = run_ns3_simulation(NUM_SENSORS, FPS, DURATION)
    
    gpu_proc_time = b / (cap / p) if p > 0 else 0
    cloud_delay = 0.110 + 0.010 
    edge_delay = true_ns3_rtt + gpu_proc_time
    nsedge_total_delay = (x * cloud_delay) + ((1 - x) * edge_delay)
    
    results = {
        'DipDCE Physical (Real Baseline)': physical_dipdce_delay * 1000,
        'EdgeSimPy (Native)': edgesimpy_delay * 1000,
        'EdgeCloudSim (Native)': ecs_delay * 1000,
        'Simu5G (Native)': simu5g_delay * 1000,
        'NSEdge (Native NS-3)': nsedge_total_delay * 1000
    }
    
    # Export metrics to JSON for Jupyter Notebook Plotting
    os.makedirs(os.path.join(BASE_DIR, "results"), exist_ok=True)
    out_file = os.path.join(BASE_DIR, "results", "dipdce_native_metrics_final.json")
    with open(out_file, "w") as f:
        json.dump(results, f, indent=4)
        
    print(f"\nResults successfully exported to {out_file}.")
    print("Please use notebooks/plot_dipdce_baseline.ipynb to generate the physical baseline visualizations.")

if __name__ == "__main__":
    main()
