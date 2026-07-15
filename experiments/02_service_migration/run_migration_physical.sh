#!/usr/bin/env bash
set -e

BASE_DIR="/proj/oasees-PG0/NS3-Edge/NSEdge-Validation"
PYTHON_VENV="/proj/oasees-PG0/net4hpc/.venv/bin/python3"
WORKER_PATH="$BASE_DIR/validation/worker.py"
ORCH_PATH="$BASE_DIR/validation/migration_orchestrator.py"
RECV_PATH="$BASE_DIR/validation/state_receiver.py"
OUT_CSV="$BASE_DIR/experiments/02_service_migration/results/physical_tasks.csv"

echo "--> Cleaning up old processes"
pkill -f worker.py || true
pkill -f migration_orchestrator.py || true
pkill -f state_receiver.py || true
sudo tc qdisc del dev lo root >/dev/null 2>&1 || true

echo "--> Starting Workers"
nohup $PYTHON_VENV $WORKER_PATH 8888 > /tmp/worker_8888.log 2>&1 &
nohup $PYTHON_VENV $WORKER_PATH 8889 > /tmp/worker_8889.log 2>&1 &
nohup $PYTHON_VENV $RECV_PATH 9999 > /tmp/recv_9999.log 2>&1 &

sleep 2

echo "--> Running Migration Orchestrator"
# 30 seconds duration, 2 Hz arrival rate, 150 matrix size (150*150*8 = 180000 bytes)
$PYTHON_VENV $ORCH_PATH 30.0 2.0 150 $OUT_CSV

echo "--> Shutting down Workers"
pkill -f worker.py || true
pkill -f state_receiver.py || true
sudo tc qdisc del dev lo root >/dev/null 2>&1 || true

echo "--> Physical Migration Run Complete. Data saved to $OUT_CSV"
