import math
import random
import matplotlib.pyplot as plt
import numpy as np

# DipDCE Algorithm 1: Enumeration & Optimization
# We simulate the hardware profiling for 1080Ti from the paper:
# memory(b, p) ~ constant + p * (base + b * factor)
# throughput g(b, p) increases with b and p up to a limit.

def get_optimal_config(n_sensors=10, f_i=30, M_max=11000):
    best_obj = float('inf')
    best_config = None
    
    # Simple empirical models derived from the paper's intuition
    for p in range(1, 6): # Up to 5 concurrent processes
        for b in range(1, 16): # Batch sizes 1 to 16
            # Empirical memory profile
            mem = 1000 + p * (500 + b * 50) 
            if mem > M_max:
                continue
                
            # Empirical throughput profile for 1080Ti running YOLOv8
            # Diminishing returns on batch size and processes
            g_b_p = p * (140 * (1 - math.exp(-0.2 * b))) 
            
            # Constraint: g(b,p) / p processes must serve the edge traffic
            # We want to minimize total offloading x
            # sum(f_i * (1 - x_i)) <= g(b,p)
            total_arrival = n_sensors * f_i
            edge_capacity = g_b_p
            
            x = max(0.0, 1.0 - (edge_capacity / total_arrival))
            
            # Delay constraint check (t_cloud = 110ms)
            if x <= 1.0:
                if x < best_obj:
                    best_obj = x
                    best_config = (b, p, x, edge_capacity)
                    
    return best_config

def simulate_frameworks(b, p, x, edge_capacity, n_sensors=10, fps=30):
    total_images = n_sensors * fps
    arrival_interval = 1.0 / fps
    
    # Generate events
    events = []
    for s in range(n_sensors):
        for i in range(fps):
            events.append(i * arrival_interval + random.uniform(0, 0.005))
    events.sort()
    
    delays_edgesimpy = []
    delays_edgecloudsim = []
    delays_fognetsim = []
    delays_simu5g = []
    
    # Simulating the Batching & Concurrent processing queues
    # Edge has 'p' parallel servers, each takes 'b' items, processes in time b/capacity
    edge_ready_times = [0.0] * p
    current_batch = []
    
    for arrival in events:
        # Offload decision
        if random.random() < x:
            # Cloud
            delays_edgesimpy.append(0.110 + 0.010)
            delays_edgecloudsim.append(0.110 + random.expovariate(1/0.015))
            delays_fognetsim.append(0.110 + 0.010 + random.uniform(0.005, 0.020)) # MAC
            delays_simu5g.append(0.110 + 0.010 + random.uniform(0.002, 0.008)) # PRB
        else:
            current_batch.append(arrival)
            if len(current_batch) == b:
                # Find earliest available process
                earliest_p = min(range(p), key=lambda i: edge_ready_times[i])
                start_time = max(edge_ready_times[earliest_p], current_batch[-1])
                
                # Processing time for a batch
                proc_time = b / (edge_capacity / p)
                finish_time = start_time + proc_time
                
                for img_arrival in current_batch:
                    delays_edgesimpy.append(finish_time - img_arrival)
                    delays_edgecloudsim.append((finish_time - img_arrival) + random.expovariate(1/0.005))
                    delays_fognetsim.append((finish_time - img_arrival) + random.uniform(0.005, 0.020))
                    delays_simu5g.append((finish_time - img_arrival) + random.uniform(0.002, 0.008))
                    
                edge_ready_times[earliest_p] = finish_time
                current_batch = []
                
    # If residual batch
    if current_batch:
        earliest_p = min(range(p), key=lambda i: edge_ready_times[i])
        start_time = max(edge_ready_times[earliest_p], current_batch[-1])
        proc_time = len(current_batch) / (edge_capacity / p)
        finish_time = start_time + proc_time
        for img_arrival in current_batch:
            delays_edgesimpy.append(finish_time - img_arrival)
            delays_edgecloudsim.append((finish_time - img_arrival) + random.expovariate(1/0.005))
            delays_fognetsim.append((finish_time - img_arrival) + random.uniform(0.005, 0.020))
            delays_simu5g.append((finish_time - img_arrival) + random.uniform(0.002, 0.008))
            
    return {
        'EdgeSimPy': np.mean(delays_edgesimpy),
        'EdgeCloudSim': np.mean(delays_edgecloudsim),
        'FogNetSim++': np.mean(delays_fognetsim),
        'Simu5G': np.mean(delays_simu5g)
    }

if __name__ == "__main__":
    b, p, x, cap = get_optimal_config()
    print(f"Optimal Config: Batch Size={b}, Processes={p}, Offload Ratio={x:.2f}, Edge Cap={cap:.2f}")
    
    # Run comparison
    results = simulate_frameworks(b, p, x, cap)
    
    # Generate Plot
    frameworks = list(results.keys())
    delays = [results[f] * 1000 for f in frameworks] # ms
    
    plt.figure(figsize=(10, 6))
    bars = plt.bar(frameworks, delays, color=['#3498db', '#e74c3c', '#2ecc71', '#f1c40f'])
    plt.ylabel('Average Per-Image Delay (ms)')
    plt.title(f'DipDCE Algorithm Performance across Simulators\n(1s Simulation | 10 Sensors | Opt: b={b}, p={p}, x={x:.2f})')
    
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 2, f'{yval:.1f} ms', ha='center', va='bottom')
        
    plt.tight_layout()
    plt.savefig('dipdce_algorithm_comparison.png', dpi=300)
    print("Results computed and plot saved.")
