import json
import matplotlib.pyplot as plt
import numpy as np
import os
import seaborn as sns

plt.style.use('seaborn-v0_8-whitegrid')
sns.set_context("paper", font_scale=1.5)
plt.rcParams['font.family'] = 'serif'

os.makedirs('journal_plots', exist_ok=True)

with open('results/extensive_validation.json', 'r') as f:
    data = json.load(f)

with open('results/fl_results.json', 'r') as f:
    fl_data = json.load(f)

# ----------------------------------------------------
# 1. Network Realism - RTT
# ----------------------------------------------------
scenarios = ['baseline', 'loss', 'jitter']
labels = ['Baseline', 'Packet Loss (3%)', 'Jitter (5ms)']
phys_rtt = [data['network_realism']['phys'][s]['avg_rtt'] for s in scenarios]
sim_rtt = [data['network_realism']['sim'][s]['avg_rtt'] for s in scenarios]
phys_err = [data['network_realism']['phys'][s].get('std_rtt', 0) for s in scenarios]
sim_err = [data['network_realism']['sim'][s].get('std_rtt', 0) for s in scenarios]

x = np.arange(len(labels))
width = 0.35

fig, ax = plt.subplots(figsize=(8, 6))
rects1 = ax.bar(x - width/2, phys_rtt, width, yerr=phys_err, label='Physical Cluster', color='#3498db', edgecolor='black', capsize=5)
rects2 = ax.bar(x + width/2, sim_rtt, width, yerr=sim_err, label='NSEdge Simulation', color='#e74c3c', edgecolor='black', capsize=5)

ax.set_ylabel('Response Time (ms)', fontweight='bold')
ax.set_title('Network Realism Validation: Response Time', fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.legend()
fig.tight_layout()
plt.savefig('journal_plots/1_network_realism_rtt.png', dpi=300)
plt.close()

# ----------------------------------------------------
# 2. Network Realism - Reliability
# ----------------------------------------------------
phys_rel = [data['network_realism']['phys'][s]['reliability'] for s in scenarios]
sim_rel = [data['network_realism']['sim'][s]['reliability'] for s in scenarios]

fig, ax = plt.subplots(figsize=(8, 6))
rects1 = ax.bar(x - width/2, phys_rel, width, label='Physical Cluster', color='#2ecc71', edgecolor='black')
rects2 = ax.bar(x + width/2, sim_rel, width, label='NSEdge Simulation', color='#f39c12', edgecolor='black')

ax.set_ylabel('Task Reliability (%)', fontweight='bold')
ax.set_title('Network Realism Validation: Reliability', fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.set_ylim(0, 110)
ax.legend()
fig.tight_layout()
plt.savefig('journal_plots/2_network_realism_reliability.png', dpi=300)
plt.close()

# ----------------------------------------------------
# 3. Federated Learning Scalability
# ----------------------------------------------------
phys_nodes = fl_data['fl_scalability']['phys_nodes']
sim_nodes = fl_data['fl_scalability']['sim_nodes']
phys_rtt = fl_data['fl_scalability']['phys_rtt']
sim_rtt = fl_data['fl_scalability']['sim_rtt']

fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(phys_nodes, phys_rtt, 'bo-', markersize=8, linewidth=2, label='Physical Edge (Local Workers)')
ax.plot(sim_nodes, sim_rtt, 'rs--', markersize=8, linewidth=2, label='NSEdge Scaled Simulation')

ax.set_xlabel('Number of Active Edge Nodes', fontweight='bold')
ax.set_ylabel('Average Response Time (ms)', fontweight='bold')
ax.set_title('Federated Learning Workload Scalability', fontweight='bold')
ax.set_xscale('log')
ax.set_xticks([1, 2, 4, 10, 100, 1000])
ax.get_xaxis().set_major_formatter(plt.ScalarFormatter())
ax.grid(True, which="both", ls="--", alpha=0.5)
ax.legend()
fig.tight_layout()
plt.savefig('journal_plots/3_fl_scalability.png', dpi=300)
plt.close()

# ----------------------------------------------------
# 4. Smart City Scalability
# ----------------------------------------------------
sc_phys_nodes = fl_data['smart_city_scalability']['phys_nodes']
sc_sim_nodes = fl_data['smart_city_scalability']['sim_nodes']
sc_phys_rtt = fl_data['smart_city_scalability']['phys_rtt']
sc_sim_rtt = fl_data['smart_city_scalability']['sim_rtt']

fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(sc_phys_nodes, sc_phys_rtt, 'go-', markersize=8, linewidth=2, label='Physical Edge (Local Workers)')
ax.plot(sc_sim_nodes, sc_sim_rtt, 'm^--', markersize=8, linewidth=2, label='NSEdge Scaled Simulation')

ax.set_xlabel('Number of Active Edge Nodes', fontweight='bold')
ax.set_ylabel('Average Response Time (ms)', fontweight='bold')
ax.set_title('Smart City Traffic Scalability', fontweight='bold')
ax.set_xscale('log')
ax.set_xticks([1, 2, 4, 10, 100, 1000])
ax.get_xaxis().set_major_formatter(plt.ScalarFormatter())
ax.grid(True, which="both", ls="--", alpha=0.5)
ax.legend()
fig.tight_layout()
plt.savefig('journal_plots/4_sc_scalability.png', dpi=300)
plt.close()

# ----------------------------------------------------
# 5. Confidence Intervals (Validation Tightness)
# ----------------------------------------------------
mean_phys = data['ci']['phys_mean']
err_phys = data['ci']['phys_ci']
mean_sim = data['ci']['sim_mean']
err_sim = data['ci']['sim_ci']

fig, ax = plt.subplots(figsize=(6, 6))
x_ci = [0, 1]
means = [mean_phys, mean_sim]
errs = [err_phys, err_sim]
labels_ci = ['Physical (95% CI)', 'Simulation (95% CI)']
colors = ['#8e44ad', '#2980b9']

for i in range(2):
    ax.bar(x_ci[i], means[i], yerr=errs[i], width=0.5, color=colors[i], edgecolor='black', capsize=10, alpha=0.8)

ax.set_ylabel('Response Time (ms)', fontweight='bold')
ax.set_title('Calibration Confidence (Base Scenario)', fontweight='bold')
ax.set_xticks(x_ci)
ax.set_xticklabels(labels_ci)
fig.tight_layout()
plt.savefig('journal_plots/5_confidence_intervals.png', dpi=300)
plt.close()

print("Journal plots generated in journal_plots/")
