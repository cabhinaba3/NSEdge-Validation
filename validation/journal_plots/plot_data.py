import os
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

DATA_DIR = "/home/cohitherewer/src/journal_plots/data"
OUTPUT_DIR = "/home/cohitherewer/.gemini/antigravity-cli/brain/be78b449-13ea-47ad-aa1e-a49d81791c16/plots"

os.makedirs(OUTPUT_DIR, exist_ok=True)

cluster_sizes = [2, 4, 8, 16, 32, 64]
modes = ["deepdecision", "local", "remote", "strawman"]

def parse_csv(filepath):
    records = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
    return records

# 1. Scalability of DeepDecision (Avg RTT & Completion Rate vs Nodes)
avg_rtts = []
completion_rates = []
avg_energy = []

for size in cluster_sizes:
    tasks_file = os.path.join(DATA_DIR, f"tasks_deepdecision_{size}.csv")
    nodes_file = os.path.join(DATA_DIR, f"nodes_deepdecision_{size}.csv")
    
    if os.path.exists(tasks_file):
        tasks = parse_csv(tasks_file)
        # Average response time for met SLAs
        rtts = [float(t['response_time_ms']) for t in tasks if t['met_sla'] == '1']
        if len(rtts) > 0:
            avg_rtt = sum(rtts) / len(rtts)
        else:
            avg_rtt = 0
        avg_rtts.append(avg_rtt)
        
        # Completion Rate
        total_tasks = len(tasks)
        completed = len(rtts)
        rate = (completed / total_tasks * 100) if total_tasks > 0 else 0
        completion_rates.append(rate)
    else:
        avg_rtts.append(0)
        completion_rates.append(0)
        
    if os.path.exists(nodes_file):
        nodes = parse_csv(nodes_file)
        # Avg energy per EDGE node
        edges = [float(n['final_energy_j']) for n in nodes if n['tier'] == 'EDGE']
        if len(edges) > 0:
            avg_eng = sum(edges) / len(edges)
        else:
            avg_eng = 0
        avg_energy.append(avg_eng)
    else:
        avg_energy.append(0)

# Plot 1: Scalability RTT
plt.figure(figsize=(8, 5))
plt.plot(cluster_sizes, avg_rtts, marker='o', linestyle='-', color='b', linewidth=2, markersize=8)
plt.title("DeepDecision Scalability: Average RTT vs Cluster Size", fontsize=14)
plt.xlabel("Cluster Size (Number of Edges & Clouds)", fontsize=12)
plt.ylabel("Average Response Time (ms)", fontsize=12)
plt.grid(True, linestyle='--', alpha=0.7)
plt.xticks(cluster_sizes)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "scalability_rtt.png"), dpi=300)
plt.close()

# Plot 2: Scalability Completion Rate
plt.figure(figsize=(8, 5))
plt.plot(cluster_sizes, completion_rates, marker='s', linestyle='-', color='g', linewidth=2, markersize=8)
plt.title("DeepDecision Scalability: SLA Compliance Rate", fontsize=14)
plt.xlabel("Cluster Size (Number of Edges & Clouds)", fontsize=12)
plt.ylabel("Completion Rate (%)", fontsize=12)
plt.grid(True, linestyle='--', alpha=0.7)
plt.ylim(0, 105)
plt.xticks(cluster_sizes)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "scalability_completion_rate.png"), dpi=300)
plt.close()

# Plot 3: Comparison across Modes at Size 16
mode_rtts = []
mode_energy = []
mode_labels = []

for mode in modes:
    tasks_file = os.path.join(DATA_DIR, f"tasks_{mode}_16.csv")
    nodes_file = os.path.join(DATA_DIR, f"nodes_{mode}_16.csv")
    if os.path.exists(tasks_file):
        tasks = parse_csv(tasks_file)
        rtts = [float(t['response_time_ms']) for t in tasks if t['met_sla'] == '1']
        mode_rtts.append(sum(rtts) / len(rtts) if len(rtts) > 0 else 0)
        mode_labels.append(mode.capitalize())
        
    if os.path.exists(nodes_file):
        nodes = parse_csv(nodes_file)
        edges = [float(n['final_energy_j']) for n in nodes if n['tier'] == 'EDGE']
        mode_energy.append(sum(edges) / len(edges) if len(edges) > 0 else 0)

if mode_labels:
    # Subplot for RTT and Energy comparison
    fig, ax1 = plt.subplots(figsize=(10, 6))
    
    color = 'tab:blue'
    ax1.set_xlabel('Offloading Policy (Cluster Size = 16)', fontsize=12)
    ax1.set_ylabel('Average RTT (ms)', color=color, fontsize=12)
    ax1.bar([x - 0.2 for x in range(len(mode_labels))], mode_rtts, width=0.4, color=color, label='Avg RTT')
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.set_xticks(range(len(mode_labels)))
    ax1.set_xticklabels(mode_labels)
    
    ax2 = ax1.twinx()  
    color = 'tab:red'
    ax2.set_ylabel('Average Edge Node Energy (Joules)', color=color, fontsize=12)  
    ax2.bar([x + 0.2 for x in range(len(mode_labels))], mode_energy, width=0.4, color=color, label='Energy (J)')
    ax2.tick_params(axis='y', labelcolor=color)
    
    fig.tight_layout()  
    plt.title("Performance Comparison of Offloading Policies", fontsize=14)
    plt.savefig(os.path.join(OUTPUT_DIR, "mode_comparison.png"), dpi=300)
    plt.close()

print("Plots generated successfully in", OUTPUT_DIR)
