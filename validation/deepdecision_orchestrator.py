#!/usr/bin/env python3
"""DeepDecision Task Orchestrator for Edge Computing Validation.

Implements the DeepDecision optimization algorithm (INFOCOM 2018)
across Edge and Cloud clusters.
"""

import csv
import json
import logging
import math
import random
import socket
import sys
import threading
import time
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("DeepDecisionOrchestrator")

WORKER_PORT = 8888
SOCKET_TIMEOUT = 5.0
BUFFER_SIZE = 4096

# Model execution times (ms)
l_CNN = {
    0: {160: 10.0, 320: 20.0, 480: 30.0},     # Remote Big-YOLO on Edge
    1: {160: 200.0, 320: 600.0, 480: 1100.0}, # Local Tiny-YOLO
    2: {160: 600.0, 320: 2400.0, 480: 4500.0},          # Local Big-YOLO
    3: {160: 5.0, 320: 10.0, 480: 15.0}       # Remote Big-YOLO on Cloud
}

# Base Accuracies
A_base = {
    0: {160: 0.60, 320: 0.80, 480: 0.90},     # Edge
    1: {160: 0.30, 320: 0.45, 480: 0.55},     # Local Tiny
    2: {160: 0.55, 320: 0.75, 480: 0.85},     # Local Big
    3: {160: 0.65, 320: 0.85, 480: 0.95}      # Cloud
}

# Energy consumption per frame (mJ)
b_1 = lambda p: 3727.0 * (l_CNN[1][p] / 1000.0)
b_2 = lambda p: 5000.0 * (l_CNN[2][p] / 1000.0)

b_i = {1: b_1, 2: b_2}

# Thread safety lock for task_records
records_lock = threading.Lock()
task_records = []

# Clusters definition
EDEFAULT_SLAVES = [
    {"id": 1, "ip": "127.0.0.1", "port": 8888, "name": "slavenode1"},
    {"id": 2, "ip": "127.0.0.1", "port": 8889, "name": "slavenode2"},
    # Simulate slightly longer reach to cloud nodes (id 3 and 4)
    {"id": 3, "ip": "127.0.0.1", "port": 8890, "name": "slavenode3"},
    {"id": 4, "ip": "127.0.0.1", "port": 8891, "name": "slavenode4"}
]

EDGE_CLUSTER = [EDEFAULT_SLAVES[0], EDEFAULT_SLAVES[1]]
CLOUD_CLUSTER = [EDEFAULT_SLAVES[2], EDEFAULT_SLAVES[3]]

edge_rr_idx = 0
cloud_rr_idx = 0
rr_lock = threading.Lock()

# Global start time reference
t_start = 0.0

def get_bandwidth_profile(t: float) -> float:
    """Returns bandwidth in kbps based on elapsed time."""
    if t < 20.0:
        return 100.0
    elif t < 60.0:
        return 500.0
    else:
        return 1000.0

def solve_algorithm1_one_type(model_type: int, B: float, L: float, B_limit: float, C: float, c: float, F: float, A_target: float, alpha: float) -> tuple:
    """Solves Algorithm 1 for a specific remote model type (0 for Edge, 3 for Cloud)."""
    best_remote = None
    best_remote_val = -float('inf')
    f_remote = 30.0
    
    for p in [160, 320, 480]:
        for r in [100.0, 500.0, 1000.0]:
            if r > B or c * r > C:
                continue
            
            tx_delay_ms = (r / B) * 1000.0
            l_0 = l_CNN[model_type][p] + tx_delay_ms + L * 1000.0
            
            if (l_CNN[model_type][p] / 1000.0) > (1.0 / f_remote):
                continue
            
            base_acc = A_base[model_type][p]
            bitrate_disc = 1.0 if r >= 1000.0 else (0.85 if r >= 500.0 else 0.65)
            staleness_disc = math.exp(-0.002 * max(0.0, l_0 - 100.0))
            acc = base_acc * bitrate_disc * staleness_disc
            
            if acc < A_target or f_remote < F:
                continue
                
            val = f_remote + alpha * acc
            if val > best_remote_val:
                best_remote_val = val
                best_remote = (model_type, p, r, f_remote, acc, l_0)
                
    return best_remote, best_remote_val

