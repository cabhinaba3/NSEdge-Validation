#!/usr/bin/env python3
import socket
import sys
import time

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 state_receiver.py [port]")
        sys.exit(1)
    port = int(sys.argv[1])
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", port))
    server.listen(1)
    print(f"State receiver listening on {port}...")
    
    while True:
        try:
            conn, addr = server.accept()
            print(f"Accepted connection from {addr}")
            total_received = 0
            start_t = time.perf_counter()
            while True:
                data = conn.recv(1024 * 1024)
                if not data:
                    break
                total_received += len(data)
            end_t = time.perf_counter()
            print(f"Received {total_received / (1024*1024):.2f} MB in {end_t - start_t:.2f} s")
            conn.close()
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
