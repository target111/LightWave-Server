import colorsys
import math
import random
import socket
import struct
import time

from lib.effects.base import EffectBase


class MusicVisualizer(EffectBase):
    """
    Layered music visualizer driven by UDP FFT data.
    """

    # Bass pulses ripple outward from the center, mids shift hue, treble
    # spawns sparkles, and beat hits trigger flashes and color changes.
    # Send packed little-endian float32 values (0.0-1.0) over UDP.

    CONFIG_SCHEMA = [
        {
            "name": "port",
            "type": "int",
            "default": 5555,
            "description": "UDP port to listen on",
        },
        {
            "name": "smoothing",
            "type": "float",
            "default": 0.4,
            "description": "Temporal smoothing (0.0 = raw, 0.99 = molasses)",
        },
        {
            "name": "sensitivity",
            "type": "float",
            "default": 2.5,
            "description": "Overall gain multiplier",
        },
        {
            "name": "beat_threshold",
            "type": "float",
            "default": 1.4,
            "description": (
                "Beat detection threshold (current vs average energy)"
            ),
        },
        {
            "name": "pulse_speed",
            "type": "float",
            "default": 2.0,
            "description": (
                "Speed of bass ripple pulses (pixels per frame at 60 FPS)"
            ),
        },
        {
            "name": "sparkle_decay",
            "type": "float",
            "default": 0.88,
            "description": "Treble sparkle fade speed (per frame at 60 FPS)",
        },
        {
            "name": "flash_decay",
            "type": "float",
            "default": 0.4,
            "description": (
                "Beat flash fade speed (0.0 = 1 frame, 0.9 = slow fade)"
            ),
        },
        {
            "name": "pulse_intensity",
            "type": "float",
            "default": 1.5,
            "description": "Base multiplier for pulse brightness",
        },
        {
            "name": "beat_multiplier",
            "type": "float",
            "default": 1.5,
            "description": "Extra brightness multiplier for beat hits",
        },
        {
            "name": "pulse_width",
            "type": "float",
            "default": 3.0,
            "description": "Starting width of bass pulses",
        },
        {
            "name": "ambient_brightness",
            "type": "float",
            "default": 0.05,
            "description": "Minimum brightness of the background wave",
        },
        {
            "name": "silence_timeout",
            "type": "float",
            "default": 0.5,
            "description": "Seconds without UDP data before fading to ambient",
        },
    ]

    port: int
    smoothing: float
    sensitivity: float
    beat_threshold: float
    pulse_speed: float
    sparkle_decay: float
    flash_decay: float
    pulse_intensity: float
    beat_multiplier: float
    pulse_width: float
    ambient_brightness: float
    silence_timeout: float

    _REF_FPS = 60.0

    def __init__(self, led, **kwargs):
        super().__init__(led, **kwargs)

        n = self.led.count

        # -- frequency band state --
        self._bins: list[float] = []
        self.bass = 0.0
        self.mids = 0.0
        self.treble = 0.0
        self.energy = 0.0

        # -- beat detection --
        self.energy_history: list[float] = [0.0] * 30
        self.energy_idx = 0
        self.beat_cooldown = 0.0

        # -- hue state --
        self.base_hue = 0.0
        self.beat_hue_offset = 0.0

        # -- visual layers state --
        # Each pulse: [position_from_center, intensity, hue]
        self.pulses: list[list[float]] = []
        self.sparkle_buffer = [0.0] * n
        self.sparkle_hues = [0.0] * n
        self.flash_level = 0.0
        self.wave_t = 0.0

        # -- per-pixel output buffer (RGB floats 0-1) --
        self.pixel_r = [0.0] * n
        self.pixel_g = [0.0] * n
        self.pixel_b = [0.0] * n

        # -- delta-time tracking --
        self._last_time = time.monotonic()
        self._last_packet_time = self._last_time
        # Spawn rates were "one per frame" at 60 FPS; accumulate fractional
        # frames so slower/faster loops produce the same rate per second.
        self._pulse_spawn_accum = 0.0
        self._sparkle_spawn_accum = 0.0

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("0.0.0.0", self.port))
        self._sock.setblocking(False)

    def _drain_udp(self) -> list[float] | None:
        latest_data = None
        while True:
            try:
                data, _ = self._sock.recvfrom(4096)
                latest_data = data
            except BlockingIOError:
                break

        if latest_data:
            num_floats = len(latest_data) // 4
            if num_floats > 0:
                payload = latest_data[: num_floats * 4]
                return list(struct.unpack(f"<{num_floats}f", payload))
        return None

    def _update_bins(self, raw: list[float]):
        if len(self._bins) != len(raw):
            self._bins = [0.0] * len(raw)

        a = self.smoothing
        for i in range(len(raw)):
            v = max(0.0, min(1.0, raw[i])) * self.sensitivity
            self._bins[i] = a * self._bins[i] + (1.0 - a) * v

    def _extract_bands(self):
        n = len(self._bins)
        if n == 0:
            self.bass = self.mids = self.treble = self.energy = 0.0
            return

        bass_end = max(1, n // 4)
        mid_end = max(bass_end + 1, int(n * 0.65))

        self.bass = max(self._bins[:bass_end])
        self.mids = max(self._bins[bass_end:mid_end])
        self.treble = max(self._bins[mid_end:])
        self.energy = sum(self._bins) / n

    def _detect_beat(self, frames: float) -> bool:
        avg = sum(self.energy_history) / len(self.energy_history)
        self.energy_history[self.energy_idx] = self.energy
        self.energy_idx = (self.energy_idx + 1) % len(self.energy_history)

        if self.beat_cooldown > 0:
            self.beat_cooldown -= frames
            return False

        if avg > 0.01 and self.energy > avg * self.beat_threshold:
            self.beat_cooldown = 6  # ~100ms lockout
            return True
        return False

    def _update_hue(self, beat: bool, frames: float):
        self.base_hue = (self.base_hue + self.mids * 0.003 * frames) % 1.0

        if beat:
            self.beat_hue_offset = random.uniform(0.15, 0.45)
        else:
            self.beat_hue_offset *= 0.92**frames

    def _spawn_pulses(self, beat: bool, frames: float):
        if self.bass <= 0.15:
            self._pulse_spawn_accum = 0.0
            return

        self._pulse_spawn_accum += frames
        while self._pulse_spawn_accum >= 1.0:
            self._pulse_spawn_accum -= 1.0

            # Cap so overlapping pulses don't instantly blow out to white
            intensity = min(self.bass * self.pulse_intensity, 2.0)
            if beat:
                intensity *= self.beat_multiplier

            hue = (self.base_hue + self.beat_hue_offset) % 1.0
            self.pulses.append([0.0, intensity, hue])

    def _update_pulses(self, frames: float):
        n = self.led.count
        center = n / 2.0
        alive = []

        pulse_decay = 0.96**frames

        for pos, intensity, hue in self.pulses:
            pos += self.pulse_speed * frames
            intensity *= pulse_decay

            if intensity < 0.02 or pos > center + 5:
                continue

            width = self.pulse_width + pos * 0.15
            r, g, b = colorsys.hsv_to_rgb(hue, 0.85, 1.0)

            for offset in [-1, 1]:
                pixel_center = center + offset * pos
                lo = max(0, int(pixel_center - width))
                hi = min(n - 1, int(pixel_center + width))

                for j in range(lo, hi + 1):
                    dist = abs(j - pixel_center)
                    falloff = max(0.0, 1.0 - dist / width)
                    strength = intensity * falloff
                    self.pixel_r[j] += r * strength
                    self.pixel_g[j] += g * strength
                    self.pixel_b[j] += b * strength

            alive.append([pos, intensity, hue])

        self.pulses = alive

    def _update_sparkles(self, frames: float):
        n = self.led.count
        decay = self.sparkle_decay**frames

        for i in range(n):
            self.sparkle_buffer[i] *= decay

        self._sparkle_spawn_accum += self.treble * 12 * frames
        num_new = int(self._sparkle_spawn_accum)
        self._sparkle_spawn_accum -= num_new

        for _ in range(num_new):
            idx = random.randint(0, n - 1)
            self.sparkle_buffer[idx] = min(1.0, self.treble * 1.5)
            self.sparkle_hues[idx] = (
                self.base_hue + self.beat_hue_offset + random.uniform(-0.1, 0.1)
            ) % 1.0

        for i in range(n):
            if self.sparkle_buffer[i] > 0.05:
                r, g, b = colorsys.hsv_to_rgb(self.sparkle_hues[i], 0.3, 1.0)
                v = self.sparkle_buffer[i]
                self.pixel_r[i] += r * v
                self.pixel_g[i] += g * v
                self.pixel_b[i] += b * v

    def _background_wave(self, frames: float):
        n = self.led.count
        self.wave_t += (0.02 + self.energy * 0.1) * frames

        hue = (self.base_hue + self.beat_hue_offset) % 1.0
        base_brightness = self.ambient_brightness + self.energy * 0.10

        for i in range(n):
            frac = i / max(n - 1, 1)
            wave = (math.sin(frac * 6.0 + self.wave_t) + 1.0) * 0.5
            v = base_brightness * (0.3 + 0.7 * wave)
            pixel_hue = (hue + frac * 0.3) % 1.0
            r, g, b = colorsys.hsv_to_rgb(pixel_hue, 0.7, v)

            self.pixel_r[i] += r
            self.pixel_g[i] += g
            self.pixel_b[i] += b

    def _flash(self, beat: bool, frames: float):
        if beat:
            self.flash_level = 0.6

        self.flash_level *= self.flash_decay**frames

        if self.flash_level > 0.01:
            n = self.led.count
            for i in range(n):
                self.pixel_r[i] += self.flash_level
                self.pixel_g[i] += self.flash_level
                self.pixel_b[i] += self.flash_level

    def tick(self):
        now = time.monotonic()
        dt = now - self._last_time
        self._last_time = now

        # Clamp dt so a stall (e.g. GC pause) doesn't fast-forward the effect
        dt = min(dt, 0.05)
        frames = dt * self._REF_FPS

        raw = self._drain_udp()
        if raw is not None:
            self._last_packet_time = now
            self._update_bins(raw)
        elif now - self._last_packet_time > self.silence_timeout:
            # The sender stopped (or died mid-stream). Without this the bins
            # freeze at their last values and the effect keeps replaying the
            # final frame; feed silence so it decays back to the ambient wave.
            self._update_bins([0.0] * len(self._bins))
        self._extract_bands()

        beat = self._detect_beat(frames)
        self._update_hue(beat, frames)

        n = self.led.count

        self.pixel_r = [0.0] * n
        self.pixel_g = [0.0] * n
        self.pixel_b = [0.0] * n

        # Layers blend additively into the pixel buffer
        self._background_wave(frames)
        self._spawn_pulses(beat, frames)
        self._update_pulses(frames)
        self._update_sparkles(frames)
        self._flash(beat, frames)

        buffer = [
            (
                max(0, min(255, int(self.pixel_r[i] * 255))),
                max(0, min(255, int(self.pixel_g[i] * 255))),
                max(0, min(255, int(self.pixel_b[i] * 255))),
            )
            for i in range(n)
        ]
        self.led.set_pixels(buffer)

    def teardown(self):
        try:
            self._sock.close()
        except OSError:
            pass