def solve_algorithm1(B_edge: float, L_edge: float, B_cloud: float, L_cloud: float, B_limit: float, C: float, c: float, F: float, A_target: float, alpha: float) -> tuple:
    """Solves Algorithm 1 comparing Local, Edge, and Cloud cluster options."""
    # 1. Edge offload evaluation
    best_edge, best_edge_val = solve_algorithm1_one_type(0, B_edge, L_edge, B_limit, C, c, F, A_target, alpha)
    
    # 2. Cloud offload evaluation
    best_cloud, best_cloud_val = solve_algorithm1_one_type(3, B_cloud, L_cloud, B_limit, C, c, F, A_target, alpha)
    
    # 3. Local models evaluation
    best_local = None
    best_local_val = -float('inf')
    for i in [1, 2]:
        for p in [160, 320, 480]:
            f_max_battery = B_limit / b_i[i](p)
            f_max_compute = 1.0 / (l_CNN[i][p] / 1000.0)
            f_feasible = min(30.0, min(f_max_compute, f_max_battery))
            
            acc = A_base[i][p]
            if acc < A_target or f_feasible < F:
                continue
                
            val = f_feasible + alpha * acc
            if val > best_local_val:
                best_local_val = val
                best_local = (i, p, 0.0, f_feasible, acc, l_CNN[i][p])
                
    # Compare choices
    choices = []
    if best_edge is not None:
        choices.append((best_edge_val, best_edge))
    if best_cloud is not None:
        choices.append((best_cloud_val, best_cloud))
    if best_local is not None:
        choices.append((best_local_val, best_local))
        
    if choices:
        choices.sort(key=lambda x: x[0], reverse=True)
        return choices[0][1]
    else:
        f_feasible = min(30.0, min(1.0 / (l_CNN[1][160]/1000.0), B_limit / b_i[1](160)))
        return (1, 160, 0.0, f_feasible, A_base[1][160], l_CNN[1][160])

def recv_all(sock: socket.socket, length: int) -> bytes:
    data = b""
    while len(data) < length:
        packet = sock.recv(length - len(data))
        if not packet:
            raise ConnectionError("Socket closed prematurely")
        data += packet
    return data

def run_single_task(task_id: int, target_worker: Dict[str, Any], decision_tuple: tuple, arrival_time: float) -> None:
    """Executes task locally or offloads it, measuring latency and logging metrics."""
    global t_start
    i, p, r, f, acc, expected_latency = decision_tuple
    
    # Power mapping
    if i in [0, 3]:
        power_mw = 2060.0
    elif i == 1:
        power_mw = 3727.0
    else:
        power_mw = 5000.0
        
    if i in [1, 2]:
        # Execute locally sequentially
        exec_start = time.perf_counter()
        sleep_sec = l_CNN[i][p] / 1000.0
        time.sleep(sleep_sec)
        exec_ms = (time.perf_counter() - exec_start) * 1000.0
        
        # RTT = Completion Time - Arrival Time (includes local queuing)
        total_rtt_ms = (time.perf_counter() - t_start - arrival_time) * 1000.0
        status = "LOCAL"
    else:
        # Remote execution over network socket
        client_socket = None
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(2.0)
            client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            client_socket.connect((target_worker["ip"], target_worker["port"]))
            
            # Payload size in bytes = r / (8 * f)
            payload_bytes = int((r * 1000.0) / (8.0 * f))
            request = {
                "task_id": task_id,
                "sleep_time_ms": l_CNN[i][p]
            }
            
            base_encoded_len = len(json.dumps(request).encode("utf-8"))
            padding_len = payload_bytes - base_encoded_len - 15
            if padding_len > 0:
                request["dummy"] = "x" * padding_len
                
            req_data = json.dumps(request).encode("utf-8")
            req_header = f"{len(req_data):010d}".encode("utf-8")
            client_socket.sendall(req_header + req_data)
            
            resp_header = recv_all(client_socket, 10)
            resp_len = int(resp_header.decode("utf-8"))
            response_bytes = recv_all(client_socket, resp_len)
            
            if response_bytes:
                response = json.loads(response_bytes.decode("utf-8"))
                exec_ms = response.get("exec_time_ms", 0.0)
                
                # RTT = Completion Time - Arrival Time (includes network queuing)
                total_rtt_ms = (time.perf_counter() - t_start - arrival_time) * 1000.0
                status = "OFFLOADED_EDGE" if i == 0 else "OFFLOADED_CLOUD"
            else:
                total_rtt_ms = expected_latency
                exec_ms = l_CNN[i][p]
                status = "FAILED"
        except Exception as err:
            logger.debug("Failed remote task %d on %s: %s", task_id, target_worker["name"] if target_worker else "None", err)
            total_rtt_ms = expected_latency
            exec_ms = l_CNN[i][p]
            status = "FAILED"
        finally:
            if client_socket:
                client_socket.close()
            
    # Log metrics thread-safely
    with records_lock:
        task_records.append({
            "task_id": task_id,
            "model_type": "cloud" if i == 3 else ("edge" if i == 0 else ("tiny_yolo" if i == 1 else "big_yolo")),
            "resolution": p,
            "bitrate": r,
            "frame_rate": f,
            "response_time_ms": total_rtt_ms,
            "exec_time_s": exec_ms / 1000.0,
            "energy_mw": power_mw,
            "accuracy": acc,
            "status": status,
            "arrival_time_s": arrival_time
        })

