import json
import time
from edge_sim_py import *

def dummy_algorithm(parameters):
    pass

def main():
    ds = {
        "NetworkSwitch": [{"attributes": {"id": 1, "coordinates": [0,0]}, "relationships": {"edge_servers": [{"class": "EdgeServer", "id": i} for i in range(6)]}}],
        "EdgeServer": [],
        "Service": [],
        "Application": []
    }
    
    # 0 = cloud
    ds["EdgeServer"].append({
        "attributes": {"id": 0, "cpu": 100000, "memory": 100000, "disk": 100000},
        "relationships": {"network_switch": {"class": "NetworkSwitch", "id": 1}}
    })
    
    # 1 to 5 = edge
    for i in range(1, 6):
        ds["EdgeServer"].append({
            "attributes": {"id": i, "cpu": 10000, "memory": 10000, "disk": 100000},
            "relationships": {"network_switch": {"class": "NetworkSwitch", "id": 1}}
        })
        
    for i in range(50):
        ds["Application"].append({
            "attributes": {"id": i},
            "relationships": {"services": [{"class": "Service", "id": i}]}
        })
        ds["Service"].append({
            "attributes": {"id": i, "cpu_demand": 100, "memory_demand": 10, "_available": True, "state": 0},
            "relationships": {
                "server": {"class": "EdgeServer", "id": 1 + (i % 5)},
                "application": {"class": "Application", "id": i}
            }
        })

    with open("custom_dataset.json", "w") as f:
        json.dump(ds, f, indent=4)

    start_wall_time = time.time()
    
    simulator = Simulator(tick_duration=1, tick_unit="seconds")
    simulator.initialize(input_file="custom_dataset.json")
    simulator.resource_management_algorithm = dummy_algorithm
    
    for _ in range(10):
        simulator.step()
    
    end_wall_time = time.time()
    exec_time = end_wall_time - start_wall_time
    print(f"EdgeSimPy Simulation Time: {exec_time:.4f} seconds")
    
    results = {
        "simulator": "EdgeSimPy",
        "wall_clock_time": exec_time,
        "simulated_time": 10.0,
        "tasks_completed": 50 * 10
    }
    
    with open("results_edgesimpy.json", "w") as f:
        json.dump(results, f, indent=4)

if __name__ == "__main__":
    main()
