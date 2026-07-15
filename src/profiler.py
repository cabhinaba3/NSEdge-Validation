#!/usr/bin/env python3
"""Unified Profiler for Edge Node Network and Compute Capacity.

Measures matrix multiplication CPU execution times and link bandwidth/RTT to
generate configurations for calibrating the simulator.
"""

import argparse
import json
import socket
import sys
import time
import numpy as np

WORKER_PORT = 8888
TEST_MATRIX_SIZES = [50, 100, 150, 200, 250]
PROFILES_OUT = "configs/profiles_validation.json"

def profile_cpu(iterations: int = 20) -> None:
    """Measures execution latency of matrix multiplications across various sizes."""
    print("==================================================")
    print("          CPU Workload Profiling Module")
    print("==================================================")
    
    profiles = {}
    for size in TEST_MATRIX_SIZES:
        times = []
        for _ in range(iterations):
            t_start = time.perf_counter()
            mat_a = np.random.rand(size, size)
            mat_b = np.random.rand(size, size)
            _ = np.dot(mat_a, mat_b)
            t_end = time.perf_counter()
            times.append((t_end - t_start) * 1000.0)
            
        mean_t = np.mean(times)
        std_t = np.std(times)
        print(f"Matrix {size}x{size} | Mean: {mean_t:.3f} ms | StdDev: {std_t:.3f} ms")
        
        # Save profiles mapped by task sizes in bytes
        bytes_size = size * size * 8  # 8 bytes per double float
        profiles[str(bytes_size)] = {
            "workload_class": "GENERIC_COMPUTE",
            "mean_exec_time_ms": mean_t,
            "std_dev_exec_time_ms": std_t
        }

    profile_data = {
        "intel_i5": {
            "tiers": ["EDGE", "DEVICE"],
            "profiles": profiles
        }
    }
    
    try:
        with open(PROFILES_OUT, "w") as f:
            json.dump(profile_data, f, indent=4)
        print(f"\nSaved hardware CPU profile to {PROFILES_OUT}")
    except Exception as e:
        print(f"Error saving profile: {e}", file=sys.stderr)

def profile_network(target_ip: str) -> None:
    """Measures TCP link throughput and round-trip time (RTT)."""
    print("==================================================")
    print("        Network Link Profiling Module")
    print("==================================================")
    print(f"Target node IP: {target_ip}")
    
    # 1. Measure RTT (Latency test with tiny packets)
    rtts = []
    print("Measuring link round-trip time (latency)...")
    for _ in range(50):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2.0)
            t_start = time.perf_counter()
            s.connect((target_ip, WORKER_PORT))
            t_end = time.perf_counter()
            rtts.append((t_end - t_start) * 1000.0)
            s.close()
        except Exception as e:
            print(f"Error connecting: {e}", file=sys.stderr)
            time.sleep(0.1)

    if not rtts:
        print("Failed to gather latency metrics.", file=sys.stderr)
        return

    avg_rtt = np.mean(rtts)
    one_way_delay = avg_rtt / 2.0
    print(f"RTT: Mean = {avg_rtt:.3f} ms | StdDev = {np.std(rtts):.3f} ms")
    print(f"One-way delay estimate: {one_way_delay:.3f} ms")

    # 2. Measure Throughput (5MB data transfer sink)
    print("\nMeasuring link bandwidth (throughput)...")
    request = {
        "task_id": 9999,
        "sleep_time_ms": 0.0,
        "dummy": "X" * (5 * 1024 * 1024)
    }
    import json
    payload = json.dumps(request).encode("utf-8")
    req_header = f"{len(payload):010d}".encode("utf-8")
    full_payload = req_header + payload
    throughputs = []
    
    for _ in range(5):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10.0)
            s.connect((target_ip, WORKER_PORT))
            
            t_start = time.perf_counter()
            s.sendall(full_payload)
            # Read small ACK
            _ = s.recv(1024)
            t_end = time.perf_counter()
            
            duration = t_end - t_start
            speed_mbps = (len(payload) * 8) / (duration * 1e6)
            throughputs.append(speed_mbps)
            s.close()
        except Exception as e:
            print(f"Error during bandwidth run: {e}", file=sys.stderr)
            
    if throughputs:
        print(f"Bandwidth: Mean = {np.mean(throughputs):.1f} Mbps | Max = {np.max(throughputs):.1f} Mbps")
    else:
        print("Failed to gather bandwidth metrics.", file=sys.stderr)

def main() -> None:
    parser = argparse.ArgumentParser(description="NSEdge Profiling Module")
    subparsers = parser.add_subparsers(dest="mode", required=True)
    
    # CPU Profiler Subcommand
    cpu_parser = subparsers.add_parser("cpu", help="Profile CPU compute performance")
    cpu_parser.add_argument("--iter", type=int, default=20, help="Iterations per matrix size")
    
    # Network Profiler Subcommand
    net_parser = subparsers.add_parser("network", help="Profile network bandwidth and RTT")
    net_parser.add_argument("--ip", type=str, required=True, help="IP address of the target worker node")
    
    args = parser.parse_args()
    if args.mode == "cpu":
        profile_cpu(args.iter)
    elif args.mode == "network":
        profile_network(args.ip)

if __name__ == "__main__":
    main()
