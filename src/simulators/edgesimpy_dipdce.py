import random
import time

def simulate_dipdce_edgesimpy(pr=0.48, num_sensors=10, fps=30, t_cloud=0.110, mu_edge=140):
    # Discrete-event simulation logic based on the DipDCE formulas (M/D/1 equivalent)
    total_images = num_sensors * fps
    arrival_interval = 1.0 / fps
    
    events = []
    for s in range(num_sensors):
        for i in range(fps):
            arrival_time = i * arrival_interval + random.uniform(0, 0.005)
            events.append(arrival_time)
            
    events.sort()
    
    delays = []
    edge_ready_time = 0
    
    for arrival in events:
        if random.random() < pr:
            # Cloud
            delay = t_cloud + 0.010
            delays.append(delay)
        else:
            # Edge
            if edge_ready_time < arrival:
                edge_ready_time = arrival
            processing_time = 1.0 / mu_edge
            start_process = edge_ready_time
            finish_process = start_process + processing_time
            
            delay = finish_process - arrival
            delays.append(delay)
            edge_ready_time = finish_process
            
    avg_delay = sum(delays) / len(delays)
    return avg_delay

if __name__ == "__main__":
    for pr in [0.1, 0.48, 0.9]:
        delay = simulate_dipdce_edgesimpy(pr=pr)
        print(f"EdgeSimPy PR={pr} Avg Delay: {delay:.4f} s")
