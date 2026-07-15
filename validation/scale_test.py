import subprocess
import json

nodes = [2, 4, 8, 16, 32]
results = {}

for n in nodes:
    print(f"Running simulation with {n} edges and {n} clouds...")
    cmd = f"ssh n079-16 \"cd /proj/oasees-PG0/NS3-Edge/ns-3 && ./ns3 run 'ns3-deepdecision-cluster-scenario --duration=30.0 --mode=deepdecision --num_edges={n} --num_clouds={n}' > /tmp/sim_{n}.log 2>&1\""
    subprocess.run(cmd, shell=True)
    # Get the number of completed tasks from the log
    cmd = f"ssh n079-16 \"grep 'completed task' /tmp/sim_{n}.log | wc -l\""
    completed = int(subprocess.check_output(cmd, shell=True).strip())
    # Average latency? We can parse it.
    cmd = f"ssh n079-16 \"grep 'completed task' /tmp/sim_{n}.log | awk '{{print \\$7}}' | sed 's/latency=+//g' | sed 's/ms//g' | awk '{{sum+=\\$1}} END {{print sum/NR}}'\""
    try:
        avg_lat = float(subprocess.check_output(cmd, shell=True).strip())
    except:
        avg_lat = 0.0
    results[n] = {"completed": completed, "avg_exec_latency_ms": avg_lat}
    print(f"Nodes: {n}, Completed: {completed}, Avg Exec Latency: {avg_lat:.2f} ms")

with open("/home/cohitherewer/scale_results.json", "w") as f:
    json.dump(results, f, indent=4)
