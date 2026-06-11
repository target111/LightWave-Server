"""Shared UDP plumbing for stream-driven effects (visualizer, ambilight)."""

import socket
import struct


class UdpFloatListener:
    """Non-blocking UDP socket receiving packed little-endian float32
    payloads. Senders stream frames continuously; only the newest packet
    matters, so reads drain the queue and keep the last one."""

    def __init__(self, port: int):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("0.0.0.0", port))
        self._sock.setblocking(False)

    def drain_latest(self) -> tuple[float, ...] | None:
        """Read all pending packets and unpack the latest, or None."""
        latest = None
        while True:
            try:
                data, _ = self._sock.recvfrom(4096)
                latest = data
            except BlockingIOError:
                break

        if latest:
            num_floats = len(latest) // 4
            if num_floats > 0:
                payload = latest[: num_floats * 4]
                return struct.unpack(f"<{num_floats}f", payload)
        return None

    def close(self) -> None:
        try:
            self._sock.close()
        except OSError:
            pass