def main() -> None:
    global task_records
    global edge_rr_idx
    global cloud_rr_idx
    global t_start
    task_records = []
    
    if len(sys.argv) < 4:
        print("Usage: python3 deepdecision_orchestrator.py [duration_s] [mode: deepdecision|local|remote|strawman] [csv_out_path]")
        sys.exit(1)
        
    duration = float(sys.argv[1])
    mode = sys.argv[2]
    csv_out_path = sys.argv[3]
    
    logger.info("Initializing DeepDecision Cluster Orchestrator in mode: %s, duration: %.1fs", mode, duration)
    
    t_start = time.perf_counter()
    task_id = 0
    next_arrival = 0.0
    
    # Constraint thresholds
    B_limit = 3000.0  # mW
    C_budget = 1.0
    c_cost = 0.0
    F_min = 2.0
    A_min = 0.3
    alpha_val = 15.0
    
    # Executors: Single worker for local queue, multithreaded for concurrent remote sockets
    local_executor = ThreadPoolExecutor(max_workers=1)
    remote_executor = ThreadPoolExecutor(max_workers=100)
    
    try:
        while True:
            elapsed = time.perf_counter() - t_start
            if elapsed >= duration:
                break
                
            B_edge = get_bandwidth_profile(elapsed)
            L_edge = 0.010 # 10 ms Edge delay
            B_cloud = 5000.0 # 5 Mbps Cloud bandwidth
            L_cloud = 0.080 # 80 ms Cloud delay
            
            if mode == "deepdecision":
                decision = solve_algorithm1(B_edge, L_edge, B_cloud, L_cloud, B_limit, C_budget, c_cost, F_min, A_min, alpha_val)
            elif mode == "local":
                f_feasible = min(30.0, min(1.0 / (l_CNN[1][160]/1000.0), B_limit / b_i[1](160)))
                decision = (1, 160, 0.0, f_feasible, A_base[1][160], l_CNN[1][160])
            elif mode == "remote":
                # Prefers Edge, falls back to Cloud if Edge is highly degraded
                if B_edge < 200.0:
                    tx_delay = (500.0 / B_cloud) * 1000.0
                    l_0 = l_CNN[3][320] + tx_delay + L_cloud * 1000.0
                    acc = A_base[3][320] * 0.85 * math.exp(-0.002 * max(0.0, l_0 - 100.0))
                    decision = (3, 320, 500.0, 15.0, acc, l_0)
                else:
                    tx_delay = (500.0 / B_edge) * 1000.0
                    l_0 = l_CNN[0][320] + tx_delay + L_edge * 1000.0
                    acc = A_base[0][320] * 0.85 * math.exp(-0.002 * max(0.0, l_0 - 100.0))
                    decision = (0, 320, 500.0, 15.0, acc, l_0)
            elif mode == "strawman":
                # Prefers Cloud due to high constant bandwidth
                tx_delay = (500.0 / B_cloud) * 1000.0
                l_0 = l_CNN[3][320] + tx_delay + L_cloud * 1000.0
                acc_remote = A_base[3][320] * 0.85 * math.exp(-0.002 * max(0.0, l_0 - 100.0))
                decision = (3, 320, 500.0, 15.0, acc_remote, l_0)
                    
            i, p, r, f, acc, expected_latency = decision
            
            if elapsed >= next_arrival:
                target_worker = None
                if i == 0:
                    with rr_lock:
                        target_worker = EDGE_CLUSTER[edge_rr_idx % len(EDGE_CLUSTER)]
                        edge_rr_idx += 1
                elif i == 3:
                    with rr_lock:
                        target_worker = CLOUD_CLUSTER[cloud_rr_idx % len(CLOUD_CLUSTER)]
                        cloud_rr_idx += 1
                
                # Submit to corresponding executor
                if i in [1, 2]:
                    local_executor.submit(run_single_task, task_id, target_worker, decision, elapsed)
                else:
                    remote_executor.submit(run_single_task, task_id, target_worker, decision, elapsed)
                    
                interval = random.expovariate(f)
                next_arrival += interval
                task_id += 1
                
            time.sleep(0.001)
    finally:
        print("--> Joining ThreadPoolExecutor threads...")
        local_executor.shutdown(wait=True)
        remote_executor.shutdown(wait=True)
        
    try:
        with open(csv_out_path, "w", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=[
                "task_id", "model_type", "resolution", "bitrate", "frame_rate",
                "response_time_ms", "exec_time_s", "energy_mw", "accuracy", "status", "arrival_time_s"
            ])
            writer.writeheader()
            writer.writerows(task_records)
        logger.info("Experiment successfully completed. Logged %d tasks to %s", len(task_records), csv_out_path)
    except Exception as err:
        logger.error("Failed to write task records to CSV: %s", err)

if __name__ == "__main__":
    main()
