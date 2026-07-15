#!/bin/bash
cd /proj/oasees-PG0/NS3-Edge/NSEdge-Validation/validation

sudo sysctl -w net.ipv4.tcp_no_metrics_save=1 >/dev/null 2>&1
sudo ip tcp_metrics flush >/dev/null 2>&1

/proj/oasees-PG0/net4hpc/.venv/bin/python3 worker.py --port 8888 > worker1.log 2>&1 &
/proj/oasees-PG0/net4hpc/.venv/bin/python3 worker.py --port 8889 > worker2.log 2>&1 &
/proj/oasees-PG0/net4hpc/.venv/bin/python3 state_receiver.py --port 9999 > state.log 2>&1 &
sleep 2
sudo tc qdisc del dev lo root >/dev/null 2>&1
/proj/oasees-PG0/net4hpc/.venv/bin/python3 migration_orchestrator.py 30 5.0 150 tasks.csv
sudo killall python3

