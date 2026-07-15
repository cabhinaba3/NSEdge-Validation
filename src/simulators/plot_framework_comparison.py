import matplotlib.pyplot as plt
import numpy as np

frameworks = ['EdgeSimPy', 'EdgeCloudSim', 'FogNetSim++', 'MEC Simulator', 'DeepDecision']
exec_time_for_10s = [0.002, 0.218, 45.3, 52.1, 38.5] # execution time for 10s of simulated time
per_image_delay = [0.150, 0.165, 0.280, 0.275, 0.290] # per-packet delay

x = np.arange(len(frameworks))

plt.style.use('ggplot')

# Plot 1: Execution Time
fig, ax = plt.subplots(figsize=(10, 6))
ax.bar(x, exec_time_for_10s, color=['#3498db', '#e74c3c', '#2ecc71', '#f1c40f', '#9b59b6'])
ax.set_ylabel('Execution Time (seconds) - Lower is Better')
ax.set_title('Simulation Scalability: Wall-clock time to simulate 10s of runtime (50 Users, CNN)')
ax.set_xticks(x)
ax.set_xticklabels(frameworks)
ax.set_yscale('log')
for i, v in enumerate(exec_time_for_10s):
    ax.text(i, v + (v*0.1), f'{v}s', ha='center', va='bottom')
plt.savefig('framework_exec_time.png', bbox_inches='tight')

# Plot 2: Per-Image Delay Accuracy
fig2, ax2 = plt.subplots(figsize=(10, 6))
ax2.bar(x, per_image_delay, color=['#3498db', '#e74c3c', '#2ecc71', '#f1c40f', '#9b59b6'])
ax2.set_ylabel('Avg Per-Image Delay (seconds)')
ax2.set_title('Packet-Level Accuracy: Simulated Delay for CNN Inference Offloading')
ax2.set_xticks(x)
ax2.set_xticklabels(frameworks)
ax2.axhline(y=0.285, color='r', linestyle='--', label='Physical Testbed Baseline (0.285s)')
ax2.legend()
for i, v in enumerate(per_image_delay):
    ax2.text(i, v + 0.005, f'{v}s', ha='center', va='bottom')
plt.savefig('framework_packet_delay.png', bbox_inches='tight')

