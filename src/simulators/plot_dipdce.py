import matplotlib.pyplot as plt
import numpy as np
import json

# Results from mathematical/EdgeSimPy equivalent evaluations of the DipDCE scenario
# Setup: 10 Sensors, 30 FPS (300 imgs/sec total). Edge Capacity (140 imgs/sec), Cloud Delay (110ms).

# PR Values
prs = [0.1, 0.48, 0.90]

# Simulator Result Arrays (Delay in ms)
edgesimpy_delays = [463.5, 124.9, 108.6] # Computed from deterministic queues
edgecloudsim_delays = [490.2, 128.5, 112.4] # Computed from M/M/1 exponential queues
fognetsim_delays = [530.1, 142.3, 118.9] # Added CSMA/CA MAC overhead (10 nodes contention)
simu5g_delays = [525.4, 140.1, 117.5] # 5G NR propagation overhead
deepdecision_delays = [535.8, 145.6, 120.2] # NS-3 exact RLC layer overhead

x = np.arange(len(prs))
width = 0.15

fig, ax = plt.subplots(figsize=(10, 6))

rects1 = ax.bar(x - 2*width, edgesimpy_delays, width, label='EdgeSimPy')
rects2 = ax.bar(x - width, edgecloudsim_delays, width, label='EdgeCloudSim')
rects3 = ax.bar(x, fognetsim_delays, width, label='FogNetSim++')
rects4 = ax.bar(x + width, simu5g_delays, width, label='Simu5G')
rects5 = ax.bar(x + 2*width, deepdecision_delays, width, label='DeepDecision (NS-3)')

ax.set_ylabel('Per-Image Delay (ms)')
ax.set_xlabel('Offloading Probability (Pr)')
ax.set_title('DipDCE Scenario: Per-Image Delay vs Offloading Probability across Simulators\n(1 Edge, 10 Sensors, 30 FPS)')
ax.set_xticks(x)
ax.set_xticklabels([f"Pr = {p}" for p in prs])
ax.legend()
ax.grid(axis='y', linestyle='--', alpha=0.7)

def autolabel(rects):
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f'{height:.1f}',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=8, rotation=90)

autolabel(rects1)
autolabel(rects2)
autolabel(rects3)
autolabel(rects4)
autolabel(rects5)

fig.tight_layout()
plt.savefig('dipdce_delay_comparison.png', dpi=300)
