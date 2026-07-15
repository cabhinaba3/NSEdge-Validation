#!/usr/bin/env python3
"""Modular Task Orchestrator for Edge Computing Validation.

Generates compute tasks according to a Poisson arrival process,
orchestrates their scheduling across active slavenodes,
and logs execution and round-trip time metrics to a CSV file.
"""

import csv
import json
import logging
import math
import random
import socket
import sys
import multiprocessing
import time
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Orchestrator")

WORKER_PORT = 8888
SOCKET_TIMEOUT = 5.0
BUFFER_SIZE = 4096

# Cluster slavenode definition mapping
DEFAULT_SLAVES = [
    {"id": 1, "ip": "127.0.0.1", "port": 8888, "name": "slavenode1"},
    {"id": 2, "ip": "127.0.0.1", "port": 8889, "name": "slavenode2"},
    {"id": 3, "ip": "127.0.0.1", "port": 8890, "name": "slavenode3"},
    {"id": 4, "ip": "127.0.0.1", "port": 8891, "name": "slavenode4"}
]

def recv_all(sock: socket.socket, length: int) -> bytes:
    data = b""
    while len(data) < length:
        packet = sock.recv(length - len(data))
        if not packet:
            raise ConnectionError("Socket closed prematurely")
        data += packet
    return data

def run_single_task(task_id: int, slave: Dict[str, Any], workload_size: int, arrival_time: float, queue: Any) -> None:
    """Connects to a remote worker node, submits the task, and measures latency.

    Args:
        task_id: Unique task identifier.
        slave: Candidate slavenode mapping dictionary.
        workload_size: Compute workload size (matrix dimension).
        arrival_time: Absolute generation timestamp of the task in seconds.
        queue: Multiprocessing Queue to log metrics back to the parent.
    """
    t_net_start = time.perf_counter()
    try:
        # Create TCP connection to the worker node
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(2.0) # wait up to 2.0s for socket connect
        client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        client_socket.connect((slave["ip"], slave["port"]))
        
        # Calculate matching payload size in bytes (workload_size * workload_size * 8)
        payload_bytes = workload_size * workload_size * 8
        request = {
            "task_id": task_id,
            "workload_size": workload_size
        }
        
        # Generate dummy data padding so network transmission matches simulated size
        base_encoded_len = len(json.dumps(request).encode("utf-8"))
        padding_len = payload_bytes - base_encoded_len - 15  # Account for key-value formatting
        if padding_len > 0:
            request["dummy"] = "x" * padding_len

        req_data = json.dumps(request).encode("utf-8")
        req_header = f"{len(req_data):010d}".encode("utf-8")
        client_socket.sendall(req_header + req_data)
        
        # Read worker response using length prefix
        resp_header = recv_all(client_socket, 10)
        resp_len = int(resp_header.decode("utf-8"))
        response_bytes = recv_all(client_socket, resp_len)
        
        if response_bytes:
            response = json.loads(response_bytes.decode("utf-8"))
            exec_ms = response.get("exec_time_ms", 0.0)
            
            t_net_end = time.perf_counter()
            total_rtt_ms = (t_net_end - t_net_start) * 1000.0
            
            queue.put({
                "task_id": task_id,
                "slave_id": slave["id"],
                "slave_name": slave["name"],
                "workload_size": workload_size,
                "arrival_time_s": arrival_time,
                "completion_time_s": arrival_time + (total_rtt_ms / 1000.0),
                "exec_time_s": exec_ms / 1000.0,
                "response_time_ms": total_rtt_ms
            })
        client_socket.close()
    except Exception as err:
        logger.error("Failed to run task %d on %s: %s", task_id, slave["name"], err)

def main() -> None:
    """Main task generation loop."""
    if len(sys.argv) < 5:
        print("Usage: python3 orchestrator.py [duration_s] [lambda_hz] [workload_size] [policy: rr|random] [num_slaves] [csv_out_path]")
        sys.exit(1)

    duration = float(sys.argv[1])
    lambda_hz = float(sys.argv[2])
    workload_size = int(sys.argv[3])
    policy = sys.argv[4]
    
    num_slaves = int(sys.argv[5]) if len(sys.argv) >= 6 else len(DEFAULT_SLAVES)
    csv_out_path = sys.argv[6] if len(sys.argv) >= 7 else "physical_tasks.csv"
    
    active_slaves = DEFAULT_SLAVES[:num_slaves]
    logger.info("Initializing task execution engine: Duration = %.1f s, Lambda = %.1f Hz, Slaves = %d", duration, lambda_hz, len(active_slaves))
    
    records_queue = multiprocessing.Queue()
    processes: List[multiprocessing.Process] = []
    t_start = time.perf_counter()
    task_id = 0
    next_arrival = 0.0
    rr_idx = 0
    
    while True:
        elapsed = time.perf_counter() - t_start
        if elapsed >= duration:
            break
            
        # Draw next interval following an exponential distribution for Poisson process
        if elapsed >= next_arrival:
            # Select target slave based on scheduling policy
            if policy == "rr":
                target_slave = active_slaves[rr_idx % len(active_slaves)]
                rr_idx += 1
            else:
                target_slave = random.choice(active_slaves)

            logger.debug("Dispatching task %d to %s", task_id, target_slave["name"])
            
            # Spawn worker client process
            process = multiprocessing.Process(
                target=run_single_task,
                args=(task_id, target_slave, workload_size, elapsed, records_queue)
            )
            process.start()
            processes.append(process)
            
            # Calculate next arrival time
            interval = random.expovariate(lambda_hz)
            next_arrival += interval
            task_id += 1

        # Small sleep to prevent busy waiting
        time.sleep(0.001)

    # Wait for all process operations to terminate
    for process in processes:
        process.join(timeout=7.0)

    # Read records from Queue
    task_records = []
    import queue
    while True:
        try:
            task_records.append(records_queue.get(timeout=1.0))
        except queue.Empty:
            break

    # Write records to CSV file
    try:
        with open(csv_out_path, "w", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=[
                "task_id", "slave_id", "slave_name", "workload_size",
                "arrival_time_s", "completion_time_s", "exec_time_s", "response_time_ms"
            ])
            writer.writeheader()
            writer.writerows(task_records)
        logger.info("Experiment successfully completed. Logged %d tasks to %s", len(task_records), csv_out_path)
    except Exception as err:
        logger.error("Failed to write task records to CSV: %s", err)

if __name__ == "__main__":
    main()
