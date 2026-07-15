import nbformat as nbf
import os

nb = nbf.v4.new_notebook()

md_intro = """# Physical DipDCE Algorithm Validation

This notebook visualizes the performance of DipDCE execution natively across EdgeSimPy, EdgeCloudSim, Simu5G, and our native NS-3 integration (NSEdge).
It also renders a red solid line representing the **true physical average delay** calculated by executing the DipDCE workload on the real local cluster."""

code_plot = """import json
import matplotlib.pyplot as plt
import os

# Load JSON results
results_file = "../results/dipdce_native_metrics_final.json"
with open(results_file, 'r') as f:
    results = json.load(f)

# Extract Baseline vs Frameworks
baseline_val = results.pop('DipDCE Physical (Real Baseline)', 0.0)
frameworks = list(results.keys())
delays = [results[f] for f in frameworks]

# Plot
plt.figure(figsize=(10, 6))
colors = ['#3498db', '#e74c3c', '#f1c40f', '#9b59b6']
bars = plt.bar(frameworks, delays, color=colors)
plt.ylabel('Average Per-Image Delay (ms)')
plt.title('DipDCE Native Implementations vs Real Physical Baseline')

# Add the Physical Baseline Line
plt.axhline(y=baseline_val, color='r', linestyle='-', linewidth=2.5, label=f'Physical Baseline ({baseline_val:.1f} ms)')
plt.legend()

# Add text labels
for bar in bars:
    plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, f'{bar.get_height():.1f}', ha='center')

plt.tight_layout()
os.makedirs('../docs', exist_ok=True)
plt.savefig('../docs/dipdce_baseline_plot.png', dpi=300)
plt.show()
"""

nb['cells'] = [nbf.v4.new_markdown_cell(md_intro), nbf.v4.new_code_cell(code_plot)]

os.makedirs('/proj/oasees-PG0/NS3-Edge/NSEdge-Validation/notebooks', exist_ok=True)
with open('/proj/oasees-PG0/NS3-Edge/NSEdge-Validation/notebooks/plot_dipdce_baseline.ipynb', 'w') as f:
    nbf.write(nb, f)

print("Notebook generated successfully!")
