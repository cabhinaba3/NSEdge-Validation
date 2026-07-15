#!/usr/bin/env python3
import json
import logging
import socket
import sys
import time
import random
import threading
import queue
import argparse
import concurrent.futures

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("PhysicalWorker")

task_queue = queue.Queue()

def perform_compute_workload(size: int) -> float:
    mat_a = [[random.random() for _ in range(size)] for _ in range(size)]
    mat_b = [[random.random() for _ in range(size)] for _ in range(size)]
    mat_c = [[0.0 for _ in range(size)] for _ in range(size)]

    t_start = time.perf_counter()
    for i in range(size):
        for j in range(size):
            s = 0.0
            for k in range(size):
                s += mat_a[i][k] * mat_b[k][j]
            mat_c[i][j] = s
    t_end = time.perf_counter()
    return (t_end - t_start) * 1000.0

def recv_all(sock: socket.socket, length: int) -> bytes:
    data = b""
    while len(data) < length:
        packet = sock.recv(length - len(data))
        if not packet:
            raise ConnectionError("Socket closed prematurely")
        data += packet
    return data

def task_processor(batch_size: int, num_processes: int):
    logger.info("Task processor started with Batch Size = %d, Processes = %d", batch_size, num_processes)
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=max(1, num_processes)) as executor:
        while True:
            batch = []
            try:
                # Wait for at least one item
                item = task_queue.get(timeout=1.0)
                if item is None:
                    break
                batch.append(item)
                
                # Greedily gather up to batch_size
                while len(batch) < batch_size:
                    try:
                        item = task_queue.get_nowait()
                        if item is None:
                            break
                        batch.append(item)
                    except queue.Empty:
                        break
            except queue.Empty:
                continue
                
            if not batch:
                continue
                
            logger.info("Processing batch of size %d", len(batch))
            
            # Submit batch to process pool
            futures = []
            for client_socket, client_address, request in batch:
                workload_size = request.get("workload_size", 0)
                sleep_time_ms = request.get("sleep_time_ms", 0.0)
                
                if sleep_time_ms > 0:
                    future = executor.submit(time.sleep, sleep_time_ms / 1000.0)
                else:
                    future = executor.submit(perform_compute_workload, workload_size)
                futures.append((future, client_socket, request, sleep_time_ms))
                
            # Collect results and reply
            for future, client_socket, request, sleep_time_ms in futures:
                try:
                    res = future.result()
                    exec_ms = sleep_time_ms if sleep_time_ms > 0 else res
                    response = {
                        "task_id": request.get("task_id", -1),
                        "exec_time_ms": exec_ms,
                        "status": "COMPLETED"
                    }
                    resp_data = json.dumps(response).encode("utf-8")
                    resp_header = f"{len(resp_data):010d}".encode("utf-8")
                    client_socket.sendall(resp_header + resp_data)
                except Exception as err:
                    logger.error("Error executing task: %s", err)
                finally:
                    try:
                        client_socket.close()
                    except:
                        pass
                    task_queue.task_done()

def handle_client_connection(client_socket: socket.socket, client_address: tuple) -> None:
    try:
        header = recv_all(client_socket, 10)
        payload_len = int(header.decode("utf-8"))
        data = recv_all(client_socket, payload_len)
        if not data:
            client_socket.close()
            return

        request = json.loads(data.decode("utf-8"))
        task_queue.put((client_socket, client_address, request))
    except Exception as err:
        logger.error("Error receiving data from client %s: %s", client_address[0], err)
        try:
            client_socket.close()
        except:
            pass

def main() -> None:
    parser = argparse.ArgumentParser(description="Physical Edge Worker Node")
    parser.add_argument("--port", type=int, default=8899, help="Port to listen on")
    parser.add_argument("--batch-size", type=int, default=1, help="Number of requests to batch")
    parser.add_argument("--processes", type=int, default=1, help="Number of concurrent worker processes")
    
    # We must support the legacy calling format `python3 worker.py 8899` without flags
    # So we parse positional port manually if args don't start with --
    args, unknown = parser.parse_known_args()
    
    port = args.port
    if unknown and len(unknown) == 1 and unknown[0].isdigit():
        port = int(unknown[0])
        
    processor_thread = threading.Thread(target=task_processor, args=(args.batch_size, args.processes), daemon=True)
    processor_thread.start()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server_socket.bind(("0.0.0.0", port))
        server_socket.listen(512) 
        logger.info("Worker daemon listening on port %d...", port)

        while True:
            client_socket, client_address = server_socket.accept()
            client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            conn_thread = threading.Thread(target=handle_client_connection, args=(client_socket, client_address), daemon=True)
            conn_thread.start()
    except KeyboardInterrupt:
        logger.info("Shutting down.")
    finally:
        server_socket.close()
        task_queue.put(None)

if __name__ == "__main__":
    main()
