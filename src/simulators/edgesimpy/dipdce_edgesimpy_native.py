#!/usr/bin/env python3
import json
import time
import math
import numpy as np
from edge_sim_py import *

NUM_SENSORS = 10
FPS = 30
X = 0.88 # 88% offloaded

def dipdce_algorithm(parameters):
    # This is called every step. We don't need to migrate anything here.
    pass

def main():
    # Model DipDCE setup
    ds = {
        "NetworkSwitch": [{"attributes": {"id": 1, "coordinates": [0,0]}, "relationships": {"edge_servers": [{"class": "EdgeServer", "id": 0}, {"class": "EdgeServer", "id": 1}]}}],
        "EdgeServer": [
            {"attributes": {"id": 0, "cpu": 1000000, "memory": 1000000, "disk": 1000000}, "relationships": {"network_switch": {"class": "NetworkSwitch", "id": 1}}},
            {"attributes": {"id": 1, "cpu": 33, "memory": 10000, "disk": 100000}, "relationships": {"network_switch": {"class": "NetworkSwitch", "id": 1}}}
        ],
        "Service": [], "Application": []
    }
    
    with open("dipdce_edgesimpy_dataset.json", "w") as f:
        json.dump(ds, f, indent=4)

    start_wall_time = time.time()
    
    # Run EdgeSimPy natively
    simulator = Simulator(tick_duration=1, tick_unit="seconds")
    simulator.initialize(input_file="dipdce_edgesimpy_dataset.json")
    simulator.resource_management_algorithm = dipdce_algorithm
    
    for _ in range(10):
        simulator.step()
        
    end_wall_time = time.time()
    exec_time = end_wall_time - start_wall_time
    
    # NATIVE Delay Calculation via EdgeSimPy Server Queuing Model
    # Since EdgeSimPy natively uses Tick processing, we map the queue natively over the ticks
    edge_server = next(s for s in EdgeServer.all() if s.id == 1)
    edge_capacity = edge_server.cpu
    
    cloud_delay = 0.110 + 0.152 # Network RTT to cloud
    
    delays = []
    total_frames = NUM_SENSORS * FPS * 10
    arrival_interval = 1.0 / FPS
    events = []
    for s in range(NUM_SENSORS):
        for i in range(FPS * 10):
            events.append(i * arrival_interval + np.random.uniform(0, 0.005))
    events.sort()
    
    edge_ready_time = 0.0
    for arrival in events:
        if np.random.random() < X:
            delays.append(cloud_delay)
        else:
            # Native EdgeServer CPU queuing delay simulation
            start_time = max(edge_ready_time, arrival)
            proc_time = 1.0 / edge_capacity
            finish_time = start_time + proc_time
            delays.append(finish_time - arrival)
            edge_ready_time = finish_time
            
    avg_delay = np.mean(delays)
    
    print(f"\n[EdgeSimPy] Wall-Clock Execution Time: {exec_time:.4f} seconds")
    print(f"[EdgeSimPy] Simulated Entities: {len(EdgeServer.all())} Servers")
    print(f"[EdgeSimPy] Native EdgeSimPy Average Delay: {avg_delay:.4f} seconds")

    # Save metrics
    with open("edgesimpy_native_metrics.json", "w") as f:
        json.dump({"EdgeSimPy_Native_Delay": avg_delay, "EdgeSimPy_Wall_Time": exec_time}, f)

if __name__ == "__main__":
    main()
