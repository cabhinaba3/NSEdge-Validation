import subprocess
import os

NS3_DIR = "/proj/oasees-PG0/NS3-Edge/ns-3"
REMOTE_HOST = "n079-16"
DATA_DIR = "/home/cohitherewer/src/journal_plots/data"

cluster_sizes = [2, 4, 8, 16, 32, 64]
modes = ["deepdecision", "local", "remote", "strawman"]
duration = 30.0

def run_experiment(mode, size):
    print(f"Running {mode} with size {size}...")
    cmd = f"ssh {REMOTE_HOST} \"cd {NS3_DIR} && ./ns3 run 'ns3-deepdecision-cluster-scenario --duration={duration} --mode={mode} --num_edges={size} --num_clouds={size}' > /dev/null 2>&1\""
    subprocess.run(cmd, shell=True, check=True)
    
    tasks_local = os.path.join(DATA_DIR, f"tasks_{mode}_{size}.csv")
    nodes_local = os.path.join(DATA_DIR, f"nodes_{mode}_{size}.csv")
    
    cmd_scp1 = f"scp {REMOTE_HOST}:{NS3_DIR}/results-deepdecision/tasks.csv {tasks_local}"
    cmd_scp2 = f"scp {REMOTE_HOST}:{NS3_DIR}/results-deepdecision/nodes.csv {nodes_local}"
    
    subprocess.run(cmd_scp1, shell=True, check=True)
    subprocess.run(cmd_scp2, shell=True, check=True)

if __name__ == "__main__":
    for size in cluster_sizes:
        run_experiment("deepdecision", size)
        
    for mode in modes:
        if mode != "deepdecision":
            run_experiment(mode, 16)
