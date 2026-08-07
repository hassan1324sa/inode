import sys
import socket
from app.core.settings import settings

def check_temporal() -> bool:
    host_port = settings.temporal.host.split(":")
    host = host_port[0]
    port = int(host_port[1]) if len(host_port) > 1 else 7233
    try:
        s = socket.create_connection((host, port), timeout=3)
        s.close()
        return True
    except Exception as e:
        print(f"Temporal check failed: {e}", file=sys.stderr)
        return False

def main():
    if not check_temporal():
        sys.exit(1)
    print("Worker health check passed.")
    sys.exit(0)

if __name__ == "__main__":
    main()
