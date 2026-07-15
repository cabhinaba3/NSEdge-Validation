#!/usr/bin/env python3
import csv
import json
import logging
import random
import socket
import sys
import multiprocessing
import queue
import threading
import time
from typing import Dict, List, Any
import subprocess

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("MigrationOrchestrator")

WORKER_PORT_1 = 8888
WORKER_PORT_2 = 8889
STATE_PORT = 9999
STATE_SIZE_BYTES = 1024 * 1024 * 1024  # 1 GB

def setup_tc():
    subprocess.run("sudo tc qdisc del dev lo root >/dev/null 2>&1", shell=True)
    subprocess.run("sudo tc qdisc add dev lo root handle 1: htb", shell=True, check=True)
    subprocess.run("sudo tc class add dev lo parent 1: classid 1:1 htb rate 10Gbps", shell=True, check=True)
    
    subprocess.run("sudo tc class add dev lo parent 1:1 classid 1:10 htb rate 1Gbps", shell=True, check=True)
    subprocess.run("sudo tc class add dev lo parent 1:1 classid 1:20 htb rate 1Gbps", shell=True, check=True)
    
    subprocess.run("sudo tc qdisc add dev lo parent 1:10 handle 10: netem delay 0ms", shell=True, check=True)
    subprocess.run("sudo tc qdisc add dev lo parent 1:20 handle 20: netem delay 0ms", shell=True, check=True)
    
    subprocess.run("sudo tc filter add dev lo protocol ip parent 1:0 u32 match ip dport 8888 0xffff flowid 1:10", shell=True, check=True)
    subprocess.run("sudo tc filter add dev lo protocol ip parent 1:0 u32 match ip sport 8888 0xffff flowid 1:10", shell=True, check=True)
    
    subprocess.run("sudo tc filter add dev lo protocol ip parent 1:0 u32 match ip dport 8889 0xffff flowid 1:20", shell=True, check=True)
    subprocess.run("sudo tc filter add dev lo protocol ip parent 1:0 u32 match ip sport 8889 0xffff flowid 1:20", shell=True, check=True)
    
    subprocess.run("sudo tc filter add dev lo protocol ip parent 1:0 u32 match ip dport 9999 0xffff flowid 1:20", shell=True, check=True)
    subprocess.run("sudo tc filter add dev lo protocol ip parent 1:0 u32 match ip sport 9999 0xffff flowid 1:20", shell=True, check=True)

def apply_tc_filters(delay1_ms: float, delay2_ms: float):
    subprocess.run(f"sudo tc qdisc change dev lo parent 1:10 handle 10: netem delay {delay1_ms:.2f}ms", shell=True, check=True)
    subprocess.run(f"sudo tc qdisc change dev lo parent 1:20 handle 20: netem delay {delay2_ms:.2f}ms", shell=True, check=True)

def recv_all(sock: socket.socket, length: int) -> bytes:
    data = b""
    while len(data) < length:
        packet = sock.recv(length - len(data))
        if not packet:
            raise ConnectionError("Socket closed prematurely")
        data += packet
    return data

def run_single_task(task_id: int, slave: Dict[str, Any], workload_size: int, arrival_time: float, queue: Any) -> None:
    t_net_start = time.perf_counter()
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(2.0)
        client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        client_socket.connect((slave["ip"], slave["port"]))
        
        payload_bytes = workload_size * workload_size * 8
        request = {"task_id": task_id, "workload_size": workload_size}
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

def mobility_manager(start_time: float, duration: float, migration_trigger_event: threading.Event):
    """Simulates user moving away from Node 1 (delay increases) and towards Node 2 (delay decreases)."""
    logger.info("Mobility manager started. Calling initial apply_tc_filters...")
    apply_tc_filters(10.0, 50.0)
    logger.info("Initial apply_tc_filters returned!")
    
    migrated = False
    while True:
        elapsed = time.perf_counter() - start_time
        if elapsed > duration:
            break
            
        # Linear shift from t=0 to t=30
        progress = min(1.0, elapsed / duration)
        d1 = 10.0 + progress * 40.0 # 10 -> 50
        d2 = 50.0 - progress * 40.0 # 50 -> 10
        
        logger.info("Calling apply_tc_filters...")
        apply_tc_filters(d1, d2)
        logger.info("apply_tc_filters returned!")
        
        # Follow Me at the Edge trigger: when d1 > d2 + 10ms
        logger.info(f"Mobility loop: elapsed={elapsed:.2f}, progress={progress:.2f}, d1={d1:.2f}, d2={d2:.2f}")
        if d1 > d2 + 10.0 and not migrated:
            logger.warning("Mobility trigger: Node 1 delay (%.1f) > Node 2 (%.1f) + 10ms. TRIGGERING MIGRATION!", d1, d2)
            migration_trigger_event.set()
            migrated = True
            
        time.sleep(2.0)
    subprocess.run("sudo tc qdisc del dev lo root >/dev/null 2>&1", shell=True)

