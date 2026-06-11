"""Regression test: when the UDP sender stops mid-stream, the visualizer
must fade back to its ambient state instead of replaying the last frame."""

import socket
import struct
import time

import pytest

from lib.effects.library.visualizer import MusicVisualizer


@pytest.fixture
def visualizer(led):
    effect = MusicVisualizer(led, port=0, silence_timeout=0.05)
    yield effect
    effect.teardown()


def _send_bins(effect: MusicVisualizer, value: float, count: int = 32):
    recv_sock = effect._udp._sock
    port = recv_sock.getsockname()[1]
    payload = struct.pack(f"<{count}f", *([value] * count))
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(payload, ("127.0.0.1", port))
    # Give the loopback packet a moment to land in the receive buffer
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        try:
            recv_sock.recvfrom(4096, socket.MSG_PEEK)
            return
        except BlockingIOError:
            time.sleep(0.001)
    raise AssertionError("UDP packet never arrived")


def test_loud_audio_raises_energy(visualizer):
    _send_bins(visualizer, 0.8)
    visualizer.tick(1 / 60)
    assert visualizer.energy > 0.5
    assert visualizer.bass > 0.5


def test_sender_stop_fades_to_ambient(visualizer):
    _send_bins(visualizer, 0.8)
    visualizer.tick(1 / 60)
    assert visualizer.energy > 0.5

    # Sender interrupted: no more packets. Without the silence timeout the
    # bins stay frozen and pulses keep spawning from stale data forever.
    for _ in range(150):
        visualizer.tick(1 / 60)

    assert visualizer.energy < 0.01
    assert visualizer.bass < 0.01
    assert visualizer.pulses == []


def test_brief_gap_does_not_reset(visualizer):
    _send_bins(visualizer, 0.8)
    visualizer.tick(1 / 60)
    energy_before = visualizer.energy

    # A gap shorter than silence_timeout (e.g. between packets) keeps state
    visualizer.tick(1 / 60)
    assert visualizer.energy == pytest.approx(energy_before)
