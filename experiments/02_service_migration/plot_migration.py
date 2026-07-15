#!/usr/bin/env python3
import pandas as pd
import matplotlib.pyplot as plt
import os
import sys

def main():
    if len(sys.argv) < 3:
        print("Usage: plot_migration.py <physical_csv> <ns3_csv> <out_dir>")
        sys.exit(1)
        
    phys_csv = sys.argv[1]
    ns3_csv = sys.argv[2]
    out_dir = sys.argv[3]
    
    os.makedirs(out_dir, exist_ok=True)
    
    phys_df = pd.read_csv(phys_csv)
    ns3_df = pd.read_csv(ns3_csv)
    
    # Calculate response time
    # For NS-3, response_time_ms is (completion_time_s - arrival_time_s) * 1000
    if "response_time_ms" not in ns3_df.columns and "completion_time_s" in ns3_df.columns:
        ns3_df["response_time_ms"] = (ns3_df["completion_time_s"] - ns3_df["arrival_time_s"]) * 1000.0

    plt.figure(figsize=(10, 5))
    plt.plot(phys_df["arrival_time_s"], phys_df["response_time_ms"], 'o-', label="Physical Testbed", markersize=4, alpha=0.7)
    plt.plot(ns3_df["arrival_time_s"], ns3_df["response_time_ms"], 'x-', label="NSEdge (Sim)", markersize=4, alpha=0.7)
    
    plt.axvline(x=18.75, color='r', linestyle='--', label="Migration Triggered")
    plt.axvline(x=26.75, color='g', linestyle='--', label="Migration Completed")
    
    plt.xlabel("Simulation Time (s)")
    plt.ylabel("Response Time (ms)")
    plt.title("Service Migration: Follow Me at the Edge")
    plt.grid(True)
    plt.legend()
    plt.ylim(0, max(phys_df["response_time_ms"].max(), ns3_df["response_time_ms"].max()) * 1.1)
    
    out_path = os.path.join(out_dir, "migration_response_time.png")
    plt.savefig(out_path, dpi=300)
    print(f"Plot saved to {out_path}")

if __name__ == "__main__":
    main()
