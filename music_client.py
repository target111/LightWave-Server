"""
LightWave Music Sender
Captures system audio via PipeWire/PulseAudio monitor source, computes FFT,
sends bins over UDP.
"""

import argparse
import json
import shutil
import socket
import struct
import subprocess
import sys

import numpy as np


def check_dependencies():
    """Ensure required system commands are available."""
    missing = []
    for cmd in ["parec", "pactl"]:
        if shutil.which(cmd) is None:
            missing.append(cmd)

    if missing:
        print(f"Error: Missing required commands: {', '.join(missing)}")
        print("Please install pipewire-pulse / pulseaudio-utils.")
        sys.exit(1)


def get_default_sink() -> str:
    """Get the default PulseAudio/PipeWire sink name."""
    try:
        result = subprocess.run(
            ["pactl", "get-default-sink"], capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print("Error: could not get default sink. Is pipewire-pulse running?")
        print(f"  stderr: {e.stderr.strip()}")
        sys.exit(1)


def list_sinks():
    """List available sinks with their monitor source names."""
    try:
        result = subprocess.run(
            ["pactl", "-f", "json", "list", "sinks"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        print("Error: could not list sinks. Is pipewire-pulse running?")
        sys.exit(1)

    try:
        sinks = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("Error: Failed to parse pactl JSON output.")
        sys.exit(1)

    default = get_default_sink()

    print("Available sinks:\n")
    for sink in sinks:
        name = sink.get("name", "?")
        desc = sink.get("description", "Unknown device")
        monitor = sink.get("monitor_source", f"{name}.monitor")
        marker = " ← default" if name == default else ""

        print(f"  {name}{marker}")
        print(f"    {desc}")
        print(f"    monitor: {monitor}\n")

    print("Use --sink <name> to pick one, or omit for the default.")
    print("The monitor source is what captures audio going TO that sink.")


def build_log_bin_edges(
    num_bins: int, fft_size: int, sample_rate: int
) -> list[tuple[int, int]]:
    """
    Map FFT bins to output bins on a logarithmic scale.
    Returns a list of (low_index, high_index) tuples to optimize the hot loop.
    """
    freqs = np.fft.rfftfreq(fft_size, d=1.0 / sample_rate)
    min_freq = max(freqs[1], 30.0)
    max_freq = min(16000.0, sample_rate / 2)

    log_edges = np.logspace(np.log10(min_freq), np.log10(max_freq), num=num_bins + 1)

    bin_slices = []
    for i in range(num_bins):
        # Convert frequencies to array indices
        lo_idx = round(log_edges[i] * fft_size / sample_rate)
        hi_idx = round(log_edges[i + 1] * fft_size / sample_rate)

        # Clamp bounds
        lo_idx = max(1, min(lo_idx, len(freqs) - 1))
        hi_idx = max(1, min(hi_idx, len(freqs) - 1))

        # Ensure at least 1 bin is captured
        if hi_idx <= lo_idx:
            hi_idx = lo_idx + 1

        bin_slices.append((lo_idx, hi_idx))

    return bin_slices


def run(
    host: str,
    port: int,
    sink: str | None,
    num_bins: int,
    gain: float,
    sample_rate: int,
    chunk_size: int,
):
    target = (host, port)
    fft_size = chunk_size

    # Pre-calculate to save CPU in the hot loop
    bin_slices = build_log_bin_edges(num_bins, fft_size, sample_rate)
    window = np.hanning(fft_size).astype(np.float32)
    normalization_factor = gain / (fft_size / 2)

    # Format string for struct. '<' means Little-Endian, 'f' means float32.
    # E.g., for 32 bins, this results in '<32f'
    packet_format = f"<{num_bins}f"

    monitor_source = f"{sink}.monitor" if sink else f"{get_default_sink()}.monitor"

    parec_cmd = [
        "parec",
        "--format=float32le",
        f"--rate={sample_rate}",
        "--channels=1",
        f"--device={monitor_source}",
        "--latency-msec=20",
    ]

    print(f"Monitor: {monitor_source}")
    print(f"Sending {num_bins} bins → {host}:{port}  (gain={gain})")
    print("Press Ctrl+C to stop.\n")

    bytes_per_chunk = chunk_size * 4  # 4 bytes per float32

    # Use context managers to guarantee cleanup
    with (
        socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock,
        subprocess.Popen(
            parec_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        ) as proc,
    ):
        try:
            output = np.zeros(num_bins, dtype=np.float32)

            while True:
                # This call blocks until exactly bytes_per_chunk is available,
                # effectively locking the while loop to the audio sample rate.
                raw = proc.stdout.read(bytes_per_chunk)

                if not raw or len(raw) < bytes_per_chunk:
                    # If we get less than requested, the stream ended (parec died).
                    # Do not 'continue', as it misaligns byte boundaries.
                    err = proc.stderr.read().decode().strip()
                    print(f"\nparec exited or stream ended. {err}")
                    break

                # Parse raw PCM → numpy
                mono = np.frombuffer(raw, dtype=np.float32)

                # Windowed FFT → magnitude spectrum
                spectrum = np.abs(np.fft.rfft(mono * window))

                # Aggregate bins using the pre-calculated tuples
                for i, (lo, hi) in enumerate(bin_slices):
                    output[i] = np.mean(spectrum[lo:hi])

                # Normalize, apply gain, clamp
                output *= normalization_factor
                np.clip(output, 0.0, 1.0, out=output)

                # Pack as Little-Endian floats to ensure network compatibility
                payload = struct.pack(packet_format, *output)
                sock.sendto(payload, target)

        except KeyboardInterrupt:
            pass
        finally:
            proc.terminate()

    print("\nStopped.")


def main():
    check_dependencies()

    parser = argparse.ArgumentParser(
        description="Capture audio → FFT → UDP for LightWave MusicVisualizer"
    )
    parser.add_argument(
        "--list", action="store_true", help="List available sinks and exit"
    )
    parser.add_argument(
        "--sink", "-s", type=str, default=None, help="PulseAudio/PipeWire sink name"
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="LightWave server IP (default: 127.0.0.1)"
    )
    parser.add_argument("--port", "-p", type=int, default=5555, help="UDP port")
    parser.add_argument(
        "--bins", "-b", type=int, default=32, help="Number of frequency bins"
    )
    parser.add_argument("--gain", "-g", type=float, default=3.0, help="Gain multiplier")
    parser.add_argument("--rate", type=int, default=48000, help="Sample rate")
    parser.add_argument(
        "--chunk", type=int, default=1024, help="FFT window size in samples"
    )

    args = parser.parse_args()

    if args.list:
        list_sinks()
        sys.exit(0)

    run(
        host=args.host,
        port=args.port,
        sink=args.sink,
        num_bins=args.bins,
        gain=args.gain,
        sample_rate=args.rate,
        chunk_size=args.chunk,
    )


if __name__ == "__main__":
    main()
