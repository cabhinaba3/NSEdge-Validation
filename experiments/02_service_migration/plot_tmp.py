import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

def read_csv(filename):
    arrival = []
    response = []
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            arrival.append(float(row['arrival_time_s']))
            response.append(float(row['response_time_ms']))
    return arrival, response

def plot_migration(ns3_file, phys_file, title, output_file):
    ns3_arr, ns3_resp = read_csv(ns3_file)
    phys_arr, phys_resp = read_csv(phys_file)

    plt.figure(figsize=(10, 6))
    
    # Plot NS-3
    plt.plot(ns3_arr, ns3_resp, marker='o', label='NS-3 Simulation', alpha=0.8)
    
    # Plot Physical
    plt.plot(phys_arr, phys_resp, marker='x', label='Physical Emulation', alpha=0.8)

    plt.axvline(x=25, color='r', linestyle='--', label='Migration Triggered (Node1 -> Node2)')
    
    plt.title(title)
    plt.xlabel('Experiment Time (s)')
    plt.ylabel('End-to-End Response Time (ms)')
    plt.grid(True)
    plt.legend()
    plt.ylim(0, 1000)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.close()

if __name__ == "__main__":
    base_dir = "results"
    out_dir = "results"
    
    # Ethernet Plot
    plot_migration(f"{base_dir}/ns3_tasks.csv", f"{base_dir}/physical_tasks.csv", 
                   "Service Migration Response Time (Ethernet / P2P)", 
                   f"{out_dir}/migration_response_time.png")
                   
    # 5G Plot
    plot_migration(f"{base_dir}/ns3_tasks_5g.csv", f"{base_dir}/physical_tasks.csv", 
                   "Service Migration Response Time (5G)", 
                   f"{out_dir}/migration_response_time_5g.png")
                   
    print("Plots generated.")