def migrate_state():
    logger.info("Starting 1GB state transfer to Node 2...")
    t_start = time.perf_counter()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(("127.0.0.1", STATE_PORT))
        chunk = b"X" * (1024 * 1024) # 1MB chunk
        sent = 0
        while sent < STATE_SIZE_BYTES:
            sock.sendall(chunk)
            sent += len(chunk)
        sock.close()
        t_end = time.perf_counter()
        logger.info("State transfer complete in %.2fs (%.2f Mbps).", (t_end - t_start), (STATE_SIZE_BYTES * 8) / (1e6 * (t_end - t_start)))
        return True
    except Exception as e:
        logger.error("State transfer failed: %s", e)
        return False

def main():
    if len(sys.argv) < 5:
        print("Usage: python3 migration_orchestrator.py [duration_s] [lambda_hz] [workload_size] [csv_out_path]")
        sys.exit(1)

    duration = float(sys.argv[1])
    lambda_hz = float(sys.argv[2])
    workload_size = int(sys.argv[3])
    csv_out_path = sys.argv[4]
    
    slave1 = {"id": 1, "ip": "127.0.0.1", "port": WORKER_PORT_1, "name": "Node1"}
    slave2 = {"id": 2, "ip": "127.0.0.1", "port": WORKER_PORT_2, "name": "Node2"}
    
    current_slave = slave1
    
    records_queue = queue.Queue()
    processes: List[threading.Thread] = []
    
    t_start = time.perf_counter()
    migration_trigger_event = threading.Event()
    
    setup_tc()
    
    mob_thread = threading.Thread(target=mobility_manager, args=(t_start, duration, migration_trigger_event), daemon=True)
    mob_thread.start()
    
    task_id = 0
    next_arrival = 0.0
    migration_in_progress = False
    

    while True:
        elapsed = time.perf_counter() - t_start
        if elapsed >= duration:
            break
            
        if migration_trigger_event.is_set() and not migration_in_progress and current_slave == slave1:
            migration_in_progress = True
            # Start pre-copy state transfer in background
            def on_migration_complete(success):
                nonlocal current_slave, migration_in_progress
                if success:
                    logger.info("=== PRE-COPY COMPLETE: SWITCHING TRAFFIC TO NODE 2 ===")
                    current_slave = slave2
                migration_in_progress = False
                
            def migration_worker():
                res = migrate_state()
                on_migration_complete(res)
            
            threading.Thread(target=migration_worker, daemon=True).start()
            
        if elapsed >= next_arrival:
            # Dispatch
            process = threading.Thread(
                target=run_single_task,
                args=(task_id, current_slave, workload_size, elapsed, records_queue)
            )
            process.start()
            processes.append(process)
            
            interval = random.expovariate(lambda_hz)
            next_arrival += interval
            task_id += 1

        time.sleep(0.005)

    for p in processes:
        p.join(timeout=2.0)

    task_records = []
    while True:
        try:
            task_records.append(records_queue.get_nowait())
        except queue.Empty:
            break

    try:
        with open(csv_out_path, "w", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=[
                "task_id", "slave_id", "slave_name", "workload_size",
                "arrival_time_s", "completion_time_s", "exec_time_s", "response_time_ms"
            ])
            writer.writeheader()
            writer.writerows(task_records)
        logger.info("Logged %d tasks to %s", len(task_records), csv_out_path)
    except Exception as err:
        logger.error("Failed to write task records to CSV: %s", err)

if __name__ == "__main__":
    main()
