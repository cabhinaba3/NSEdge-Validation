#!/usr/bin/env python3
"""Physical worker daemon for edge node resource orchestration validation.

Listens for TCP task offloading requests from the master orchestrator,
performs matrix multiplication compute workload of specified intensity sequentially,
and returns execution metrics back to the master.
"""

import json
import logging
import socket
import sys
import time
import random
import threading
import queue

# Configure logging to standard output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("PhysicalWorker")

if len(sys.argv) > 1:
    WORKER_PORT = int(sys.argv[1])
else:
    WORKER_PORT = 8888
BUFFER_SIZE = 4096

task_queue = queue.Queue()

def perform_compute_workload(size: int) -> float:
    """Executes a square matrix multiplication of shape (size, size) as workload.

    Args:
        size: Dimension of the square matrices to multiply.

    Returns:
        Execution latency in milliseconds.
    """
    # Generate random square matrices
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

def task_processor():
    """Worker thread that processes tasks sequentially from the queue."""
    logger.info("Task processor thread started.")
    while True:
        try:
            task_item = task_queue.get()
            if task_item is None:
                task_queue.task_done()
                break
            
            client_socket, client_address, request = task_item
            task_id = request.get("task_id", -1)
            workload_size = request.get("workload_size", 0)
            sleep_time_ms = request.get("sleep_time_ms", 0.0)

            logger.info("Starting execution of Task ID %d, workload size %d on CPU queue", task_id, workload_size)
            try:
                # Execute workload and measure precise execution latency
                if sleep_time_ms > 0:
                    time.sleep(sleep_time_ms / 1000.0)
                    exec_ms = sleep_time_ms
                else:
                    exec_ms = perform_compute_workload(workload_size)

                # Prepare and send response
                response = {
                    "task_id": task_id,
                    "exec_time_ms": exec_ms,
                    "status": "COMPLETED"
                }
                resp_data = json.dumps(response).encode("utf-8")
                resp_header = f"{len(resp_data):010d}".encode("utf-8")
                client_socket.sendall(resp_header + resp_data)
                logger.info("Completed and sent Task ID %d response to %s", task_id, client_address[0])
            except Exception as err:
                logger.error("Error processing client task %d: %s", task_id, err)
                try:
                    client_socket.close()
                except Exception:
                    pass
            finally:
                task_queue.task_done()
        except Exception as err:
            logger.error("Task processor error: %s", err)

def handle_client_connection(client_socket: socket.socket, client_address: tuple) -> None:
    """Reads request payload from client socket and queues the task."""
    logger.info("Accepted connection from %s:%d", client_address[0], client_address[1])
    try:
        # Read 10-byte length prefix first
        header = recv_all(client_socket, 10)
        payload_len = int(header.decode("utf-8"))
        
        # Read the rest of the payload
        data = recv_all(client_socket, payload_len)
        if not data:
            client_socket.close()
            return

        request = json.loads(data.decode("utf-8"))
        # Queue the request, keeping connection active until processing is complete
        task_queue.put((client_socket, client_address, request))
        logger.debug("Queued Task ID %d from %s", request.get("task_id", -1), client_address[0])
    except Exception as err:
        logger.error("Error receiving data from client %s: %s", client_address[0], err)
        try:
            client_socket.close()
        except Exception:
            pass

def main() -> None:
    """Main entry point for worker daemon."""
    # Start sequential execution queue processor thread
    processor_thread = threading.Thread(target=task_processor, daemon=True)
    processor_thread.start()

    import signal
    def sigterm_handler(signum, frame):
        raise KeyboardInterrupt("SIGTERM received")
    signal.signal(signal.SIGTERM, sigterm_handler)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server_socket.bind(("0.0.0.0", WORKER_PORT))
        server_socket.listen(128)  # Increase backlog for concurrent connections
        logger.info("Worker daemon listening on port %d...", WORKER_PORT)

        while True:
            client_socket, client_address = server_socket.accept()
            client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            # Spawn a new thread to read connection data non-blockingly
            conn_thread = threading.Thread(target=handle_client_connection, args=(client_socket, client_address), daemon=True)
            conn_thread.start()
    except KeyboardInterrupt:
        logger.info("Worker daemon shutting down on user request.")
    except Exception as err:
        logger.critical("Fatal socket server error: %s", err)
    finally:
        server_socket.close()
        task_queue.put(None)  # stop processor thread

if __name__ == "__main__":
    main()
